import json, os, re, threading
from datetime import datetime
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVO = "apuestas.json"

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Bot slots-bot funcionando! V18 Activo"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

def cargar():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO, "r") as f: return json.load(f)
        except: pass
    return []

def guardar(datos):
    with open(ARCHIVO, "w") as f: json.dump(datos, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    teclado = [["📊 BALANCE","🔴 LISTADO ROJOS"]]
    await update.message.reply_text("✅ V18 VIVO - Manda el partido y te respondo al tiro", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (update.message.text or "").strip()
    datos = cargar()
    if "BALANCE" in texto:
        await update.message.reply_text(f"💰 Balance: {len(datos)} apuestas"); return
    if "LISTADO ROJOS" in texto:
        await update.message.reply_text("🔴 Listado: revisando..."); return
    es_numero = bool(re.match(r"^\d+(\.\d+)?$", texto))
    if context.user_data.get("esperando_tipster"):
        tipster = texto
        monto = context.user_data.get("monto")
        pick = context.user_data.get("pick")
        nuevo = {"fecha": datetime.now().strftime("%d/%m %H:%M"), "tipster": tipster, "m