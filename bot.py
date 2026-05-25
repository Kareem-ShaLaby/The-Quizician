import re
import string
import random
import json
import os
from io import BytesIO

from telegram import Update, ReactionTypeEmoji
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


BOT_TOKEN = "PUT_YOUR_TOKEN_HERE"


# ---------- USERS STORAGE ----------
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


# ---------- PDF MEMORY ----------
PDF_BUFFER = {}  # user_id -> list


# ---------- DHIKR ----------
dhikr_list = [
    "صلي على النبي ﷺ",
    "سبحان الله وبحمده، سبحان الله العظيم",
    "لا حول ولا قوة إلا بالله",
    "الحمد لله"
]


# ---------- 🧠 AI AUTO-CLEANER ----------
def ai_clean_text(text: str) -> str:
    """
    Lightweight AI-like cleaner for messy quiz input.
    """

    text = text.replace("\u200f", "").replace("\u200e", "")  # RTL/LTR marks
    text = re.sub(r"[•●▪︎■▶►]", "", text)  # bullet noise
    text = re.sub(r"\s+", " ", text)  # collapse spaces

    # Fix spaced options like "A )" → "A)"
    text = re.sub(r"([A-Ea-e])\s+\)", r"\1)", text)
    text = re.sub(r"([A-Ea-e])\s+\.", r"\1.", text)

    # Normalize weird separators
    text = text.replace("–", "-").replace("—", "-")

    return text.strip()


# ---------- HELPERS ----------
def clean_option(line: str):
    line = line.strip()
    line = re.sub(r"^[A-Ea-e1-5][\)\.\-]\s*", "", line)
    line = re.sub(r"^[-•]\s*", "", line)
    return line.strip()


def normalize_mcq_block(block: str):
    block = ai_clean_text(block)

    if "\n" in block:
        return [l.strip() for l in block.split("\n") if l.strip()]

    match = re.search(r"\b([A-Ea-e1-5])[\)\.]", block)
    if not match:
        return [block]

    question = block[:match.start()].strip()
    options_part = block[match.start():]

    parts = re.split(r"(?=\b[A-Ea-e1-5][\)\.])", options_part)
    return [question] + [p.strip() for p in parts if p.strip()]


def parse_written_question(block: str):
    lines = [l.rstrip() for l in block.split("\n") if l.strip()]
    if len(lines) < 2:
        return None

    title = lines[0]
    content = "\n".join(lines[1:])

    if not (content.strip().startswith(".") and content.strip().endswith(".")):
        return None

    content = content.strip()[1:-1].strip()
    return title, content


# ---------- REACTIONS ----------
async def react_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        roll = random.randint(1, 20)
        emoji = "🫡" if roll <= 15 else "❤️" if roll <= 19 else "🏆"

        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reaction=[ReactionTypeEmoji(emoji)],
            is_big=False
        )
    except:
        pass


async def react_fire(context, chat_id, message_id):
    try:
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[ReactionTypeEmoji("🔥")]
        )
    except:
        pass


# ---------- PDF BUILDER ----------
def generate_pdf(items):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    content = []

    for i, item in enumerate(items, start=1):

        if item["type"] == "mcq":
            content.append(Paragraph(f"{i}. {item['q']}", styles["Normal"]))
            content.append(Spacer(1, 5))

            for idx, opt in enumerate(item["options"]):
                if idx == item["correct"]:
                    content.append(Paragraph(f"<b>{opt}</b>", styles["Normal"]))
                else:
                    content.append(Paragraph(opt, styles["Normal"]))

            content.append(Spacer(1, 10))


        elif item["type"] == "written":
            content.append(Paragraph(f"{i}. {item['title']}", styles["Normal"]))
            content.append(Spacer(1, 5))
            content.append(Paragraph(item["content"], styles["Normal"]))
            content.append(Spacer(1, 10))


        elif item["type"] == "poll":
            content.append(Paragraph(f"{i}. {item['question']}", styles["Normal"]))
            content.append(Spacer(1, 5))

            for idx, opt in enumerate(item["options"]):
                if item.get("correct") is not None and idx == item["correct"]:
                    content.append(Paragraph(f"<b>{opt}</b>", styles["Normal"]))
                else:
                    content.append(Paragraph(opt, styles["Normal"]))

            content.append(Spacer(1, 10))

    doc.build(content)
    buffer.seek(0)
    return buffer


# ---------- HANDLER ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_chat.id

    # ---------- POLL SUPPORT ----------
    if update.message.poll:

        poll = update.message.poll
        options = [o.text for o in poll.options]

        correct = poll.correct_option_id if poll.type == "quiz" else None

        if user_id in PDF_BUFFER:
            PDF_BUFFER[user_id].append({
                "type": "poll",
                "question": poll.question,
                "options": options,
                "correct": correct
            })

        await update.message.reply_text("📊 تم حفظ Poll في PDF")
        return


    if not update.message.text:
        return

    text = ai_clean_text(update.message.text)

    try:
        blocks = re.split(r"\n\s*\n", text)

        for block in blocks:

            # ---------- WRITTEN ----------
            written = parse_written_question(block)
            if written:
                title, content = written

                if user_id in PDF_BUFFER:
                    PDF_BUFFER[user_id].append({
                        "type": "written",
                        "title": title,
                        "content": content
                    })
                    await update.message.reply_text("📝 تم حفظ سؤال PDF")
                continue


            # ---------- MCQ ----------
            lines = normalize_mcq_block(block)
            if len(lines) < 3:
                continue

            question = lines[0]
            options = []
            correct_index = None

            for line in lines[1:]:
                opt = clean_option(line)

                has_z = re.search(r"\s+[zZ]\s*$", opt)
                has_check = "✅" in opt or "✔" in opt

                if has_z or has_check:
                    opt = re.sub(r"\s+[zZ]\s*$", "", opt)
                    opt = opt.replace("✅", "").replace("✔", "")
                    correct_index = len(options)

                if opt:
                    options.append(opt)

            options = [
                f"{string.ascii_uppercase[i]}) {opt}"
                for i, opt in enumerate(options)
            ]

            if user_id in PDF_BUFFER:
                PDF_BUFFER[user_id].append({
                    "type": "mcq",
                    "q": question,
                    "options": options,
                    "correct": correct_index if correct_index is not None else 0
                })
                await update.message.reply_text("🧠 تم حفظ السؤال للـ PDF")
                continue

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌ خطأ في التنسيق")


# ---------- PDF COMMANDS ----------
async def pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    PDF_BUFFER[update.effective_chat.id] = []
    await update.message.reply_text("📥 بدأ وضع PDF — ابعت الأسئلة")


async def pdf_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id

    items = PDF_BUFFER.get(user_id, [])
    if not items:
        await update.message.reply_text("❌ لا يوجد بيانات")
        return

    pdf = generate_pdf(items)

    await update.message.reply_document(
        document=pdf,
        filename="questions.pdf"
    )

    PDF_BUFFER.pop(user_id, None)


async def pdf_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    PDF_BUFFER.pop(update.effective_chat.id, None)
    await update.message.reply_text("🗑 تم مسح PDF")


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in USERS:
        USERS.add(chat_id)
        save_users()

    await update.message.reply_text("Bot ready ✅")


# ---------- MAIN ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("pdf_start", pdf_start))
app.add_handler(CommandHandler("pdf_generate", pdf_generate))
app.add_handler(CommandHandler("pdf_clear", pdf_clear))
app.add_handler(MessageHandler(filters.ALL, handle))

print("Bot running...")
app.run_polling()
