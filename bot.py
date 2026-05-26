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

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Frame, PageTemplate
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# ═══════════════════════════════════════════════════════════════
# FONT SETUP
# ═══════════════════════════════════════════════════════════════
FONT_NAME      = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"

if os.path.exists("comic.ttf"):
    try:
        pdfmetrics.registerFont(TTFont("ComicSans", "comic.ttf"))
        FONT_NAME      = "ComicSans"
        FONT_NAME_BOLD = "ComicSans"
        print("✅ Comic Sans loaded")
    except Exception as e:
        print(f"⚠️  Could not load comic.ttf: {e} — using Helvetica")
else:
    print("ℹ️  comic.ttf not found — using Helvetica.")

BOT_TOKEN = "8661732123:AAEkdln3xbp0EJiNBCKYChH0A8ioCYkSNic"

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
# PDF MEMORY  +  STATE MACHINE
# ═══════════════════════════════════════════════════════════════
PDF_BUFFER    = {}   # user_id -> list of question dicts
PDF_NAMES     = {}   # user_id -> str  (file name chosen by user)
AWAITING_NAME = {}   # user_id -> True  (waiting for name input)

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
# MAX quiz per message in normal mode
# ═══════════════════════════════════════════════════════════════
MAX_QUESTIONS_PER_MSG = 40

# Telegram poll question limit (300 chars) and description limit (200 chars)
TELEGRAM_Q_LIMIT = 300
TELEGRAM_DESC_LIMIT = 200

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def clean_option(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[A-Ea-e1-5][).\-]\s*", "", line)
    line = re.sub(r"^[-•]\s*", "", line)
    return line.strip()

def strip_leading_letter_prefix(option: str) -> str:
    """Remove A) B) C) D) E) prefix if already present."""
    return re.sub(r"^[A-Ea-e]\)\s*", "", option).strip()

def normalize_mcq_block(block: str):
    block = block.strip()
    if "\n" in block:
        return [l.strip() for l in block.split("\n") if l.strip()]
    match = re.search(r"\b([A-Ea-e1-5])[).]", block)
    if not match:
        return [block]
    question    = block[:match.start()].strip()
    options_part = block[match.start():]
    parts = re.split(r"(?=\b[A-Ea-e1-5][).])", options_part)
    return [question] + [p.strip() for p in parts if p.strip()]

def parse_written_question(block: str):
    lines = [l.rstrip() for l in block.split("\n") if l.strip()]
    if len(lines) < 2:
        return None
    title   = lines[0]
    content = "\n".join(lines[1:])
    if not (content.strip().startswith(".") and content.strip().endswith(".")):
        return None
    content = content.strip()[1:-1].strip()
    return title, content

def split_question_for_telegram(question: str):
    """
    If question exceeds Telegram's 300-char limit, split it:
    - First TELEGRAM_Q_LIMIT chars go into the question field
    - Remainder goes into explanation/description (shown after answer)
    Returns (main_question, description_or_None)
    """
    if len(question) <= TELEGRAM_Q_LIMIT:
        return question, None
    # Try to split at a sentence boundary near the limit
    cutoff = TELEGRAM_Q_LIMIT - 3  # leave room for "..."
    split_pos = question.rfind(". ", 0, cutoff)
    if split_pos == -1:
        split_pos = question.rfind(" ", 0, cutoff)
    if split_pos == -1:
        split_pos = cutoff
    main = question[:split_pos].strip()
    rest = question[split_pos:].strip()
    # Trim description to Telegram's limit
    if len(rest) > TELEGRAM_DESC_LIMIT:
        rest = rest[:TELEGRAM_DESC_LIMIT - 1].rsplit(" ", 1)[0] + "…"
    return main, rest

# ═══════════════════════════════════════════════════════════════
# KEYBOARD HELPERS
# ═══════════════════════════════════════════════════════════════
def generate_pdf_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 Export as PDF",  callback_data="gen_pdf"),
            InlineKeyboardButton("📝 Export as DOCX", callback_data="gen_docx"),
        ],
        [InlineKeyboardButton("🗑 Clear & Cancel", callback_data="clear_pdf")],
    ])

# ═══════════════════════════════════════════════════════════════
# PDF BUILDER  (with header)
# ═══════════════════════════════════════════════════════════════
def build_pdf(items: list, doc_title: str = "questions") -> BytesIO:
    buffer = BytesIO()

    LEFT_TEXT  = "MDM44 | NOTES"
    RIGHT_TEXT = "Made by The Quizician"
    LEFT_COLOR  = colors.HexColor("#00BCD4")   # Cyan
    RIGHT_COLOR = colors.HexColor("#7B1FA2")   # Purple

    # ── Header drawing function ──────────────────────────────────
    def draw_header(canvas, doc):
        canvas.saveState()
        # Left label — Cyan
        canvas.setFont(FONT_NAME_BOLD, 9)
        canvas.setFillColor(LEFT_COLOR)
        canvas.drawString(2*cm, A4[1] - 1.4*cm, LEFT_TEXT)
        # Right label — Purple
        canvas.setFillColor(RIGHT_COLOR)
        canvas.drawRightString(A4[0] - 2*cm, A4[1] - 1.4*cm, RIGHT_TEXT)
        # Thin separator line under header
        canvas.setStrokeColor(colors.HexColor("#CFD8DC"))
        canvas.setLineWidth(0.5)
        canvas.line(2*cm, A4[1] - 1.65*cm, A4[0] - 2*cm, A4[1] - 1.65*cm)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.4*cm, bottomMargin=2*cm,
        onFirstPage=draw_header,
        onLaterPages=draw_header,
    )

    # ── Styles ──────────────────────────────────────────────────
    Q_STYLE = ParagraphStyle(
        "QStyle",
        fontName=FONT_NAME_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1A1A2E"),
        spaceAfter=6,
        spaceBefore=14,
    )
    OPT_STYLE = ParagraphStyle(
        "OptStyle",
        fontName=FONT_NAME,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1A1A2E"),
        leftIndent=14,
        spaceAfter=3,
    )
    OPT_CORRECT = ParagraphStyle(
        "OptCorrect",
        fontName=FONT_NAME_BOLD,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1B5E20"),
        leftIndent=14,
        spaceAfter=3,
    )
    WRITTEN_TITLE = ParagraphStyle(
        "WTitle",
        fontName=FONT_NAME_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1A1A2E"),
        spaceAfter=4,
        spaceBefore=14,
    )
    WRITTEN_BODY = ParagraphStyle(
        "WBody",
        fontName=FONT_NAME,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#37474F"),
        leftIndent=14,
        spaceAfter=6,
    )
    NUM_STYLE = ParagraphStyle(
        "NumStyle",
        fontName=FONT_NAME_BOLD,
        fontSize=9,
        textColor=colors.HexColor("#90A4AE"),
        spaceAfter=2,
    )

    HR_COLOR = colors.HexColor("#CFD8DC")

    story = []
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

        if idx < len(items):
            story.append(Spacer(1, 6))
            story.append(HRFlowable(
                width="100%", thickness=0.5,
                color=HR_COLOR, spaceAfter=4
            ))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ═══════════════════════════════════════════════════════════════
# DOCX BUILDER  (via Node.js / docx npm)
# ═══════════════════════════════════════════════════════════════
def build_docx(items: list, doc_title: str = "questions") -> BytesIO:
    """Generate a .docx using the docx npm package via a temp Node script."""

    # Build JS-safe data structure
    questions_json = json.dumps(items, ensure_ascii=False)

    js_script = r"""
const { Document, Packer, Paragraph, TextRun, AlignmentType, BorderStyle,
        TabStopType, TabStopPosition } = require('docx');
const fs = require('fs');

const items = JSON.parse(process.env.QUESTIONS_JSON);
const outPath = process.env.OUT_PATH;

const LEFT_COLOR  = "00ACC1";  // cyan
const RIGHT_COLOR = "7B1FA2"; // purple
const GREEN_COLOR = "1B5E20";
const DARK_COLOR  = "1A1A2E";
const GRAY_COLOR  = "546E7A";

const CONTENT_WIDTH_DXA = 9026; // A4 with 2cm margins each side ≈ 9026 DXA

function headerParagraph() {
    return new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_WIDTH_DXA }],
        children: [
            new TextRun({
                text: "MDM44 | NOTES",
                bold: true,
                color: LEFT_COLOR,
                size: 18,
                font: "Arial",
            }),
            new TextRun({
                text: "\tMade by The Quizician",
                bold: true,
                color: RIGHT_COLOR,
                size: 18,
                font: "Arial",
            }),
        ],
        border: {
            bottom: { style: BorderStyle.SINGLE, size: 4, color: "CFD8DC", space: 4 }
        },
        spacing: { after: 160 },
    });
}

function hrParagraph() {
    return new Paragraph({
        children: [],
        border: {
            bottom: { style: BorderStyle.SINGLE, size: 2, color: "CFD8DC", space: 1 }
        },
        spacing: { before: 80, after: 80 },
    });
}

const children = [headerParagraph()];

items.forEach((item, idx) => {
    // Question number label
    children.push(new Paragraph({
        children: [new TextRun({ text: `Q${idx + 1}`, bold: true, color: "90A4AE", size: 18, font: "Arial" })],
        spacing: { before: 200, after: 40 },
    }));

    if (item.type === "mcq") {
        children.push(new Paragraph({
            children: [new TextRun({ text: item.q, bold: true, color: DARK_COLOR, size: 24, font: "Arial" })],
            spacing: { after: 80 },
        }));
        item.options.forEach((opt, i) => {
            const isCorrect = i === item.correct;
            children.push(new Paragraph({
                children: [new TextRun({
                    text: (isCorrect ? "✓  " : "     ") + opt,
                    bold: isCorrect,
                    color: isCorrect ? GREEN_COLOR : DARK_COLOR,
                    size: 22,
                    font: "Arial",
                })],
                indent: { left: 280 },
                spacing: { after: 60 },
            }));
        });
    } else if (item.type === "written") {
        children.push(new Paragraph({
            children: [new TextRun({ text: item.title, bold: true, color: DARK_COLOR, size: 24, font: "Arial" })],
            spacing: { after: 80 },
        }));
        item.content.split("\n").forEach(line => {
            line = line.trim();
            if (line) {
                children.push(new Paragraph({
                    numbering: { reference: "bullets", level: 0 },
                    children: [new TextRun({ text: line, color: GRAY_COLOR, size: 22, font: "Arial" })],
                    spacing: { after: 60 },
                }));
            }
        });
    }

    if (idx < items.length - 1) {
        children.push(hrParagraph());
    }
});

const doc = new Document({
    numbering: {
        config: [{
            reference: "bullets",
            levels: [{
                level: 0,
                format: "bullet",
                text: "•",
                alignment: AlignmentType.LEFT,
                style: { paragraph: { indent: { left: 720, hanging: 360 } } }
            }]
        }]
    },
    sections: [{
        properties: {
            page: {
                size: { width: 11906, height: 16838 },
                margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 }
            }
        },
        children,
    }]
});

Packer.toBuffer(doc).then(buf => {
    fs.writeFileSync(outPath, buf);
    console.log("OK");
});
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "gen.js")
        out_path    = os.path.join(tmpdir, "output.docx")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(js_script)

        env = os.environ.copy()
        env["QUESTIONS_JSON"] = questions_json
        env["OUT_PATH"]       = out_path
        # ensure docx module is findable
        env["NODE_PATH"] = os.path.expanduser("~/.npm-global/lib/node_modules")

        result = subprocess.run(
            ["node", script_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Node error: {result.stderr}")

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
    except:
        pass

async def react_fire(context, chat_id, message_id):
    try:
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[ReactionTypeEmoji("🔥")],
        )
    except:
        pass

# ═══════════════════════════════════════════════════════════════
# FORWARDED POLL HANDLER
# ═══════════════════════════════════════════════════════════════
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.poll:
        return

    user_id = update.effective_chat.id

    if user_id not in PDF_BUFFER:
        await update.message.reply_text(
            "ℹ️  ابدأ وضع PDF أولاً بـ /pdf_start ثم ابعت الأسئلة."
        )
        return

    poll = update.message.poll
    question = poll.question
    options  = [opt.text for opt in poll.options]

    correct_index = poll.correct_option_id
    if correct_index is None:
        correct_index = 0

    # ── FIX: strip existing A) B) C) prefix before re-labeling ──
    cleaned_options = [strip_leading_letter_prefix(opt) for opt in options]

    labeled_options = [
        f"{string.ascii_uppercase[i]}) {opt}"
        for i, opt in enumerate(cleaned_options)
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
        reply_markup=generate_pdf_keyboard(),
    )

# ═══════════════════════════════════════════════════════════════
# TEXT MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_chat.id
    text    = update.message.text.strip()

    # ── AWAITING PDF NAME ────────────────────────────────────────
    if AWAITING_NAME.get(user_id):
        name = text.strip()
        PDF_NAMES[user_id]    = name
        PDF_BUFFER[user_id]   = []
        del AWAITING_NAME[user_id]
        await update.message.reply_text(
            f"📥 <b>PDF mode Activated</b> — File name: <i>{name}</i>\n\n"
            "• ابعت أسئلة نصية (MCQ أو مكتوبة)\n"
            "• أو <b>فوروارد</b> كويزات سبق ما الـ Bot بعتها\n\n"
            "اضغط <b>Export as PDF</b> أو <b>Export as DOCX</b> لما تخلص 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=generate_pdf_keyboard(),
        )
        return

    try:
        blocks = re.split(r"\n\s*\n", text)

        if len(blocks) > MAX_QUESTIONS_PER_MSG:
            await update.message.reply_text(f"❌ الحد الأقصى {MAX_QUESTIONS_PER_MSG} سؤال في المرة الواحدة")
            return

        for block in blocks:

            # ── WRITTEN ─────────────────────────────────────────
            written = parse_written_question(block)
            if written:
                title, content = written

                if user_id in PDF_BUFFER:
                    PDF_BUFFER[user_id].append({
                        "type":    "written",
                        "title":   title,
                        "content": content,
                    })
                    count = len(PDF_BUFFER[user_id])
                    await update.message.reply_text(
                        f"📝 تم حفظ سؤال مكتوب ({count} حتى الآن)",
                        reply_markup=generate_pdf_keyboard(),
                    )
                else:
                    await update.message.reply_text(
                        f"*{title}*\n||{content}||",
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
                continue

            # ── MCQ ─────────────────────────────────────────────
            lines = normalize_mcq_block(block)
            if len(lines) < 3:
                continue

            question      = lines[0]
            options       = []
            correct_index = None

            for line in lines[1:]:
                opt = clean_option(line)
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

            if correct_index is None or correct_index >= len(options):
                await update.message.reply_text("❌ مفيش إجابة صح محددة")
                continue

            # ── PDF MODE ────────────────────────────────────────
            if user_id in PDF_BUFFER:
                PDF_BUFFER[user_id].append({
                    "type":    "mcq",
                    "q":       question,
                    "options": options,
                    "correct": correct_index,
                })
                count = len(PDF_BUFFER[user_id])
                await update.message.reply_text(
                    f"🧠 تم حفظ السؤال ({count} حتى الآن)",
                    reply_markup=generate_pdf_keyboard(),
                )
                continue

            # ── NORMAL QUIZ MODE ─────────────────────────────────
            # Split long questions across question + explanation fields
            main_q, description = split_question_for_telegram(question)

            poll_kwargs = dict(
                chat_id=user_id,
                question=main_q,
                options=options,
                type="quiz",
                correct_option_id=correct_index,
                is_anonymous=True,
            )
            if description:
                poll_kwargs["explanation"] = description

            poll_msg = await context.bot.send_poll(**poll_kwargs)

            await react_fire(context, poll_msg.chat.id, poll_msg.message_id)
            await react_random(update, context)

            if random.randint(1, 10) <= 7:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=random.choice(dhikr_list),
                )

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌ خطأ في التنسيق")

# ═══════════════════════════════════════════════════════════════
# INLINE BUTTON HANDLER
# ═══════════════════════════════════════════════════════════════
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    items = PDF_BUFFER.get(user_id, [])
    name  = PDF_NAMES.get(user_id, "questions")

    if query.data == "gen_pdf":
        if not items:
            await query.message.reply_text("❌ لا يوجد أسئلة محفوظة بعد")
            return
        await query.message.reply_text(f"⏳ جاري توليد PDF لـ {len(items)} سؤال...")
        pdf = build_pdf(items, name)
        safe_name = re.sub(r'[^\w\s\-]', '', name).strip().replace(" ", "_") or "questions"
        await query.message.reply_document(
            document=pdf,
            filename=f"{safe_name}.pdf",
            caption=f"📄 {len(items)} سؤال — {name} ❤️",
        )
        PDF_BUFFER.pop(user_id, None)
        PDF_NAMES.pop(user_id, None)

    elif query.data == "gen_docx":
        if not items:
            await query.message.reply_text("❌ لا يوجد أسئلة محفوظة بعد")
            return
        await query.message.reply_text(f"⏳ جاري توليد DOCX لـ {len(items)} سؤال...")
        try:
            docx_buf = build_docx(items, name)
            safe_name = re.sub(r'[^\w\s\-]', '', name).strip().replace(" ", "_") or "questions"
            await query.message.reply_document(
                document=docx_buf,
                filename=f"{safe_name}.docx",
                caption=f"📝 {len(items)} سؤال — {name} ❤️",
            )
        except Exception as e:
            print("DOCX ERROR:", e)
            await query.message.reply_text(f"❌ خطأ في توليد الـ DOCX: {e}")
        PDF_BUFFER.pop(user_id, None)
        PDF_NAMES.pop(user_id, None)

    elif query.data == "clear_pdf":
        PDF_BUFFER.pop(user_id, None)
        PDF_NAMES.pop(user_id, None)
        AWAITING_NAME.pop(user_id, None)
        await query.message.reply_text("🗑 تم مسح كل الأسئلة المحفوظة")

# ═══════════════════════════════════════════════════════════════
# PDF COMMANDS
# ═══════════════════════════════════════════════════════════════
async def pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    AWAITING_NAME[user_id] = True
    # Clear any previous session
    PDF_BUFFER.pop(user_id, None)
    PDF_NAMES.pop(user_id, None)
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
    await update.message.reply_text(f"⏳ جاري توليد PDF لـ {len(items)} سؤال...")
    pdf = build_pdf(items, name)
    safe_name = re.sub(r'[^\w\s\-]', '', name).strip().replace(" ", "_") or "questions"
    await update.message.reply_document(
        document=pdf,
        filename=f"{safe_name}.pdf",
        caption=f"📄 {len(items)} سؤال — {name} ❤️",
    )
    PDF_BUFFER.pop(user_id, None)
    PDF_NAMES.pop(user_id, None)

async def pdf_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    PDF_BUFFER.pop(user_id, None)
    PDF_NAMES.pop(user_id, None)
    AWAITING_NAME.pop(user_id, None)
    await update.message.reply_text("🗑 تم مسح الأسئلة المحفوظة")

# ═══════════════════════════════════════════════════════════════
# START
# ═══════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in USERS:
        USERS.add(chat_id)
        save_users()

    await update.message.reply_text(
        "❤️ <b>بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</b> ❤️\n"
        "<b><i>منور يا كويزاوي🌹</i></b>\n",
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
        "• /pdf_start — اكتب اسم الملف، ثم ابعت الأسئلة أو فوروارد كويزات\n"
        "• اضغط <b>Export as PDF</b> أو <b>Export as DOCX</b>\n"
        "• /pdf_clear — إلغاء",
        parse_mode=ParseMode.HTML,
    )
    await update.message.reply_text(
        "🆕 <b>Latest Updates — V5.0</b>\n"
        "• Change PDF name\n"
        "• Export your file in PDF/DOCX\n"
        "• إصلاح تكرار A) B) C) \n"
        "• improved quiz file formating\n"
        "•زيادة الحد الأقصى للأسئلة في المرة الواحدة: 40\n"
        "• الأسئلة الطويلة تتقسم تلقائياً بين السؤال والـ Description\n\n"
        "❤ صلي على النبي ❤",
        parse_mode=ParseMode.HTML,
    )

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start",        start))
app.add_handler(CommandHandler("pdf_start",    pdf_start))
app.add_handler(CommandHandler("pdf_generate", pdf_generate))
app.add_handler(CommandHandler("pdf_clear",    pdf_clear))

app.add_handler(MessageHandler(filters.FORWARDED & filters.POLL, handle_poll))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running... V5.0")
app.run_polling()
