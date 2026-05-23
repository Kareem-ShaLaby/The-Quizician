import re
import string
import random

from telegram import Update, ReactionTypeEmoji
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode


BOT_TOKEN = "8661732123:AAEkdln3xbp0EJiNBCKYChH0A8ioCYkSNic"


# ---------- DHIKR ----------
dhikr_list = [
    "صلي على النبي ﷺ",
    "سبحان الله وبحمده، سبحان الله العظيم",
    "لا حول ولا قوة إلا بالله",
    "الحمد لله"
]


# ---------- HELPERS ----------

def clean_option(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[A-Za-z0-9]+[\)\.\-]\s*", "", line)
    line = re.sub(r"^[-•]\s*", "", line)
    return line.strip()


def normalize_mcq_block(block: str):
    block = block.strip()

    if "\n" in block:
        return [l.strip() for l in block.split("\n") if l.strip()]

    match = re.search(r"\b[aA][\)\.]", block)
    if not match:
        return [block]

    question = block[:match.start()].strip()
    options_part = block[match.start():]

    parts = re.split(r"(?=\b[A-Za-z][\)\.])", options_part)

    return [question] + [p.strip() for p in parts if p.strip()]


# ---------- REACTIONS ----------

async def react_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        roll = random.randint(1, 20)

        if roll <= 15:
            emoji = "🫡"
        elif roll <= 19:
            emoji = "❤️"
        else:
            emoji = "🏆"

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


async def send_dhikr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = random.choice(dhikr_list)
        await update.message.reply_text(msg)
    except:
        pass


# ---------- HANDLER ----------

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    try:
        blocks = re.split(r"\n\s*\n", text)

        if len(blocks) > 20:
            await update.message.reply_text("❌ الحد الأقصى 20 سؤال/كتلة")
            return

        for block in blocks:

            lines = normalize_mcq_block(block)

            if len(lines) < 3:
                continue

            question = lines[0]

            options = []
            correct_index = None
            explanation = None

            # ---------- explanation ----------
            for i, line in enumerate(lines):
                if line.lower().startswith("ex:"):
                    explanation = line[3:].strip()
                    lines = lines[:i]
                    break

            # ---------- options ----------
            for line in lines[1:]:
                option_text = clean_option(line)

                if "✅" in option_text or re.search(r"[zZ]\s*$", option_text):
                    option_text = option_text.replace("✅", "")
                    option_text = re.sub(r"[zZ]\s*$", "", option_text).strip()
                    correct_index = len(options)

                if option_text:
                    options.append(option_text)

            # ---------- auto labels ----------
            if options and not all(re.match(r"^[A-Za-z]\)", o) for o in options):
                options = [
                    f"{string.ascii_uppercase[i]}) {opt}"
                    for i, opt in enumerate(options)
                ]

            # ---------- validation ----------
            if len(options) < 2:
                await update.message.reply_text("❌ السؤال ناقص")
                continue

            if len(options) > 12:
                await update.message.reply_text("❌ أكثر من 12 اختيار")
                continue

            if correct_index is None:
                await update.message.reply_text("❌ لا يوجد إجابة صحيحة")
                continue

            if correct_index >= len(options):
                await update.message.reply_text("❌ خطأ في الإجابة")
                continue

            # ---------- SEND POLL ----------
            poll_msg = await context.bot.send_poll(
                chat_id=update.effective_chat.id,
                question=question,
                options=options,
                type="quiz",
                correct_option_id=correct_index,
                explanation=explanation,
                is_anonymous=True,
            )

            # ---------- REACTIONS ----------
            await react_fire(context, poll_msg.chat.id, poll_msg.message_id)
            await react_random(update, context)

            # ---------- DHIKR ----------
            await send_dhikr(update, context)

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌ خطأ في التنسيق")


# ---------- START ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # save user for broadcasts
    if chat_id not in USERS:
        USERS.add(chat_id)
        save_users()

    # message 1
    await update.message.reply_text(
        "❤️ <b>بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</b> ❤️\n"
        "<b><i>Kareem Shalaby</i></b>\n"
        "منور يا كويزاوي🌹",
        parse_mode=ParseMode.HTML
    )

    # message 2
    await update.message.reply_text(
        "📚 <b>Ways to use the bot:</b>\n\n"
        "1) Multi-line MCQ:\n"
        "Question?\n"
        "a) A\n"
        "b) B z\n"
        "c) C\n\n"
        "2) Single-line MCQ:\n"
        "Question? a) A b) B.z c) C\n\n"
        "3) Written Questions:\n"
        "Title\n"
        ".answer1\n"
        "answer2\n"
        "answer3.",
        parse_mode=ParseMode.HTML
    )

    # message 3
    await update.message.reply_text(
        "🆕 <b>Latest Updates - V2.4</b>\n"
        "• 20-question support\n"
        "• Single-line MCQ parsing\n"
        "• Written spoiler mode\n"
        "• Reactions\n"
        "• Bug fixes\n\n"
        "❤ صلي على النبي ❤",
        parse_mode=ParseMode.HTML
    )


# ---------- MAIN ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
