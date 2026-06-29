import re
import string
import random
import json
import os
import tempfile
from io import BytesIO

from telegram import Update, ReactionTypeEmoji, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image as RLImage
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from docx import Document as DocxDocument
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ═══════════════════════════════════════════════════════════════
# FONT SETUP
# ═══════════════════════════════════════════════════════════════
_POPPINS_REG  = "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
_POPPINS_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"

FONT_NAME      = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"

if os.path.exists(_POPPINS_REG) and os.path.exists(_POPPINS_BOLD):
    try:
        pdfmetrics.registerFont(TTFont("Poppins",      _POPPINS_REG))
        pdfmetrics.registerFont(TTFont("Poppins-Bold", _POPPINS_BOLD))
        FONT_NAME      = "Poppins"
        FONT_NAME_BOLD = "Poppins-Bold"
        print("Poppins font loaded")
    except Exception as e:
        print(f"Poppins load error: {e} — using Helvetica")
else:
    print("Poppins not found — using Helvetica")

BOT_TOKEN = "8661732123:AAFZ-NZjhNyZQz75j0u4Rv9syFEo9twmisY"

# ── Replace with YOUR Telegram numeric user ID ──────────────────
# To find it: message @userinfobot on Telegram → it replies with your ID
ADMIN_ID = 123456789   # ← CHANGE THIS

# ═══════════════════════════════════════════════════════════════
# USERS STORAGE
# ═══════════════════════════════════════════════════════════════
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(list(USERS), f)

USERS = load_users()

# ═══════════════════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════════════════
PDF_BUFFER      = {}   # user_id -> list of item dicts
PDF_NAMES       = {}   # user_id -> str
AWAITING_NAME   = {}   # user_id -> True
SLEEPING        = set()
PROGRESS_MSG_ID = {}   # user_id -> message_id of the live progress message

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
MAX_QUESTIONS_PER_MSG = 40
TELEGRAM_Q_LIMIT      = 300   # max chars in poll question field
TELEGRAM_DESC_LIMIT   = 200   # max chars in poll description (shown above question)
TELEGRAM_EX_LIMIT     = 200   # max chars in poll explanation (shown after answering)
PDF_MAX_IMG_WIDTH     = 13 * cm

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def clean_option(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[A-Ea-e1-5][).\-]\s*", "", line)
    line = re.sub(r"^[-•]\s*", "", line)
    return line.strip()

def strip_leading_letter_prefix(option: str) -> str:
    return re.sub(r"^[A-Ea-e]\)\s*", "", option).strip()

def normalize_mcq_block(block: str):
    block = block.strip()
    if "\n" in block:
        return [l.strip() for l in block.split("\n") if l.strip()]
    match = re.search(r"\b([A-Ea-e1-5])[).]", block)
    if not match:
        return [block]
    question     = block[:match.start()].strip()
    options_part = block[match.start():]
    parts = re.split(r"(?=\b[A-Ea-e1-5][).])", options_part)
    return [question] + [p.strip() for p in parts if p.strip()]

def strip_spoiler_markers(text: str) -> str:
    return re.sub(r"\|\|(.+?)\|\|", r"\1", text, flags=re.DOTALL)

def parse_written_question(block: str):
    block = strip_spoiler_markers(block)
    lines = [l.rstrip() for l in block.split("\n") if l.strip()]
    if len(lines) < 2:
        return None
    title = re.sub(r'[\""\']+$', "", lines[0]).strip()
    content_lines = lines[1:]
    content = "\n".join(content_lines).strip()
    if not content:
        return None
    if content.startswith(".") and content.endswith("."):
        content = content[1:-1].strip()
        return title, content
    if content:
        return title, content
    return None

def parse_written_strict(block: str):
    block = strip_spoiler_markers(block)
    lines = [l.rstrip() for l in block.split("\n") if l.strip()]
    if len(lines) < 2:
        return None
    title   = lines[0]
    content = "\n".join(lines[1:]).strip()
    if content.startswith(".") and content.endswith("."):
        return title, content[1:-1].strip()
    return None

def split_question_for_telegram(question: str):
    """
    Returns (main_q, description_overflow) where:
    - main_q fits in TELEGRAM_Q_LIMIT
    - description_overflow goes into the 'description' field (shown above question)
      and is capped at TELEGRAM_DESC_LIMIT
    If question fits in Q_LIMIT, description_overflow is None.
    """
    if len(question) <= TELEGRAM_Q_LIMIT:
        return question, None
    # Try to split at a sentence boundary
    cutoff    = TELEGRAM_Q_LIMIT - 3
    split_pos = question.rfind(". ", 0, cutoff)
    if split_pos == -1:
        split_pos = question.rfind(" ", 0, cutoff)
    if split_pos == -1:
        split_pos = cutoff
    main     = question[:split_pos].strip() + "…"
    overflow = "…" + question[split_pos:].strip()
    # Cap overflow to TELEGRAM_DESC_LIMIT
    if len(overflow) > TELEGRAM_DESC_LIMIT:
        overflow = overflow[:TELEGRAM_DESC_LIMIT - 1] + "…"
    return main, overflow

def options_too_long(options: list) -> bool:
    """Check if any single option exceeds Telegram's 100-char option limit."""
    return any(len(o) > 100 for o in options)

def make_letter_only_options(count: int) -> list:
    """Return ['A', 'B', 'C', ...] for poll when answers are too long."""
    return [string.ascii_uppercase[i] for i in range(count)]

def _cleanup_images(user_id: int):
    import shutil
    img_dir = f"/tmp/quizician_imgs/{user_id}"
    if os.path.exists(img_dir):
        shutil.rmtree(img_dir, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════
# PROGRESS MESSAGE BUILDER
# ═══════════════════════════════════════════════════════════════
def build_progress_text(items: list, latest_label: str = "") -> str:
    count    = len(items)
    bar_len  = 10
    filled   = min(count, bar_len)
    bar      = "█" * filled + "░" * (bar_len - filled)

    type_counts = {"mcq": 0, "written": 0, "image": 0}
    for it in items:
        t = it.get("type", "mcq")
        if t in type_counts:
            type_counts[t] += 1

    breakdown = []
    if type_counts["mcq"]:
        breakdown.append(f"❓ {type_counts['mcq']} MCQ")
    if type_counts["written"]:
        breakdown.append(f"📝 {type_counts['written']} Written")
    if type_counts["image"]:
        breakdown.append(f"🖼 {type_counts['image']} Image")

    text = (
        f"📄 <b>PDF Collection Mode</b>\n"
        f"<code>{bar}</code>\n"
        f"Collected: <b>{count}</b> item{'s' if count != 1 else ''}"
    )
    if breakdown:
        text += f"\n{' · '.join(breakdown)}"
    if latest_label:
        text += f"\n<i>Latest: {latest_label}</i>"
    return text

async def update_progress(context, user_id: int, chat_id: int, latest_label: str = ""):
    """Edit the existing progress message, or send a new one and store its id."""
    items    = PDF_BUFFER.get(user_id, [])
    text     = build_progress_text(items, latest_label)
    keyboard = export_keyboard()
    msg_id   = PROGRESS_MSG_ID.get(user_id)

    if msg_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass  # message too old / deleted — fall through to send new

    sent = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )
    PROGRESS_MSG_ID[user_id] = sent.message_id

# ═══════════════════════════════════════════════════════════════
# KEYBOARD HELPERS
# ═══════════════════════════════════════════════════════════════
def export_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 Export as PDF",  callback_data="gen_pdf"),
            InlineKeyboardButton("📝 Export as DOCX", callback_data="gen_docx"),
        ],
        [InlineKeyboardButton("🗑 Clear & Cancel", callback_data="clear_pdf")],
    ])

def start_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📚 How To Use",     callback_data="menu_how"),
            InlineKeyboardButton("🆕 Latest Updates", callback_data="menu_updates"),
        ],
        [
            InlineKeyboardButton("📄 PDF Mode Guide", callback_data="menu_pdf"),
        ],
    ])

# ═══════════════════════════════════════════════════════════════
# MENU TEXT CONTENT
# ═══════════════════════════════════════════════════════════════
HOW_TO_USE_TEXT = (
    "📚 <b>How To Use — Quizician Bot</b>\n\n"
    "<b>1) Normal MCQ</b>\n"
    "<code>Question?\n"
    "a) Option A\n"
    "b) Option B z   ← mark correct with z\n"
    "c) Option C\n"
    "ex: Explanation here (optional)</code>\n\n"
    "<b>2) Single-line MCQ</b>\n"
    "<code>Question? a) A b) B z c) C</code>\n\n"
    "<b>3) Written / Flashcard</b>\n"
    "<code>Title\n"
    ".answer line 1\n"
    "answer line 2.</code>\n"
    "<i>Wrap the answer between dots.</i>\n\n"
    "<b>4) Forwarded Quiz Polls</b>\n"
    "Forward any Telegram quiz — the bot re-sends it with the correct answer preserved.\n\n"
    "<b>5) PDF / DOCX Mode</b>\n"
    "Use /pdf_start, collect items, then export.\n\n"
    "😴 /sleep — mute the bot until /start"
)

LATEST_UPDATES_TEXT = (
    "🆕 <b>Latest Updates — V5.4</b>\n\n"
    "• 📖 <b>ex: explanation support</b> — add <code>ex: your explanation</code> "
    "after answers to show it after answering the poll\n"
    "• ✅ <b>Forwarded quiz correct answer</b> — re-sent polls now preserve "
    "the correct answer and work outside PDF mode too\n"
    "• ⚠️ <b>Format error messages</b> — bot tells you exactly what's wrong\n"
    "• 📋 <b>Long question handling</b> — if Q is too long, sends text first then poll; "
    "if both Q and answers are too long, shows A/B/C/D only in poll\n"
    "• 🔥 Removed fire self-reaction\n"
    "• 🎛 Clean start menu with inline buttons\n"
    "• 📊 Live progress bar in PDF mode\n"
    "• 📝 PDF + DOCX export both supported"
    " ❤️ وأدعيلي دعوة حلوه ❤️\n" 
)

PDF_MODE_GUIDE_TEXT = (
    "📄 <b>PDF Mode Guide</b>\n\n"
    "<b>Step 1:</b> Send /pdf_start\n"
    "<b>Step 2:</b> Type a file name when asked\n"
    "<b>Step 3:</b> Send any of the following:\n\n"
    "  ❓ MCQ questions (text format)\n"
    "  📝 Written flashcards (dot format)\n"
    "  📊 Forwarded Telegram quizzes/polls\n"
    "  🖼 Images or comparison photos\n"
    "  💬 Messages with spoiler text (||hidden||)\n\n"
    "<b>Step 4:</b> Press <b>Export as PDF</b> or <b>Export as DOCX</b>\n\n"
    "<b>Commands:</b>\n"
    "• /pdf_start — start a new collection\n"
    "• /pdf_clear — cancel and clear\n\n"
    "<i>A live progress bar shows how many items are collected. "
    "It updates in-place — no spam.</i>"
)

# ═══════════════════════════════════════════════════════════════
# PDF BUILDER
# ═══════════════════════════════════════════════════════════════
def build_pdf(items: list, doc_title: str = "questions") -> BytesIO:
    buffer = BytesIO()

    LEFT_COLOR  = colors.HexColor("#00BCD4")
    RIGHT_COLOR = colors.HexColor("#7B1FA2")

    def draw_header(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT_NAME_BOLD, 9)
        canvas.setFillColor(LEFT_COLOR)
        canvas.drawString(2 * cm, A4[1] - 1.4 * cm, "MDM44 | Notes & Files")
        canvas.setFillColor(RIGHT_COLOR)
        canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.4 * cm, "Made by The Quizician")
        canvas.setStrokeColor(colors.HexColor("#CFD8DC"))
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, A4[1] - 1.65 * cm, A4[0] - 2 * cm, A4[1] - 1.65 * cm)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
    )

    Q_STYLE = ParagraphStyle(
        "QStyle", fontName=FONT_NAME_BOLD, fontSize=12, leading=16,
        textColor=colors.HexColor("#1A1A2E"), spaceAfter=6, spaceBefore=14,
    )
    OPT_STYLE = ParagraphStyle(
        "OptStyle", fontName=FONT_NAME, fontSize=11, leading=15,
        textColor=colors.HexColor("#1A1A2E"), leftIndent=14, spaceAfter=3,
    )
    OPT_CORRECT = ParagraphStyle(
        "OptCorrect", fontName=FONT_NAME_BOLD, fontSize=11, leading=15,
        textColor=colors.HexColor("#1B5E20"), leftIndent=14, spaceAfter=3,
    )
    WRITTEN_TITLE = ParagraphStyle(
        "WTitle", fontName=FONT_NAME_BOLD, fontSize=12, leading=16,
        textColor=colors.HexColor("#1A1A2E"), spaceAfter=4, spaceBefore=14,
    )
    WRITTEN_BODY = ParagraphStyle(
        "WBody", fontName=FONT_NAME, fontSize=11, leading=15,
        textColor=colors.HexColor("#37474F"), leftIndent=14, spaceAfter=6,
    )
    NUM_STYLE = ParagraphStyle(
        "NumStyle", fontName=FONT_NAME_BOLD, fontSize=9,
        textColor=colors.HexColor("#90A4AE"), spaceAfter=2,
    )
    IMG_CAPTION = ParagraphStyle(
        "ImgCaption", fontName=FONT_NAME, fontSize=9, leading=12,
        textColor=colors.HexColor("#78909C"), spaceAfter=6, spaceBefore=4,
    )

    HR_COLOR = colors.HexColor("#CFD8DC")
    story    = []

    for idx, item in enumerate(items, 1):
        story.append(Paragraph(f"Q{idx}", NUM_STYLE))

        if item["type"] == "mcq":
            story.append(Paragraph(item["q"], Q_STYLE))
            for i, opt in enumerate(item["options"]):
                if i == item["correct"]:
                    story.append(Paragraph(f"✓  {opt}", OPT_CORRECT))
                else:
                    story.append(Paragraph(f"     {opt}", OPT_STYLE))

        elif item["type"] == "written":
            story.append(Paragraph(item["title"], WRITTEN_TITLE))
            for line in item["content"].split("\n"):
                line = line.strip()
                if line:
                    story.append(Paragraph(f"• {line}", WRITTEN_BODY))

        elif item["type"] == "image":
            img_path = item["path"]
            try:
                img = RLImage(img_path)
                if img.imageWidth > PDF_MAX_IMG_WIDTH:
                    scale          = PDF_MAX_IMG_WIDTH / img.imageWidth
                    img.drawWidth  = PDF_MAX_IMG_WIDTH
                    img.drawHeight = img.imageHeight * scale
                story.append(Spacer(1, 8))
                story.append(img)
                if item.get("caption"):
                    story.append(Paragraph(f"📷 {item['caption']}", IMG_CAPTION))
                story.append(Spacer(1, 4))
            except Exception as e:
                story.append(Paragraph(f"[Image error: {e}]", WRITTEN_BODY))

        if idx < len(items):
            story.append(Spacer(1, 6))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HR_COLOR, spaceAfter=4))

    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header)
    buffer.seek(0)
    return buffer

# ═══════════════════════════════════════════════════════════════
# DOCX BUILDER  — pure Python, no Node.js
# ═══════════════════════════════════════════════════════════════
def _hex_to_rgb(hex_color: str):
    """Convert 'RRGGBB' string to RGBColor."""
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def _add_paragraph(doc, text: str, bold=False, size_pt=11,
                   color_hex="1A1A2E", indent_cm=0,
                   space_before=0, space_after=6,
                   align=WD_ALIGN_PARAGRAPH.LEFT) -> None:
    p   = doc.add_paragraph()
    p.alignment = align
    pf  = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after  = Pt(space_after)
    if indent_cm:
        pf.left_indent = Cm(indent_cm)
    run = p.add_run(text)
    run.bold        = bold
    run.font.size   = Pt(size_pt)
    run.font.color.rgb = _hex_to_rgb(color_hex)
    return p

def _add_horizontal_rule(doc):
    """Add a thin bottom border to simulate a horizontal rule."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),   "single")
    bottom.set(qn("w:sz"),    "4")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "CFD8DC")
    pBdr.append(bottom)
    pPr.append(pBdr)

def _set_header_border(para):
    """Add bottom border to the header paragraph."""
    pPr   = para._p.get_or_add_pPr()
    pBdr  = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),   "single")
    bottom.set(qn("w:sz"),    "4")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), "CFD8DC")
    pBdr.append(bottom)
    pPr.append(pBdr)

def build_docx(items: list, doc_title: str = "questions") -> BytesIO:
    doc = DocxDocument()

    # ── Page margins ──────────────────────────────────────────
    for section in doc.sections:
        section.top_margin    = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin   = Cm(2.0)
        section.right_margin  = Cm(2.0)

    # ── Header ────────────────────────────────────────────────
    header_para = doc.add_paragraph()
    header_para.paragraph_format.space_after = Pt(8)
    _set_header_border(header_para)

    r1 = header_para.add_run("MDM44 | Notes & Files")
    r1.bold            = True
    r1.font.size       = Pt(9)
    r1.font.color.rgb  = _hex_to_rgb("00BCD4")

    header_para.add_run("   ·   ")

    r2 = header_para.add_run("Made by The Quizician")
    r2.bold            = True
    r2.font.size       = Pt(9)
    r2.font.color.rgb  = _hex_to_rgb("7B1FA2")

    # ── Items ─────────────────────────────────────────────────
    for idx, item in enumerate(items, 1):

        # Q-number label
        _add_paragraph(doc, f"Q{idx}", bold=True, size_pt=8,
                       color_hex="90A4AE", space_before=10, space_after=2)

        if item["type"] == "mcq":
            _add_paragraph(doc, item["q"], bold=True, size_pt=12,
                           color_hex="1A1A2E", space_before=0, space_after=4)
            for i, opt in enumerate(item["options"]):
                correct = (i == item["correct"])
                _add_paragraph(
                    doc,
                    ("✓  " if correct else "     ") + opt,
                    bold=correct, size_pt=11,
                    color_hex="1B5E20" if correct else "1A1A2E",
                    indent_cm=0.7, space_after=3,
                )

        elif item["type"] == "written":
            _add_paragraph(doc, item["title"], bold=True, size_pt=12,
                           color_hex="1A1A2E", space_before=0, space_after=4)
            for line in item["content"].split("\n"):
                line = line.strip()
                if line:
                    _add_paragraph(doc, f"• {line}", bold=False, size_pt=11,
                                   color_hex="37474F", indent_cm=0.7, space_after=3)

        elif item["type"] == "image":
            img_path = item.get("path", "")
            if img_path and os.path.exists(img_path):
                try:
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before = Pt(6)
                    p.paragraph_format.space_after  = Pt(4)
                    run = p.add_run()
                    run.add_picture(img_path, width=Inches(5.5))
                    if item.get("caption"):
                        cap = _add_paragraph(
                            doc, f"📷 {item['caption']}",
                            bold=False, size_pt=9, color_hex="78909C",
                            space_after=4,
                        )
                        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception as e:
                    _add_paragraph(doc, f"[Image error: {e}]",
                                   size_pt=10, color_hex="B71C1C")
            else:
                _add_paragraph(doc, "[Image file not found]",
                               size_pt=10, color_hex="B71C1C")

        # Divider between items
        if idx < len(items):
            _add_horizontal_rule(doc)

    # ── Save to BytesIO ───────────────────────────────────────
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ═══════════════════════════════════════════════════════════════
# REACTIONS
# ═══════════════════════════════════════════════════════════════
async def react_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        roll  = random.randint(1, 20)
        emoji = "🫡" if roll <= 15 else "❤️" if roll <= 19 else "🏆"
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reaction=[ReactionTypeEmoji(emoji)],
            is_big=False,
        )
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# SLEEP / WAKE COMMANDS
# ═══════════════════════════════════════════════════════════════
async def sleep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    SLEEPING.add(user_id)
    await update.message.reply_text(
        "😴 والله لأنا سايبهالك وداخل أنام\n"
        "لما تحتاجني تاني مش معبرك\n"
    )

# ═══════════════════════════════════════════════════════════════
# FORWARDED POLL HANDLER
# ═══════════════════════════════════════════════════════════════
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.poll:
        return

    user_id = update.effective_chat.id
    if user_id in SLEEPING:
        return

    poll = update.message.poll

    # ── Normal mode: re-send the forwarded quiz as a live poll ──
    if user_id not in PDF_BUFFER:
        question      = poll.question
        # Strip any existing A) B) C) prefixes from options to avoid double-labeling
        raw_options   = [strip_leading_letter_prefix(opt.text) for opt in poll.options]
        correct_index = poll.correct_option_id if poll.correct_option_id is not None else 0

        labeled_options = [
            f"{string.ascii_uppercase[i]}) {opt}"
            for i, opt in enumerate(raw_options)
        ]

        # Check if question or options are too long
        q_fits      = len(question) <= TELEGRAM_Q_LIMIT
        answers_fit = not options_too_long(labeled_options)

        if q_fits and answers_fit:
            poll_kwargs = dict(
                chat_id=user_id,
                question=question,
                options=labeled_options,
                type="quiz",
                correct_option_id=correct_index,
                is_anonymous=True,
            )
            if poll.explanation:
                poll_kwargs["explanation"] = poll.explanation[:TELEGRAM_EX_LIMIT]
            await context.bot.send_poll(**poll_kwargs)

        elif not q_fits and answers_fit:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📋 <b>السؤال:</b>\n{question}",
                parse_mode=ParseMode.HTML,
            )
            poll_kwargs = dict(
                chat_id=user_id,
                question=".",
                options=labeled_options,
                type="quiz",
                correct_option_id=correct_index,
                is_anonymous=True,
            )
            if poll.explanation:
                poll_kwargs["explanation"] = poll.explanation[:TELEGRAM_EX_LIMIT]
            await context.bot.send_poll(**poll_kwargs)

        else:
            answer_lines = "\n".join(
                f"{'✅ ' if i == correct_index else ''}"
                f"{string.ascii_uppercase[i]}) {opt}"
                for i, opt in enumerate(raw_options)
            )
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📋 <b>السؤال:</b>\n{question}\n\n<b>الإجابات:</b>\n{answer_lines}",
                parse_mode=ParseMode.HTML,
            )
            short_q     = "."
            letter_opts = make_letter_only_options(len(raw_options))
            poll_kwargs = dict(
                chat_id=user_id,
                question=short_q,
                options=letter_opts,
                type="quiz",
                correct_option_id=correct_index,
                is_anonymous=True,
            )
            if poll.explanation:
                poll_kwargs["explanation"] = poll.explanation[:TELEGRAM_EX_LIMIT]
            await context.bot.send_poll(**poll_kwargs)

        return

    # ── PDF mode: save poll to buffer ───────────────────────────
    question      = poll.question
    raw_options   = [strip_leading_letter_prefix(opt.text) for opt in poll.options]
    correct_index = poll.correct_option_id if poll.correct_option_id is not None else 0

    labeled_options = [
        f"{string.ascii_uppercase[i]}) {opt}"
        for i, opt in enumerate(raw_options)
    ]

    PDF_BUFFER[user_id].append({
        "type":    "mcq",
        "q":       question,
        "options": labeled_options,
        "correct": correct_index,
    })

    await update_progress(
        context, user_id, update.effective_chat.id,
        latest_label=question[:50] + ("…" if len(question) > 50 else ""),
    )

# ═══════════════════════════════════════════════════════════════
# IMAGE HANDLER (PDF mode only)
# ═══════════════════════════════════════════════════════════════
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_chat.id
    if user_id in SLEEPING:
        return

    if user_id not in PDF_BUFFER:
        return   # silently ignore images outside PDF mode

    photo   = update.message.photo[-1] if update.message.photo else None
    if not photo:
        return

    caption = update.message.caption or ""

    img_dir = f"/tmp/quizician_imgs/{user_id}"
    os.makedirs(img_dir, exist_ok=True)

    img_count = sum(1 for i in PDF_BUFFER[user_id] if i["type"] == "image")
    img_path  = os.path.join(img_dir, f"img_{img_count + 1}.jpg")

    tg_file = await context.bot.get_file(photo.file_id)
    await tg_file.download_to_drive(img_path)

    PDF_BUFFER[user_id].append({
        "type":    "image",
        "path":    img_path,
        "caption": caption,
    })

    await update_progress(
        context, user_id, update.effective_chat.id,
        latest_label=f"Image{(' — ' + caption) if caption else ''}",
    )

# ═══════════════════════════════════════════════════════════════
# TEXT MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_chat.id
    if user_id in SLEEPING:
        return

    text = update.message.text.strip()

    # ── AWAITING PDF NAME ────────────────────────────────────────
    if AWAITING_NAME.get(user_id):
        name = text.strip()
        PDF_NAMES[user_id]  = name
        PDF_BUFFER[user_id] = []
        PROGRESS_MSG_ID.pop(user_id, None)
        del AWAITING_NAME[user_id]
        await update.message.reply_text(
            f"📥 <b>PDF mode activated</b> — File name: <i>{name}</i>\n\n"
            "• ابعت أسئلة نصية (MCQ أو مكتوبة)\n"
            "• أو <b>فوروارد</b> كويزات أو صور/جداول مقارنة\n\n"
            "اضغط <b>Export as PDF</b> أو <b>Export as DOCX</b> لما تخلص 👇",
            parse_mode=ParseMode.HTML,
        )
        return

    in_pdf_mode = user_id in PDF_BUFFER

    try:
        blocks = re.split(r"\n\s*\n", text)

        if not in_pdf_mode and len(blocks) > MAX_QUESTIONS_PER_MSG:
            await update.message.reply_text(
                f"❌ الحد الأقصى {MAX_QUESTIONS_PER_MSG} سؤال في المرة الواحدة"
            )
            return

        any_saved    = False
        last_label   = ""

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # ── WRITTEN ─────────────────────────────────────────
            if in_pdf_mode:
                written = parse_written_question(block)
            else:
                written = parse_written_strict(block)

            if written:
                title, content = written
                if in_pdf_mode:
                    PDF_BUFFER[user_id].append({
                        "type":    "written",
                        "title":   title,
                        "content": content,
                    })
                    any_saved  = True
                    last_label = title[:50] + ("…" if len(title) > 50 else "")
                else:
                    await update.message.reply_text(
                        f"*{title}*\n||{content}||",
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
                continue

            # ── MCQ ─────────────────────────────────────────────
            lines = normalize_mcq_block(block)
            if len(lines) < 3:
                if not in_pdf_mode:
                    await update.message.reply_text(
                        "⚠️ <b>الصياغة غلط!</b>\n\n"
                        "الشكل الصح هو:\n"
                        "<code>السؤال\n"
                        "a) خيار 1\n"
                        "b) خيار 2 z  ← علّم الصح بـ z\n"
                        "c) خيار 3\n"
                        "ex: الشرح (اختياري)</code>",
                        parse_mode=ParseMode.HTML,
                    )
                continue

            question      = lines[0]
            options       = []
            correct_index = None
            explanation   = None  # from ex: line

            for line in lines[1:]:
                # Check for ex: explanation line
                ex_match = re.match(r"^ex:\s*(.+)", line, re.IGNORECASE)
                if ex_match:
                    explanation = ex_match.group(1).strip()
                    continue

                opt       = clean_option(line)
                has_z_end = re.search(r"\s+[zZ]\s*$", opt)
                has_check = "✅" in opt

                if has_z_end or has_check:
                    opt           = opt.replace("✅", "")
                    opt           = re.sub(r"\s+[zZ]\s*$", "", opt).strip()
                    correct_index = len(options)

                if opt:
                    options.append(opt)

            raw_options = options[:]  # keep unformatted for text fallback

            options = [
                f"{string.ascii_uppercase[i]}) {opt}"
                for i, opt in enumerate(options)
            ]

            if correct_index is None or correct_index >= len(options):
                if not in_pdf_mode:
                    await update.message.reply_text(
                        "⚠️ <b>ما فيش إجابة صح!</b>\n\n"
                        "علّم الإجابة الصحيحة بـ <code>z</code> في نهايتها:\n"
                        "<code>b) الإجابة الصح z</code>",
                        parse_mode=ParseMode.HTML,
                    )
                continue

            # ── PDF MODE ────────────────────────────────────────
            if in_pdf_mode:
                PDF_BUFFER[user_id].append({
                    "type":    "mcq",
                    "q":       question,
                    "options": options,
                    "correct": correct_index,
                })
                any_saved  = True
                last_label = question[:50] + ("…" if len(question) > 50 else "")
                continue

            # ── NORMAL QUIZ MODE ─────────────────────────────────
            # Determine overflow situation
            q_fits       = len(question) <= TELEGRAM_Q_LIMIT
            answers_fit  = not options_too_long(options)

            if q_fits and answers_fit:
                # ── Case 1: Everything fits — send normally ──────
                main_q, desc_overflow = split_question_for_telegram(question)

                poll_kwargs = dict(
                    chat_id=user_id,
                    question=main_q,
                    options=options,
                    type="quiz",
                    correct_option_id=correct_index,
                    is_anonymous=True,
                )
                if desc_overflow:
                    poll_kwargs["question_parse_mode"] = None
                    # Send overflow as a separate message before the poll
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📋 <b>تكملة السؤال:</b>\n{desc_overflow}",
                        parse_mode=ParseMode.HTML,
                    )
                if explanation:
                    ex_trimmed = explanation[:TELEGRAM_EX_LIMIT]
                    poll_kwargs["explanation"] = ex_trimmed

                await context.bot.send_poll(**poll_kwargs)

            elif not q_fits and answers_fit:
                # ── Case 2: Question too long, answers OK ────────
                # Send full question as text only (no answers — they'll appear in poll)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📋 <b>السؤال:</b>\n{question}",
                    parse_mode=ParseMode.HTML,
                )
                # Poll question: just a dot — full question already sent as text
                poll_kwargs = dict(
                    chat_id=user_id,
                    question=".",
                    options=options,
                    type="quiz",
                    correct_option_id=correct_index,
                    is_anonymous=True,
                )
                if explanation:
                    poll_kwargs["explanation"] = explanation[:TELEGRAM_EX_LIMIT]
                await context.bot.send_poll(**poll_kwargs)

            else:
                # ── Case 3: Both question AND answers too long ───
                # Send full question + full answers (one per line), poll has A/B/C/D only
                answer_lines = "\n".join(
                    f"{'✅ ' if i == correct_index else ''}"
                    f"{string.ascii_uppercase[i]}) {opt}"
                    for i, opt in enumerate(raw_options)
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📋 <b>السؤال:</b>\n{question}\n\n<b>الإجابات:</b>\n{answer_lines}",
                    parse_mode=ParseMode.HTML,
                )
                short_q      = "."
                letter_opts  = make_letter_only_options(len(raw_options))
                poll_kwargs  = dict(
                    chat_id=user_id,
                    question=short_q,
                    options=letter_opts,
                    type="quiz",
                    correct_option_id=correct_index,
                    is_anonymous=True,
                )
                if explanation:
                    poll_kwargs["explanation"] = explanation[:TELEGRAM_EX_LIMIT]
                await context.bot.send_poll(**poll_kwargs)

            await react_random(update, context)

        # After all blocks in PDF mode — update the single progress message
        if in_pdf_mode and any_saved:
            await update_progress(context, user_id, update.effective_chat.id, last_label)

    except Exception as e:
        print("ERROR:", e)

# ═══════════════════════════════════════════════════════════════
# INLINE BUTTON HANDLER
# ═══════════════════════════════════════════════════════════════
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # ── START MENU BUTTONS ──────────────────────────────────────
    if query.data == "menu_how":
        await query.message.reply_text(HOW_TO_USE_TEXT, parse_mode=ParseMode.HTML)
        return

    if query.data == "menu_updates":
        await query.message.reply_text(LATEST_UPDATES_TEXT, parse_mode=ParseMode.HTML)
        return

    if query.data == "menu_pdf":
        await query.message.reply_text(PDF_MODE_GUIDE_TEXT, parse_mode=ParseMode.HTML)
        return

    # ── EXPORT BUTTONS ──────────────────────────────────────────
    items = PDF_BUFFER.get(user_id, [])
    name  = PDF_NAMES.get(user_id, "questions")
    safe  = re.sub(r"[^\w\s\-]", "", name).strip().replace(" ", "_") or "questions"

    if query.data == "gen_pdf":
        if not items:
            await query.message.reply_text("❌ لا يوجد أسئلة محفوظة بعد")
            return
        await query.message.reply_text(f"⏳ جاري توليد PDF لـ {len(items)} عنصر...")
        pdf = build_pdf(items, name)
        await query.message.reply_document(
            document=pdf, filename=f"{safe}.pdf",
            caption=f"📄 {len(items)} سؤال — {name} ❤️",
        )
        _cleanup_images(user_id)
        PDF_BUFFER.pop(user_id, None)
        PDF_NAMES.pop(user_id, None)
        PROGRESS_MSG_ID.pop(user_id, None)

    elif query.data == "gen_docx":
        if not items:
            await query.message.reply_text("❌ لا يوجد أسئلة محفوظة بعد")
            return
        await query.message.reply_text(f"⏳ جاري توليد DOCX لـ {len(items)} عنصر...")
        try:
            docx_buf = build_docx(items, name)
            await query.message.reply_document(
                document=docx_buf, filename=f"{safe}.docx",
                caption=f"📝 {len(items)} سؤال — {name} ❤️",
            )
            _cleanup_images(user_id)
            PDF_BUFFER.pop(user_id, None)
            PDF_NAMES.pop(user_id, None)
            PROGRESS_MSG_ID.pop(user_id, None)
        except Exception as e:
            print("DOCX ERROR:", e)
            await query.message.reply_text(
                f"❌ خطأ في توليد الـ DOCX:\n<code>{e}</code>",
                parse_mode=ParseMode.HTML,
            )

    elif query.data == "clear_pdf":
        _cleanup_images(user_id)
        PDF_BUFFER.pop(user_id, None)
        PDF_NAMES.pop(user_id, None)
        AWAITING_NAME.pop(user_id, None)
        PROGRESS_MSG_ID.pop(user_id, None)
        await query.message.reply_text("🗑 تم مسح كل الأسئلة المحفوظة")

# ═══════════════════════════════════════════════════════════════
# PDF COMMANDS
# ═══════════════════════════════════════════════════════════════
async def pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    _cleanup_images(user_id)
    PDF_BUFFER.pop(user_id, None)
    PDF_NAMES.pop(user_id, None)
    PROGRESS_MSG_ID.pop(user_id, None)
    AWAITING_NAME[user_id] = True
    await update.message.reply_text(
        "✏️ <b>اكتب اسم الملف اللي عايزه:</b>\n"
        "<i>Lecture 1 Anatomy Questions</i>",
        parse_mode=ParseMode.HTML,
    )

async def pdf_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    items   = PDF_BUFFER.get(user_id, [])
    if not items:
        await update.message.reply_text("❌ لا يوجد أسئلة محفوظة")
        return
    name = PDF_NAMES.get(user_id, "questions")
    safe = re.sub(r"[^\w\s\-]", "", name).strip().replace(" ", "_") or "questions"
    await update.message.reply_text(f"⏳ جاري توليد PDF لـ {len(items)} عنصر...")
    pdf = build_pdf(items, name)
    await update.message.reply_document(
        document=pdf, filename=f"{safe}.pdf",
        caption=f"📄 {len(items)} سؤال — {name} ❤️",
    )
    _cleanup_images(user_id)
    PDF_BUFFER.pop(user_id, None)
    PDF_NAMES.pop(user_id, None)
    PROGRESS_MSG_ID.pop(user_id, None)

async def pdf_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    _cleanup_images(user_id)
    PDF_BUFFER.pop(user_id, None)
    PDF_NAMES.pop(user_id, None)
    AWAITING_NAME.pop(user_id, None)
    PROGRESS_MSG_ID.pop(user_id, None)
    await update.message.reply_text("🗑 تم قرار إزالة")

# ═══════════════════════════════════════════════════════════════
# START  (also wakes bot from sleep)
# ═══════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    SLEEPING.discard(chat_id)

    if chat_id not in USERS:
        USERS.add(chat_id)
        save_users()

    await update.message.reply_text(
        "❤️<b>بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</b>\n"
        "<b>منور يا كويزاوي 🌹</b>\n\n"
        "Choose an option below to get started:",
        parse_mode=ParseMode.HTML,
        reply_markup=start_menu_keyboard(),
    )

# ═══════════════════════════════════════════════════════════════
# ADMIN HELPERS
# ═══════════════════════════════════════════════════════════════
def is_admin(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == ADMIN_ID

async def admincheck_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else "?"
    if is_admin(update):
        await update.message.reply_text(
            f"✅ <b>أنت الأدمن!</b>\n"
            f"🆔 Your ID: <code>{uid}</code>\n"
            f"👥 Total users: <b>{len(USERS)}</b>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"🚫 مش أدمن\n🆔 Your ID: <code>{uid}</code>",
            parse_mode=ParseMode.HTML,
        )

# ═══════════════════════════════════════════════════════════════
# BROADCAST COMMAND  (admin only)
# ═══════════════════════════════════════════════════════════════
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🚫 هذا الأمر للأدمن فقط")
        return

    # Message text comes after /broadcast, or from a replied-to message
    if context.args:
        text = " ".join(context.args)
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        text = update.message.reply_to_message.text
    else:
        await update.message.reply_text(
            "⚠️ استخدام:\n"
            "<code>/broadcast رسالتك هنا</code>\n\n"
            "أو رد بـ /broadcast على رسالة موجودة.",
            parse_mode=ParseMode.HTML,
        )
        return

    if not text.strip():
        await update.message.reply_text("❌ الرسالة فارغة")
        return

    users_list = list(USERS)
    total      = len(users_list)

    status_msg = await update.message.reply_text(
        f"📡 <b>جاري الإرسال لـ {total} مستخدم...</b>",
        parse_mode=ParseMode.HTML,
    )

    success = 0
    failed  = 0
    blocked = []

    for uid in users_list:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            success += 1
        except Exception as e:
            failed += 1
            blocked.append(uid)
            print(f"Broadcast failed for {uid}: {e}")

    # Remove users who blocked the bot
    if blocked:
        for uid in blocked:
            USERS.discard(uid)
        save_users()

    summary = (
        f"✅ <b>Broadcast اتبعت!</b>\n\n"
        f"👥 المستخدمين: <b>{total}</b>\n"
        f"✔️ نجح: <b>{success}</b>\n"
        f"❌ فشل / بلوك: <b>{failed}</b>"
    )
    if blocked:
        summary += f"\n🗑 تم حذف {len(blocked)} يوزر بلوك البوت من القائمة"

    await status_msg.edit_text(summary, parse_mode=ParseMode.HTML)

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start",        start))
app.add_handler(CommandHandler("sleep",        sleep_cmd))
app.add_handler(CommandHandler("admincheck",   admincheck_cmd))
app.add_handler(CommandHandler("broadcast",    broadcast_cmd))
app.add_handler(CommandHandler("pdf_start",    pdf_start))
app.add_handler(CommandHandler("pdf_generate", pdf_generate))
app.add_handler(CommandHandler("pdf_clear",    pdf_clear))

# Poll handler before text handler (forwarded OR own quiz polls)
app.add_handler(MessageHandler(filters.POLL, handle_poll))

# Image handler (photos in PDF mode)
app.add_handler(MessageHandler(filters.PHOTO, handle_image))

# Inline buttons
app.add_handler(CallbackQueryHandler(button_handler))

# Text handler last
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running... V5.5")
app.run_polling()
