from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = "8661732123:AAFZ-NZjhNyZQz75j0u4Rv9syFEo9twmisY"
MY_CHAT_ID = 940770584  # your Telegram user ID

async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ignore messages without text/media safety check
    if update.effective_message:
        await context.bot.forward_message(
            chat_id=MY_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id
        )

app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, forward))

app.run_polling()
