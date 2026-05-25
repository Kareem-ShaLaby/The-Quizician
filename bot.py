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

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet


BOT_TOKEN = "8661732123:AAEkdln3xbp0EJiNBCKYChH0A8ioCYkSNic"


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


# ---------- HELPERS ----------
def clean_option(line: str):
    line = line.strip()
    line = re.sub(r"^[A-Ea-e1-5][\)\.\-]\s*", "", line)
    line = re.sub(r"^[-•]\s*", "", line)
    return line.strip()


def normalize_mcq_block(block: str):
    block = block.strip()

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

    for item in items:
        if item["type"] == "mcq":
            content.append(Paragraph(f"<b>{item['q']}</b>", styles["Normal"]))
            content.append(Spacer(1, 6))

            for i, opt in enumerate(item["options"]):
                if i == item["correct"]:
                    content.append(Paragraph(f"<b>{opt}</b>", styles["Normal"]))
                else:
                    content.append(Paragraph(opt, styles["Normal"]))

            content.append(PageBreak())

        else:
            content.append(Paragraph(f"<b>{item['title']}</b>", styles["Normal"]))
            content.append(Spacer(1, 6))
            content.append(Paragraph(item["content"], styles["Normal"]))
            content.append(PageBreak())

    doc.build(content)
    buffer.seek(0)
    return buffer


# ---------- HANDLER ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_chat.id
    text = update.message.text.strip()

    try:
        blocks = re.split(r"\n\s*\n", text)

        if len(blocks) > 20:
            await update.message.reply_text("❌ الحد الأقصى 20")
            return

        for block in blocks:

            # ---------- WRITTEN ----------
            written = parse_written_question(block)
            if written:
                title, content = written

                # ONLY save if PDF mode is active
                if user_id in PDF_BUFFER:
                    PDF_BUFFER[user_id].append({
                        "type": "written",
                        "title": title,
                        "content": content
                    })
                    await update.message.reply_text("📝 تم حفظ سؤال PDF")
                else:
                    await update.message.reply_text(
                        f"*{title}*\n||{content}||",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
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

    # detect ONLY z/Z at END of line OR checkmark
    has_z_end = re.search(r"\s+[zZ]\s*$", opt)
    has_check = "✅" in opt

    if has_z_end or has_check:
        opt = opt.replace("✅", "")
        opt = re.sub(r"\s+[zZ]\s*$", "", opt).strip()
        correct_index = len(options)

    if opt:
        options.append(opt)

            options = [
                f"{string.ascii_uppercase[i]}) {opt}"
                for i, opt in enumerate(options)
            ]

            if correct_index is None or correct_index >= len(options):
                await update.message.reply_text("❌ خطأ في السؤال")
                continue

            # ---------- PDF MODE ----------
            if user_id in PDF_BUFFER:
                PDF_BUFFER[user_id].append({
                    "type": "mcq",
                    "q": question,
                    "options": options,
                    "correct": correct_index
                })
                await update.message.reply_text("🧠 تم حفظ السؤال للـ PDF")
                continue

            # ---------- NORMAL QUIZ ----------
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
                    text=random.choice(dhikr_list)
                )

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

    # RESET AFTER EXPORT (IMPORTANT FIX)
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

    await update.message.reply_text(
        "❤️ <b>بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</b> ❤️\n"
        "<b><i>Created by Kareem Shalaby</i></b>\n"
        "منور يا كويزاوي🌹",
        parse_mode=ParseMode.HTML
    )

    await update.message.reply_text(
        "📚 <b>Ways to use the bot:</b>\n\n"
        "1) normal MCQ:\n"
        "Question?\n"
        "a) A\n"
        "b) B z\n"
        "c) C\n\n"
        "2) Single-line MCQ: كله فنفس السطر\n"
        "Question? a) A b) Bz c) C\n\n"
        "3) Written Questions: متنساش النقطتين\n"
        "Title\n"
        ".answer1\n"
        "answer2\n"
        "answer3.",
        parse_mode=ParseMode.HTML
    )

    await update.message.reply_text(
        "🆕 <b>Latest Updates - V3.2</b>\n"
        "• 20-question support\n"
        "• Single-line MCQ parsing\n"
        "• Written spoiler mode\n"
        "• PDF Generator\n"
        "• أذكار\n\n"
        "❤ صلي على النبي ❤",
        parse_mode=ParseMode.HTML
    )


# ---------- MAIN ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("pdf_start", pdf_start))
app.add_handler(CommandHandler("pdf_generate", pdf_generate))
app.add_handler(CommandHandler("pdf_clear", pdf_clear))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling() 
