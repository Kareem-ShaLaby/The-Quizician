import re
import string
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
        # split questions by double new line
        question_blocks = re.split(r"\n\s*\n(?=[^\n])", text)

        # max 5 questions
        if len(question_blocks) > 5:
            await update.message.reply_text("❌ الحد الأقصى 5 أسئلة مرة واحدة")
            return

        for block in question_blocks:

            lines = [l.strip() for l in block.split("\n") if l.strip()]

            if len(lines) < 3:
                continue

            question = lines[0]

            options = []
            correct_index = None
            explanation = None

            # ---------- detect explanation ----------
            for i, line in enumerate(lines):
                if line.lower().startswith("ex:"):
                    explanation = line[3:].strip()
                    lines = lines[:i]
                    break

            # ---------- parse options ----------
            for line in lines[1:]:
                option_text = clean_option(line)

                # detect correct answer using ✅ or Z/z
                if "✅" in option_text or re.search(r"\b[zZ]\b$", option_text):
                    option_text = option_text.replace("✅", "").strip()
                    option_text = re.sub(r"\b[zZ]\b$", "", option_text).strip()

                    correct_index = len(options)

                if option_text:
                    options.append(option_text)

            # ---------- auto add A) B) C)... ----------
            has_labels = all(
                re.match(r"^[A-Za-z]\)", opt.strip())
                for opt in options
            )

            if not has_labels:
                labeled_options = []

                for i, opt in enumerate(options):
                    label = f"{string.ascii_uppercase[i]}) "
                    labeled_options.append(label + opt)

                options = labeled_options

            # ---------- VALIDATION ----------

            if len(options) < 2:
                await update.message.reply_text(
                    f"❌ السؤال ده محتاج اختيارين على الأقل:\n{question}"
                )
                continue

            if len(options) > 12:
                await update.message.reply_text(
                    f"❌ السؤال ده فيه أكتر من 12 اختيار:\n{question}"
                )
                continue

            if correct_index is None:
                await update.message.reply_text(
                    f"❌ حدد الإجابة الصح في السؤال:\n{question}"
                )
                continue

            if correct_index >= len(options):
                await update.message.reply_text(
                    f"❌ في مشكلة في الإجابة الصح:\n{question}"
                )
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

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("❌🥸 في مشكلة في التنسيق")
# ---------- COMMANDS ----------

from telegram.constants import ParseMode

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # ---------- FIRST MESSAGE ----------
    await update.message.reply_text(
        "❤️ <b>بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</b> ❤️\n"
        "<b><i>Created by Kareem Shalaby</i></b>\n"
        "<b>منور يا كويزاوي🌹</b>"
        "Send a question like:\n\n"
        "Question?\n"
        "a) option 1\n"
        "b) option 2 ✅\n"
        "c) option 3\n"
        "ex: explanation (optional - لازم تحت السؤال علطول)\n\n"
        "or use Z instead of ✅"
        ,
        parse_mode=ParseMode.HTML
    )

    # ---------- SECOND MESSAGE ----------
    await update.message.reply_text(
        "🆕 <b>Latest Updates - V2.1 </b>\n"
        "• Multi-question support (up to 5) - تقدر تحط كذا سؤال مره واحده\n"
        "• Supports ✅ and Z\n"
        "• Automatic A) B) C) labels\n"
        "• Bug fixes\n",

        parse_mode=ParseMode.HTML
    )

# ---------- MAIN ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot running...")
app.run_polling()
