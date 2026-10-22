import os
import sqlite3
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = "bot.db"

PICK, MONTO, TIPSTER = range(3)

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
    c.execute("INSERT INTO apuestas (pick, monto, tipster, fecha) VALUES (?,?,?,datetime('now'))", (pick, monto, tipster))
    conn.commit()
    conn.close()
    
    keyboard = [[InlineKeyboardButton("✅ Confirmar", callback_data="confirmar"),
                 InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
    
    await update.message.reply_text(
        f"Resumen:\nPICK: {pick}\nMONTO: {monto}\nTIPSTER: {tipster}",
        reply_markup=InlineKeyboardMarkup(keyboard