import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = "@your_channel_username"  # replace this

async def handle_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = text.split("\n")

    if len(lines) < 2:
        await update.message.reply_text("Invalid format.")
        return

    question = lines[0]
    options = []
    correct_index = None

    for i, line in enumerate(lines[1:]):
        line = line.strip()

        if line.endswith(","):
            correct_index = i
            line = line[:-1].strip()  # remove comma

        # remove A) / B) etc
        if ")" in line:
            line = line.split(")", 1)[1].strip()

        options.append(line)

    if correct_index is None:
        await update.message.reply_text("No correct answer marked with a comma.")
        return

    await context.bot.send_poll(
        chat_id=CHANNEL_ID,
        question=question,
        options=options,
        type="quiz",
        correct_option_id=correct_index,
        is_anonymous=False
    )

    await update.message.reply_text("Quiz posted ✅")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz))

app.run_polling()