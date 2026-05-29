import re
import string
import random
import json
import os
import subprocess
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

NPM_MODULES_DIR = "/home/claude/.npm-global/lib/node_modules"
BOT_TOKEN       = "8661732123:AAFZ-NZjhNyZQz75j0u4Rv9syFEo9twmisY"

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
PDF_BUFFER    = {}   # user_id -> list of item dicts
PDF_NAMES     = {}   # user_id -> str
AWAITING_NAME = {}   # user_id -> True
SLEEPING      = set()  # user_ids that are muted with /sleep

# ═══════════════════════════════════════════════════════════════
# DHIKR
# ═══════════════════════════════════════════════════════════════
dhikr_list = [
    "صلي على النبي ﷺ",
    "سبحان الله وبحمده، سبحان الله العظيم",
    "لا حول ولا قوة إلا بالله",
    "لا إله إلا الله، محمد رسول الله",
]

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
MAX_QUESTIONS_PER_MSG = 40
TELEGRAM_Q_LIMIT      = 300
PDF_MAX_IMG_WIDTH     = 13 * cm   # max image width in PDF (fits A4 with 2cm margins)

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
    """Remove Telegram spoiler markers ||...|| and return clean text."""
    return re.sub(r"\|\|(.+?)\|\|", r"\1", text, flags=re.DOTALL)

def parse_written_question(block: str):
    """
    Accepts written questions in two formats:

    FORMAT A (original):
        Title
        .answer content.

    FORMAT B (spoiler / forwarded style):
        Title ""               ← title line (may end with " or quotes)
        ||hidden answer text||  ← one or more spoiler lines
        OR plain lines after title

    In PDF mode we also accept a relaxed format:
        Title
        any content (no dot requirement)
    Returns (title, content) or None.
    """
    # First strip all spoiler markers from the whole block
    block = strip_spoiler_markers(block)
    lines = [l.rstrip() for l in block.split("\n") if l.strip()]

    if len(lines) < 2:
        return None

    # Clean title: remove trailing quotes/speech marks that Telegram adds
    title = re.sub(r'[\""\']+$', "", lines[0]).strip()
    content_lines = lines[1:]
    content = "\n".join(content_lines).strip()

    if not content:
        return None

    # FORMAT A: dot-wrapped content  .content.
    if content.startswith(".") and content.endswith("."):
        content = content[1:-1].strip()
        return title, content

    # FORMAT B (PDF mode only): relaxed — title + any content lines
    # We detect this if the title looks like a question/header
    # (doesn't start with a letter-option pattern like "A)" or "a.")
    # and there are content lines present.
    # We return it so PDF mode can use it; normal mode will ignore it
    # (it won't match FORMAT A so normal mode still requires dots).
    if content:
        return title, content

    return None

def parse_written_strict(block: str):
    """Strict version — only FORMAT A (dot-wrapped). Used in normal (non-PDF) mode."""
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
    if len(question) <= TELEGRAM_Q_LIMIT:
        return question, None
    cutoff    = TELEGRAM_Q_LIMIT - 3
    split_pos = question.rfind(". ", 0, cutoff)
    if split_pos == -1:
        split_pos = question.rfind(" ", 0, cutoff)
    if split_pos == -1:
        split_pos = cutoff
    main     = question[:split_pos].strip() + "…"
    overflow = "…" + question[split_pos:].strip()
    return main, overflow

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
            # Embed image, scaled to fit page width
            img_path = item["path"]
            try:
                img = RLImage(img_path)
                # Scale proportionally to fit within PDF_MAX_IMG_WIDTH
                if img.imageWidth > PDF_MAX_IMG_WIDTH:
                    scale = PDF_MAX_IMG_WIDTH / img.imageWidth
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
# DOCX BUILDER
# ═══════════════════════════════════════════════════════════════
JS_TEMPLATE = r"""
const { Document, Packer, Paragraph, TextRun, BorderStyle, TabStopType,
        ImageRun, AlignmentType } = require('docx');
const fs   = require('fs');
const path = require('path');

const items   = JSON.parse(process.env.QUESTIONS_JSON);
const outPath = process.env.OUT_PATH;

const CYAN_C   = "00BCD4";
const PURPLE_C = "7B1FA2";
const GREEN_C  = "1B5E20";
const DARK_C   = "1A1A2E";
const GRAY_C   = "546E7A";
const RULE_C   = "CFD8DC";
const CONTENT_W = 9026;

function headerParagraph() {
    return new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }],
        children: [
            new TextRun({ text: "MDM44 | Notes & Files", bold: true,
                          color: CYAN_C, size: 18, font: "Arial" }),
            new TextRun({ text: "\tMade by The Quizician", bold: true,
                          color: PURPLE_C, size: 18, font: "Arial" }),
        ],
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE_C, space: 4 } },
        spacing: { after: 160 },
    });
}

function hrParagraph() {
    return new Paragraph({
        children: [],
        border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: RULE_C, space: 1 } },
        spacing: { before: 80, after: 80 },
    });
}

const children = [headerParagraph()];

items.forEach((item, idx) => {
    children.push(new Paragraph({
        children: [new TextRun({ text: `Q${idx + 1}`, bold: true,
                                 color: "90A4AE", size: 18, font: "Arial" })],
        spacing: { before: 200, after: 40 },
    }));

    if (item.type === "mcq") {
        children.push(new Paragraph({
            children: [new TextRun({ text: item.q, bold: true,
                                     color: DARK_C, size: 24, font: "Arial" })],
            spacing: { after: 80 },
        }));
        item.options.forEach((opt, i) => {
            const correct = (i === item.correct);
            children.push(new Paragraph({
                children: [new TextRun({
                    text: (correct ? "✓  " : "     ") + opt,
                    bold: correct,
                    color: correct ? GREEN_C : DARK_C,
                    size: 22, font: "Arial",
                })],
                indent: { left: 280 },
                spacing: { after: 60 },
            }));
        });

    } else if (item.type === "written") {
        children.push(new Paragraph({
            children: [new TextRun({ text: item.title, bold: true,
                                     color: DARK_C, size: 24, font: "Arial" })],
            spacing: { after: 80 },
        }));
        item.content.split("\n").forEach(line => {
            line = line.trim();
            if (line) {
                children.push(new Paragraph({
                    children: [new TextRun({ text: "• " + line,
                                             color: GRAY_C, size: 22, font: "Arial" })],
                    indent: { left: 280 },
                    spacing: { after: 60 },
                }));
            }
        });

    } else if (item.type === "image" && item.path && fs.existsSync(item.path)) {
        try {
            const imgData = fs.readFileSync(item.path);
            const ext = path.extname(item.path).toLowerCase().replace(".", "");
            const typeMap = { jpg: "jpg", jpeg: "jpg", png: "png", gif: "gif", bmp: "bmp" };
            const imgType = typeMap[ext] || "png";
            children.push(new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new ImageRun({
                    data: imgData,
                    transformation: { width: 500, height: 350 },
                    type: imgType,
                })],
                spacing: { before: 100, after: 60 },
            }));
            if (item.caption) {
                children.push(new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "📷 " + item.caption,
                                             color: "78909C", size: 18,
                                             italics: true, font: "Arial" })],
                    spacing: { after: 80 },
                }));
            }
        } catch(e) {
            children.push(new Paragraph({
                children: [new TextRun({ text: "[Image error: " + e.message + "]",
                                         color: "B71C1C", size: 20, font: "Arial" })],
            }));
        }
    }

    if (idx < items.length - 1) children.push(hrParagraph());
});

const doc = new Document({
    sections: [{
        properties: {
            page: {
                size:   { width: 11906, height: 16838 },
                margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 },
            },
        },
        children,
    }],
});

Packer.toBuffer(doc)
    .then(buf => { fs.writeFileSync(outPath, buf); console.log("OK"); })
    .catch(e  => { console.error("ERR:", e.message); process.exit(1); });
"""

def build_docx(items: list, doc_title: str = "questions") -> BytesIO:
    with tempfile.TemporaryDirectory() as tmpdir:
        nm_link = os.path.join(tmpdir, "node_modules")
        os.symlink(NPM_MODULES_DIR, nm_link)

        script_path = os.path.join(tmpdir, "gen.js")
        out_path    = os.path.join(tmpdir, "output.docx")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(JS_TEMPLATE)

        env = os.environ.copy()
        env["QUESTIONS_JSON"] = json.dumps(items, ensure_ascii=False)
        env["OUT_PATH"]       = out_path

        result = subprocess.run(
            ["node", script_path],
            env=env, capture_output=True, text=True, timeout=30, cwd=tmpdir,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Unknown node error")

        with open(out_path, "rb") as f:
            return BytesIO(f.read())

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

async def react_fire(context, chat_id, message_id):
    try:
        await context.bot.set_message_reaction(
            chat_id=chat_id, message_id=message_id,
            reaction=[ReactionTypeEmoji("🔥")],
        )
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# SLEEP / WAKE COMMANDS
# ═══════════════════════════════════════════════════════════════
async def sleep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute the bot — it will silently ignore all messages until /start."""
    user_id = update.effective_chat.id
    SLEEPING.add(user_id)
    await update.message.reply_text(
        "😴 البوت هيستنى ولا يرد على أي رسالة.\n"
        "ابعت /start لما تحتاجه تاني."
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

    if user_id not in PDF_BUFFER:
        await update.message.reply_text(
            "ابدأ وضع PDF أولاً بـ /pdf_start ثم ابعت الأسئلة."
        )
        return

    poll          = update.message.poll
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

    count = len(PDF_BUFFER[user_id])
    await update.message.reply_text(
        f"✅ تم حفظ السؤال ({count} حتى الآن)",
        reply_markup=export_keyboard(),
    )

# ═══════════════════════════════════════════════════════════════
# IMAGE HANDLER (PDF mode only)
# ═══════════════════════════════════════════════════════════════
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download forwarded/sent images and embed them in the PDF buffer."""
    if not update.message:
        return

    user_id = update.effective_chat.id
    if user_id in SLEEPING:
        return

    # Only accept images in PDF mode
    if user_id not in PDF_BUFFER:
        return   # silently ignore images outside PDF mode

    # Get the best quality photo
    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        return

    # Caption becomes the image label in the PDF
    caption = update.message.caption or ""

    # Download image to a temp file (persist until PDF is generated)
    # We store images in a per-user temp dir
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

    count = len(PDF_BUFFER[user_id])
    await update.message.reply_text(
        f"🖼 تم حفظ الصورة ({count} حتى الآن)",
        reply_markup=export_keyboard(),
    )

# ═══════════════════════════════════════════════════════════════
# TEXT MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_chat.id
    if user_id in SLEEPING:
        return   # fully silent while sleeping

    text = update.message.text.strip()

    # ── AWAITING PDF NAME ────────────────────────────────────────
    if AWAITING_NAME.get(user_id):
        name = text.strip()
        PDF_NAMES[user_id]  = name
        PDF_BUFFER[user_id] = []
        del AWAITING_NAME[user_id]
        await update.message.reply_text(
            f"📥 <b>PDF mode activated</b> — File name: <i>{name}</i>\n\n"
            "• ابعت أسئلة نصية (MCQ أو مكتوبة)\n"
            "• أو <b>فوروارد</b> كويزات أو صور/جداول مقارنة\n\n"
            "اضغط <b>Export as PDF</b> أو <b>Export as DOCX</b> لما تخلص 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=export_keyboard(),
        )
        return

    # ── PDF MODE: accept relaxed written format ──────────────────
    in_pdf_mode = user_id in PDF_BUFFER

    try:
        blocks = re.split(r"\n\s*\n", text)

        if not in_pdf_mode and len(blocks) > MAX_QUESTIONS_PER_MSG:
            await update.message.reply_text(
                f"❌ الحد الأقصى {MAX_QUESTIONS_PER_MSG} سؤال في المرة الواحدة"
            )
            return

        any_saved = False

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # ── WRITTEN ─────────────────────────────────────────
            if in_pdf_mode:
                # Use relaxed parser in PDF mode (accepts spoiler format too)
                written = parse_written_question(block)
            else:
                # Use strict parser in normal mode (dots required)
                written = parse_written_strict(block)

            if written:
                title, content = written
                if in_pdf_mode:
                    PDF_BUFFER[user_id].append({
                        "type":    "written",
                        "title":   title,
                        "content": content,
                    })
                    any_saved = True
                else:
                    await update.message.reply_text(
                        f"*{title}*\n||{content}||",
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
                continue

            # ── MCQ ─────────────────────────────────────────────
            lines = normalize_mcq_block(block)
            if len(lines) < 3:
                continue   # silently skip — no error message

            question      = lines[0]
            options       = []
            correct_index = None

            for line in lines[1:]:
                opt       = clean_option(line)
                has_z_end = re.search(r"\s+[zZ]\s*$", opt)
                has_check = "✅" in opt

                if has_z_end or has_check:
                    opt           = opt.replace("✅", "")
                    opt           = re.sub(r"\s+[zZ]\s*$", "", opt).strip()
                    correct_index = len(options)

                if opt:
                    options.append(opt)

            options = [
                f"{string.ascii_uppercase[i]}) {opt}"
                for i, opt in enumerate(options)
            ]

            # Silently skip if no correct answer marked — no error message
            if correct_index is None or correct_index >= len(options):
                continue

            # ── PDF MODE ────────────────────────────────────────
            if in_pdf_mode:
                PDF_BUFFER[user_id].append({
                    "type":    "mcq",
                    "q":       question,
                    "options": options,
                    "correct": correct_index,
                })
                any_saved = True
                continue

            # ── NORMAL QUIZ MODE ─────────────────────────────────
            main_q, overflow = split_question_for_telegram(question)

            if overflow:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📋 <b>تكملة السؤال:</b>\n{overflow}",
                    parse_mode=ParseMode.HTML,
                )

            poll_msg = await context.bot.send_poll(
                chat_id=user_id,
                question=main_q,
                options=options,
                type="quiz",
                correct_option_id=correct_index,
                is_anonymous=True,
            )

            await react_fire(context, poll_msg.chat.id, poll_msg.message_id)
            await react_random(update, context)

            if random.randint(1, 10) <= 7:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=random.choice(dhikr_list),
                )

        # After processing all blocks in PDF mode, send ONE summary reply
        if in_pdf_mode and any_saved:
            count = len(PDF_BUFFER[user_id])
            await update.message.reply_text(
                f"✅ تم الحفظ ({count} عنصر حتى الآن)",
                reply_markup=export_keyboard(),
            )

    except Exception as e:
        print("ERROR:", e)
        # Silent fail — no error message to user unless in debug mode

# ═══════════════════════════════════════════════════════════════
# INLINE BUTTON HANDLER
# ═══════════════════════════════════════════════════════════════
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    user_id = query.from_user.id
    await query.answer()

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
        # Clean up downloaded images
        _cleanup_images(user_id)
        PDF_BUFFER.pop(user_id, None)
        PDF_NAMES.pop(user_id, None)

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
        await query.message.reply_text("🗑 تم مسح كل الأسئلة المحفوظة")

def _cleanup_images(user_id: int):
    """Remove downloaded images from disk after export."""
    import shutil
    img_dir = f"/tmp/quizician_imgs/{user_id}"
    if os.path.exists(img_dir):
        shutil.rmtree(img_dir, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════
# PDF COMMANDS
# ═══════════════════════════════════════════════════════════════
async def pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    _cleanup_images(user_id)
    PDF_BUFFER.pop(user_id, None)
    PDF_NAMES.pop(user_id, None)
    AWAITING_NAME[user_id] = True
    await update.message.reply_text(
        "✏️ <b>اكتب اسم الملف اللي عايزه:</b>\n"
        "<i>مثال: فيزياء الفصل الدراسي الأول</i>",
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

async def pdf_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    _cleanup_images(user_id)
    PDF_BUFFER.pop(user_id, None)
    PDF_NAMES.pop(user_id, None)
    AWAITING_NAME.pop(user_id, None)
    await update.message.reply_text("🗑 تم مسح الأسئلة المحفوظة")

# ═══════════════════════════════════════════════════════════════
# START  (also wakes bot from sleep)
# ═══════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    SLEEPING.discard(chat_id)   # wake up if sleeping

    if chat_id not in USERS:
        USERS.add(chat_id)
        save_users()

    await update.message.reply_text(
        "❤️ <b>بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</b> ❤️\n"
        "<b><i>منور يا كويزاوي 🌹</i></b>",
        parse_mode=ParseMode.HTML,
    )
    await update.message.reply_text(
        "📚 <b>Ways to use the bot:</b>\n\n"
        "1) Normal MCQ:\n"
        "Question?\n"
        "a) A\n"
        "b) B z   ← correct answer\n"
        "c) C\n\n"
        "2) Single-line MCQ:\n"
        "Question? a) A b) B z c) C\n\n"
        "3) Written Questions:\n"
        "Title\n"
        ".answer line 1\n"
        "answer line 2.\n\n"
        "4) PDF / DOCX Mode:\n"
        "• /pdf_start — اكتب اسم الملف، ثم:\n"
        "  – ابعت MCQ أو أسئلة مكتوبة\n"
        "  – فوروارد كويزات قديمة\n"
        "  – ابعت صور / جداول مقارنة\n"
        "  – فوروارد رسائل فيها spoilers\n"
        "• اضغط <b>Export as PDF</b> أو <b>Export as DOCX</b>\n"
        "• /pdf_clear — إلغاء\n\n"
        "😴 /sleep — البوت يصمت لحد ما تبعت /start",
        parse_mode=ParseMode.HTML,
    )
    await update.message.reply_text(
        "🆕 <b>Latest Updates — V5.2</b>\n"
        "• 😴 /sleep command — البوت يصمت تماماً\n"
        "  /start يصحيه تاني\n"
        "• 🖼 PDF/DOCX يقبل صور وجداول مقارنة\n"
        "• 📝 تحسين التعرف على الأسئلة المكتوبة\n"
        "  (يقبل spoiler format والأسئلة المعاد توجيهها)\n"
        "• 🔇 إزالة رسالة الخطأ للأسئلة بدون إجابة صح\n\n"
        "❤ صلي على النبي ❤",
        parse_mode=ParseMode.HTML,
    )

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start",        start))
app.add_handler(CommandHandler("sleep",        sleep_cmd))
app.add_handler(CommandHandler("pdf_start",    pdf_start))
app.add_handler(CommandHandler("pdf_generate", pdf_generate))
app.add_handler(CommandHandler("pdf_clear",    pdf_clear))

# Poll handler before text handler
app.add_handler(MessageHandler(filters.FORWARDED & filters.POLL, handle_poll))

# Image handler (photos in PDF mode)
app.add_handler(MessageHandler(filters.PHOTO, handle_image))

# Inline buttons
app.add_handler(CallbackQueryHandler(button_handler))

# Text handler last
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running... V5.2")
app.run_polling()
