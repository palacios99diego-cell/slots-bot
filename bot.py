import json, os, re, threading, asyncio
from datetime import datetime
from collections import defaultdict, Counter
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVO = "apuestas.json"
CHAT_FILE = "chat_id.txt"
app_web = Flask(__name__)
PEND_POR_PAGINA = 10

@app_web.route("/")
def home():
    return "V27 TIPSTER + TODAS PEND OK"

def cargar():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO, "r") as f:
                return json.load(f)
        except: pass
    return []

def guardar(d):
    with open(ARCHIVO, "w") as f:
        json.dump(d, f, indent=2)

def save_chat(cid):
    try:
        with open(CHAT_FILE, "w") as f: f.write(str(cid))
    except: pass

def get_chat(context):
    cid = context.user_data.get("chat_id") if context and context.user_data else None
    if cid: return cid
    if os.path.exists(CHAT_FILE):
        try:
            with open(CHAT_FILE, "r") as f: return int(f.read().strip())
        except: pass
    return None

def racha_roja(lista):
    racha = 0
    for ap in reversed(lista):
        r = ap.get("resultado")
        if r == "ROJO": racha += 1
        elif r == "VERDE" or r == "NULO": break
    return racha

def ultimos_7_emojis(lista):
    resueltas = [x for x in lista if x.get("resultado") in ["VERDE","ROJO","NULO"]]
    ult = resueltas[-7:]
    out = []
    for ap in ult:
        r = ap.get("resultado")
        if r == "VERDE": out.append("🟢")
        elif r == "ROJO": out.append("🔴")
        else: out.append("🟡")
    return " ".join(out) if out else "Sin datos"

def teclado_resultado(idx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 VERDE", callback_data="win_%d" % idx), InlineKeyboardButton("🔴 ROJO", callback_data="lose_%d" % idx)],
        [InlineKeyboardButton("🟡 NULO", callback_data="nulo_%d" % idx), InlineKeyboardButton("⏳ PEND", callback_data="pend_%d" % idx)]
    ])

async def verificar_alertas(context, tipster):
    datos = cargar()
    lista = [x for x in datos if x.get("tipster") == tipster]
    racha = racha_roja(lista)
    cid = get_chat(context)
    if not cid: return
    if racha >= 5:
        texto = "🚨 ALERTA %d ROJAS SEGUIDAS 🚨\n\n👤 %s\n🔴 Lleva %d perdidas" % (racha, tipster, racha)
        await context.bot.send_message(chat_id=cid, text=texto)

async def start(update, context):
    context.user_data.clear()
    context.user_data["chat_id"] = update.effective_chat.id
    save_chat(update.effective_chat.id)
    teclado = [["📊 BALANCE","⏳ PENDIENTES"],["👥 TIPSTERS 7","📋 LISTADO"]]
    await update.message.reply_text("✅ V27 ACTIVO - TIPSTER + PAGINACION", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def tipsters_cmd(update, context):
    context.user_data["chat_id"] = update.effective_chat.id
    save_chat(update.effective_chat.id)
    datos = cargar()
    if not datos:
        await update.message.reply_text("Sin apuestas")
        return
    agrupado = defaultdict(list)
    for x in datos: agrupado[x.get("tipster","?")].append(x)
    txt = "📋 Listado con últimos 7:\n\n"
    i = 1
    for tipster, lista in agrupado.items():
        racha = racha_roja(lista)
        emojis = ultimos_7_emojis(lista)
        pendientes = len([x for x in lista if x.get("resultado")=="PENDIENTE"])
        if racha >= 5:
            txt += "%d. 🔴🔴 %s 🔴🔴\n%s\n⏳ Pendientes: %d\n➡️ %d ROJAS SEGUIDAS 🚨\n\n" % (i, tipster.upper(), emojis, pendientes,