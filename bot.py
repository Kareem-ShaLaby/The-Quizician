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


# ---------- HELPERS ----------

def clean_option(line: str) -> str:
    line = line.strip()

    line = re.sub(r"^[A-Za-z0-9]+[\)\.\-]\s*", "", line)
    line = re.sub(r"^[-•]\s*", "", line)

    return line.strip()


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


# ---------- HANDLER ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    try:
        question_blocks = re.split(r"\n\s*\n(?=[^\n])", text)

        # ---------- max questions ----------
        if len(question_blocks) > 10:
            await update.message.reply_text(
                "🦦 بلاش طفس يسطا الحد الأقصى 10 أسئلة "
            )
            return

        for block in question_blocks:

            lines = [l.strip() for l in block.split("\n") if l.strip()]

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

                if "✅" in option_text or re.search(r"\b[zZ]\b$", option_text):
                    option_text = option_text.replace("✅", "").strip()
                    option_text = re.sub(r"\b[zZ]\b$", "", option_text).strip()

                    correct_index = len(options)

                if option_text:
                    options.append(option_text)

            # ---------- auto labels ----------
            has_labels = all(
                re.match(r"^[A-Za-z]\)", opt.strip())
                for opt in options
            )

            if not has_labels:
                labeled = []

                for i, opt in enumerate(options):
                    labeled.append(f"{string.ascii_uppercase[i]}) {opt}")

                options = labeled

            # ---------- validation ----------

            if len(options) < 2:
                await update.message.reply_text("❌ السؤال ناقص")
                continue

            if len(options) > 12:
                await update.message.reply_text(
                    "😭 أكتر من 12 اختيار حرام عليك"
                )
                continue

            if correct_index is None:
                await update.message.reply_text("❌ مفيش إجابة صح")
                continue

            if correct_index >= len(options):
                await update.message.reply_text("❌ مشكلة في الإجابة")
                continue

            # ---------- SEND POLL ----------
            await context.bot.send_poll(
                chat_id=update.effective_chat.id,
                question=question,
                options=options,
                type="quiz",
                correct_option_id=correct_index,
                explanation=explanation,
                is_anonymous=True,
            )

            # ---------- REACTION ----------
            await react_random(update, context)

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌🥸 في مشكلة في التنسيق")
# ---------- START COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "❤️ <b>بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</b> ❤️\n"
        "<b><i>Created by Kareem Shalaby</i></b>\n"
        "<b>منور يا كويزاوي🌹</b>\n\n"

        "Send a question like:\n"
        "Question?\n"
        "a) option 1\n"
        "b) option 2 ✅\n"
        "c) option 3\n"
        "ex: explanation (optional - لازم تحت السؤال علطول)\n\n"
        "or use Z instead of ✅",
        parse_mode=ParseMode.HTML
    )

    await update.message.reply_text(
        "🆕 <b>Latest Updates - V2.3</b>\n"
        "• increased maximum Multi-question support (up to 10!)\n"
        "• Bug fixes\n"
        "❤صلي على النبي❤\n",
        parse_mode=ParseMode.HTML
    )

# ---------- MAIN ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
