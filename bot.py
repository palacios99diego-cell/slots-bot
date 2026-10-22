import os
import sqlite3
import threading
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

TOKEN = os.environ.get("BOT_TOKEN")

flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "V18 LIVE"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def init_db():
    conn = sqlite3.connect("slots.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS picks (id INTEGER PRIMARY KEY, pick TEXT, monto REAL, tipster TEXT, estado TEXT DEFAULT 'pendiente', fecha TEXT)")
    conn.commit()
    conn.close()

PICK, MONTO, TIPSTER = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ V18 LISTO - Manda tu pick")
    return PICK

async def recibir_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pick'] = update.message.text
    await update.message.reply_text("💰 Monto?")
    return MONTO

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['monto'] = float(update.message.text.replace(',','.'))
        await update.message.reply_text("👤 Tipster?")
        return TIPSTER
    except:
        await update.message.reply_text("Manda solo número. Ej: 70")
        return MONTO

async def recibir_tipster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pick = context.user_data['pick']
    monto = context.user_data['monto']
    tipster = update.message.text
    conn = sqlite3.connect("slots.db")
    c = conn.cursor()
    c.execute("INSERT INTO picks (pick,monto,tipster,fecha) VALUES (?,?,?,?)", (pick,monto,tipster,datetime.now().strftime("%d/%m %H:%M")))
    pid = c.lastrowid
    conn.commit()
    conn.close()
    kb = [[InlineKeyboardButton("🟢 Ganada", callback_data=f"win_{pid}"), InlineKeyboardButton("🔴 Perdida", callback_data=f"loss_{pid}"), InlineKeyboardButton("🟡 Nula", callback_data=f"void_{pid}")]]
    await update.message.reply_text(f"✅ GUARDADA ID:{pid}\n{pick}\n{monto} - {tipster}", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    est, pid = q.data.split('_')
    mapa = {'win':'ganada','loss':'perdida','void':'nula'}
    conn = sqlite3.connect("slots.db")
    c = conn.cursor()
    c.execute("UPDATE picks SET estado=? WHERE id=?", (mapa[est], pid))
    conn.commit()
    conn.close()
    await q.edit_message_text(f"✅ {pid} -> {mapa[est].upper()}")

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado")
    return ConversationHandler.END

def main():
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    print("V18 INICIADO")
    app = ApplicationBuilder().token(TOKEN).build()
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
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
      