import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = "8661732123:AAFkN5Z8OqWGhGMqcMOzMQkxYrxwv4fUVEE"

# ---------- HELPERS ----------

def clean_option(line: str) -> str:
    """
    Removes prefixes like:
    a) A) 1) - • etc.
    """
    line = line.strip()

    # remove prefixes like a), A), 1)
    line = re.sub(r"^[A-Za-z0-9]+[\)\.\-]\s*", "", line)

    # remove bullets like - or •
    line = re.sub(r"^[-•]\s*", "", line)

    return line.strip()


# ---------- HANDLER ----------

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    try:
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        if len(lines) < 3:
            await update.message.reply_text("❌ سؤال + اختيارين على الأقل")
            return

        question = lines[0]

        options = []
        correct_index = None
        explanation = None

        # detect explanation line
        for i, line in enumerate(lines):
            if line.lower().startswith("ex:"):
                explanation = line[3:].strip()
                lines = lines[:i]  # cut everything after explanation
                break

        # parse options
        for i, line in enumerate(lines[1:]):
            option_text = clean_option(line)

            if "✅" in option_text:
                option_text = option_text.replace("✅", "").strip()
                correct_index = len(options)

            if option_text:
                options.append(option_text)

        # ---------- VALIDATION ----------

        if len(options) < 2:
            await update.message.reply_text("❌ لازم اختيارين على الأقل")
            return

        if len(options) > 10:
            await update.message.reply_text("❌ الحد الأقصى 10 اختيارات")
            return

        if correct_index is None:
            await update.message.reply_text("❌ حط ✅ جنب الإجابة الصح")
            return

        # ---------- SEND POLL ----------

        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=question,
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            explanation=explanation,
            is_anonymous=False,
        )

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌ في مشكلة في التنسيق")


# ---------- COMMANDS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send a question like:\n\n"
        "Question?\n"
        "a) option 1\n"
        "b) option 2 ✅\n"
        "c) option 3\n\n"
        "ex: explanation (optional)"
    )


# ---------- MAIN ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
