import os
import sqlite3
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN no esta en Environment", flush=True)

DB_PATH = "bot.db"
PICK, MONTO, TIPSTER = range(3)
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "BOT V18 OK - TOKEN: " + ("SI" if BOT_TOKEN else "NO")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS apuestas (id INTEGER PRIMARY KEY, pick TEXT, monto TEXT, tipster TEXT, fecha TEXT)")
    conn.commit()
    conn.close()

async def start(update: Update, context):
    await update.message.reply_text("Manda tu PICK:")
    return PICK

async def recibir_pick(update: Update, context):
    context.user_data['pick'] = update.message.text
    await update.message.reply_text("Manda el MONTO:")
    return MONTO

async def recibir_monto(update: Update, context):
    context.user_data['monto'] = update.message.text
    await update.message.reply_text("Manda el TIPSTER:")
    return TIPSTER

async def recibir_tipster(update: Update, context):
    pick = context.user_data['pick']
    monto = context.user_data['monto']
    tipster = update.message.text
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO apuestas VALUES (NULL,?,?,?,datetime('now'))", (pick, monto, tipster))
    conn.commit()
    conn.close()
    kb = [[InlineKeyboardButton("✅ Confirmar", callback_data="ok"), InlineKeyboardButton("❌ Cancelar", callback_data="no")]]
    await update.message.reply_text(f"PICK: {pick}\nMONTO: {monto}\nTIPSTER: {tipster}", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def cancelar(update: Update, context):
    await update.message.reply_text("Cancelado /start")
    return ConversationHandler.END

async def botones(update: Update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("✅ Guardado!" if q.data=="ok" else "❌ Cancelado")

def build_app():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_pick)],
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],
            TIPSTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_tipster)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(botones))
    return app

def main():
    print("V18 INICIADO", flush=True)
    print(f"TOKEN EXISTE: {bool(BOT_TOKEN)}", flush=True)
    if not BOT_TOKEN:
        print("NO HAY BOT_TOKEN - Ponlo en Render > Environment", flush=True)
        return
    init_db()
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    build_app().run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()