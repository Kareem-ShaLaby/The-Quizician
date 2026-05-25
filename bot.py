import re
import string
import random
import json
import os
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

# ═══════════════════════════════════════════════════════════════
# FONT SETUP
# Drop your Comic Sans file (named "comic.ttf") in the same
# folder as this script. If not found, falls back to Helvetica.
# ═══════════════════════════════════════════════════════════════
FONT_NAME      = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"

if os.path.exists("comic.ttf"):
    try:
        pdfmetrics.registerFont(TTFont("ComicSans", "comic.ttf"))
        FONT_NAME      = "ComicSans"
        FONT_NAME_BOLD = "ComicSans"   # use same file; bold handled via <b> tags
        print("✅ Comic Sans loaded")
    except Exception as e:
        print(f"⚠️  Could not load comic.ttf: {e} — using Helvetica")
else:
    print("ℹ️  comic.ttf not found — using Helvetica. "
          "Place comic.ttf next to the script to enable Comic Sans.")

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
# PDF MEMORY
# ═══════════════════════════════════════════════════════════════
PDF_BUFFER = {}   # user_id -> list of question dicts

# ═══════════════════════════════════════════════════════════════
# DHIKR
# ═══════════════════════════════════════════════════════════════
dhikr_list = [
    "صلي على النبي ﷺ",
    "سبحان الله وبحمده، سبحان الله العظيم",
    "لا حول ولا قوة إلا بالله",
    "الحمد لله",
]

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def clean_option(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[A-Ea-e1-5][).\-]\s*", "", line)
    line = re.sub(r"^[-•]\s*", "", line)
    return line.strip()

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

# ═══════════════════════════════════════════════════════════════
# GENERATE PDF BUTTON
# ═══════════════════════════════════════════════════════════════
def generate_pdf_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Generate PDF", callback_data="gen_pdf")],
        [InlineKeyboardButton("🗑 Clear & Cancel", callback_data="clear_pdf")],
    ])

# ═══════════════════════════════════════════════════════════════
# PDF BUILDER
# ═══════════════════════════════════════════════════════════════
def build_pdf(items: list) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
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
        textColor=colors.HexColor("#1B5E20"),   # dark green
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
        # Question number
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
            # Each content line as its own paragraph
            for line in item["content"].split("\n"):
                line = line.strip()
                if line:
                    story.append(Paragraph(f"• {line}", WRITTEN_BODY))

        # Separator line between questions (not after last)
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
# Catches forwarded Telegram quiz/poll messages and saves them
# to PDF_BUFFER when PDF mode is active.
# ═══════════════════════════════════════════════════════════════
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarded poll/quiz messages."""
    if not update.message or not update.message.poll:
        return

    user_id = update.effective_chat.id

    # Only capture polls when PDF mode is active
    if user_id not in PDF_BUFFER:
        await update.message.reply_text(
            "ℹ️  ابدأ وضع PDF أولاً بـ /pdf_start ثم ابعت الأسئلة."
        )
        return

    poll = update.message.poll
    question = poll.question
    options  = [opt.text for opt in poll.options]

    # Telegram quiz polls expose the correct option index
    correct_index = poll.correct_option_id  # None for regular polls

    if correct_index is None:
        # Regular poll (not quiz) — save without marking correct
        correct_index = 0   # default; user can't tell from a regular poll

    # Prefix options with letters: A) B) C) …
    labeled_options = [
        f"{string.ascii_uppercase[i]}) {opt}"
        for i, opt in enumerate(options)
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

    try:
        blocks = re.split(r"\n\s*\n", text)

        if len(blocks) > 20:
            await update.message.reply_text("❌ الحد الأقصى 20 سؤال في المرة الواحدة")
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
            poll_msg = await context.bot.send_poll(
                chat_id=user_id,
                question=question,
                options=options,
                type="quiz",
                correct_option_id=correct_index,
                is_anonymous=True,
            )

            await react_fire(context, poll_msg.chat.id, poll_msg.message_id)
            await react_random(update, context)

            # DHIKR 70%
            if random.randint(1, 10) <= 7:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=random.choice(dhikr_list),
                )

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌ خطأ في التنسيق")

# ═══════════════════════════════════════════════════════════════
# INLINE BUTTON HANDLER  (Generate PDF / Clear)
# ═══════════════════════════════════════════════════════════════
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "gen_pdf":
        items = PDF_BUFFER.get(user_id, [])
        if not items:
            await query.message.reply_text("❌ لا يوجد أسئلة محفوظة بعد")
            return

        await query.message.reply_text(
            f"⏳ جاري توليد PDF لـ {len(items)} سؤال..."
        )
        pdf = build_pdf(items)
        await query.message.reply_document(
            document=pdf,
            filename="questions.pdf",
            caption=f"📄 {len(items)} سؤال — Quizician Bot ❤️",
        )
        PDF_BUFFER.pop(user_id, None)   # reset after export

    elif query.data == "clear_pdf":
        PDF_BUFFER.pop(user_id, None)
        await query.message.reply_text("🗑 تم مسح كل الأسئلة المحفوظة")

# ═══════════════════════════════════════════════════════════════
# PDF COMMANDS  (keep old slash commands too)
# ═══════════════════════════════════════════════════════════════
async def pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    PDF_BUFFER[update.effective_chat.id] = []
    await update.message.reply_text(
        "📥 <b>وضع PDF نشط</b>\n\n"
        "• ابعت أسئلة نصية (MCQ أو مكتوبة)\n"
        "• أو <b>فوروارد</b> كويزات سبق ما الـ Bot بعتها\n\n"
        "اضغط <b>Generate PDF</b> لما تخلص 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=generate_pdf_keyboard(),
    )

async def pdf_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    items   = PDF_BUFFER.get(user_id, [])
    if not items:
        await update.message.reply_text("❌ لا يوجد أسئلة محفوظة")
        return
    await update.message.reply_text(f"⏳ جاري توليد PDF لـ {len(items)} سؤال...")
    pdf = build_pdf(items)
    await update.message.reply_document(
        document=pdf,
        filename="questions.pdf",
        caption=f"📄 {len(items)} سؤال — Quizician Bot ❤️",
    )
    PDF_BUFFER.pop(user_id, None)

async def pdf_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    PDF_BUFFER.pop(update.effective_chat.id, None)
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
        "<b><i>Created by Kareem Shalaby</i></b>\n"
        "منور يا كويزاوي 🌹",
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
        "Question? a) A b) Bz c) C\n\n"
        "3) Written Questions:\n"
        "Title\n"
        ".answer line 1\n"
        "answer line 2.\n\n"
        "4) PDF Mode:\n"
        "• /pdf_start — then send text questions OR forward old quizzes\n"
        "• Press <b>Generate PDF</b> button when done\n"
        "• /pdf_clear — cancel",
        parse_mode=ParseMode.HTML,
    )
    await update.message.reply_text(
        "🆕 <b>Latest Updates — V4.0</b>\n"
        "• Forward old quizzes directly into PDF\n"
        "• Generate PDF button (no need for /pdf_generate)\n"
        "• Questions flow continuously — no wasted pages\n"
        "• Comic Sans font support (drop comic.ttf next to script)\n"
        "• Correct answer highlighted in green ✓\n\n"
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

# Poll handler MUST come before the text handler
app.add_handler(MessageHandler(filters.FORWARDED & filters.POLL, handle_poll))

# Inline button handler
app.add_handler(CallbackQueryHandler(button_handler))

# Text handler (non-command)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running... V4.0")
app.run_polling()
