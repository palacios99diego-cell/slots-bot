import os
import sqlite3
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = "bot.db"

# Estados
PICK, MONTO, TIPSTER = range(3)

# Flask para Render
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "BOT V18 ACTIVO"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS apuestas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, pick TEXT, monto TEXT, tipster TEXT, fecha TEXT)""")
    conn.commit()
    conn.close()

# --- Handlers Telegram ---

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
    context.user_data['tipster'] = update.message.text
    
    pick = context.user_data['pick']
    monto = context.user_data['monto']
    tipster = context.user_data['tipster']
    
    # Guardar
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO apuestas (pick, monto, tipster, fecha) VALUES (?,?,?,datetime('now'))", 
              (pick, monto, tipster))
    conn.commit()
    conn.close()
    
    keyboard = [[InlineKeyboardButton("✅ Confirmar", callback_data="confirmar"),
                 InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
    
    await update.message.reply_text(
        f"Resumen:\nPICK: {pick}\nMONTO: {monto}\nTIPSTER: {tipster}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

async def cancelar(update: Update, context):
    await update.message.reply_text("Cancelado. Usa /start para empezar.")
    return ConversationHandler.END

async def botones(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "confirmar":
        await query.edit_message_text("✅ Apuesta guardada!")
    else:
        await query.edit_message_text("❌ Cancelado.")

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
    init_db()
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()
    app_telegram = build_app()
    app_telegram.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
      