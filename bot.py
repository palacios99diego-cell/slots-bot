import json, os, re, threading, asyncio
from datetime import datetime
from collections import defaultdict
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVO = "apuestas.json"
app_web = Flask(__name__)

@app_web.route("/")
def home(): return "V19 FINAL OK"

def cargar():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO,"r") as f: return json.load(f)
        except: pass
    return []

def guardar(d):
    with open(ARCHIVO,"w") as f: json.dump(d,f,indent=2)

def racha_roja(lista_apuestas):
    racha=0
    for ap in reversed(lista_apuestas):
        if ap.get("resultado")=="ROJO": racha+=1
        elif ap.get("resultado") in ["VERDE","NULO"]: break
        else: continue
    return racha

def ultimos_7_emojis(lista):
    resueltas=[x for x in lista if x.get("resultado") in ["VERDE","ROJO","NULO"]]
    ult=resueltas[-7:]
    emojis=[]
    for ap in ult:
        if ap["resultado"]=="VERDE": emojis.append("🟢")
        elif ap["resultado"]=="ROJO": emojis.append("🔴")
        else: emojis.append("🟡")
    return " ".join(emojis) if emojis else "Sin resultados"

def teclado_resultado(idx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 VERDE", callback_data=f"win_{idx}"), InlineKeyboardButton("🔴 ROJO", callback_data=f"lose_{idx}")],
        [InlineKeyboardButton("🟡 NULO", callback_data=f"nulo_{idx}"), InlineKeyboardButton("⏳ PENDIENTE", callback_data=f"pend_{idx}")]
    ])

async def verificar_alertas(context: ContextTypes.DEFAULT_TYPE, tipster: str):
    datos=cargar()
    lista=[x for x in datos if x.get("tipster")==tipster]
    racha=racha_roja(lista)
    chat_id=context.user_data.get("chat_id")
    if not chat_id: return
    if racha>=5:
        await context.bot.send_message(chat_id=chat_id, text=f"🚨 ALERTA {racha} ROJ