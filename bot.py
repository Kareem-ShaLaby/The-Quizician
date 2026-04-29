import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = "@QuizicianChannel"  # replace this

async def handle_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if len(lines) < 2:
        await update.message.reply_text("❌ Invalid format: need question + options")
        return

    question = lines[0]
    options = []
    correct_index = None

    for i, line in enumerate(lines[1:]):
        is_correct = line.endswith(",")

        # remove comma if present
        if is_correct:
            line = line[:-1].strip()

        # remove A) B) C) if present OR not present
        if ")" in line:
            line = line.split(")", 1)[1].strip()

        options.append(line)

        if is_correct:
            correct_index = i

    if correct_index is None:
        await update.message.reply_text("❌ No correct answer marked with comma (,)")
        return

    if len(options) < 2:
        await update.message.reply_text("❌ Need at least 2 options")
        return

    await context.bot.send_poll(
        chat_id=CHANNEL_ID,
        question=question,
        options=options,
        type="quiz",
        correct_option_id=correct_index,
        is_anonymous=False
    )

    await update.message.reply_text("✅ Quiz posted")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz))

app.run_polling()
