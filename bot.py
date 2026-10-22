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
def home():
    return "V19.2 OK"

def cargar():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def guardar(d):
    with open(ARCHIVO, "w") as f:
        json.dump(d, f, indent=2)

def racha_roja(lista):
    racha = 0
    for ap in reversed(lista):
        res = ap.get("resultado")
        if res == "ROJO":
            racha += 1
        elif res == "VERDE" or res == "NULO":
            break
    return racha

def ultimos_7(lista):
    resueltas = [x for x in lista if x.get("resultado") in ["VERDE", "ROJO", "NULO"]]
    ult = resueltas[-7:]
    out = []
    for ap in ult:
        r = ap.get("resultado")
        if r == "VERDE":
            out.append("G")
        elif r == "ROJO":
            out.append("R")
        else:
            out.append("N")
    if not out:
        return "Sin resultados"
    return " ".join(out)

def teclado_resultado(idx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("VERDE", callback_data=f"win_{idx}"), InlineKeyboardButton("ROJO", callback_data=f"lose_{idx}")],
        [InlineKeyboardButton("NULO", callback_data=f"nulo_{idx}"), InlineKeyboardButton("PENDIENTE", callback_data=f"pend_{idx}")]
    ])

async def verificar_alertas(context, tipster):
    datos = cargar()
    lista = [x for x in datos if x.get("tipster") == tipster]
    racha = racha_roja(lista)
    chat_id = context.user_data.get("chat_id")
    if not chat_id:
        return
    if racha >= 5:
        msg = "ALERTA " + str(racha) + " ROJAS SEGUIDAS\n\nTIPSTER: " + tipster + "\nLleva " + str(racha) + " perdidas\nSigue en racha negativa - NO APOSTAR"
        await context.bot.send_message(chat_id=chat_id, text=msg)
    elif racha == 3 or racha == 4:
        msg = tipster + " lleva " + str(racha) + " ROJAS seguidas"
        await context.bot.send_message(chat_id=chat_id, text=msg)

async def start(update, context):
    context.user_data.clear()
    context.user_data["chat_id"] = update.effective_chat.id
    teclado = [["BALANCE", "PENDIENTES"], ["TIPSTERS 7", "LISTADO"]]
    await update.message.reply_text("V19.2 ACTIVO\nManda pick, monto, tipster", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def tipsters_7_cmd(update, context):
    datos = cargar()
    if not datos:
        await update.message.reply_text("Sin apuestas")
        return
    agrupado = defaultdict(list)
    for x in datos:
        agrupado[x.get("tipster", "Sin tipster")].append(x)
    txt = "TIPSTERS - ULTIMAS 7\n\n"
    for tipster, lista in agrupado.items():
        racha = racha_roja(lista)
        emojis = ultimos_7(lista)
        if racha >= 5:
            txt += "ROJO ROJO " + tipster.upper() + " - " + emojis + " -> " + str(racha) + " ROJAS\n\n"
        elif racha >= 3:
            txt += "ROJO " + tipster + " - " + emojis + " -> " + str(racha) + " rojas\n\n"
        else:
            txt += tipster + " - " + emojis + " -> Racha:" + str(racha) + "\n\n"
    await update.message.reply_text(txt)

async def listado_cmd(update, context):
    datos = cargar()
    if not datos:
        await update.message.reply_text("Sin apuestas")
        return
    await update.message.reply_text("ULTIMAS 20:")
    for i in range(max(0, len(datos)-20), len(datos)):
        ap = datos[i]
        e = ap.get("resultado", "?")
        txt = "#" + str(i) + " " + ap.get("fecha", "") + "\n" + ap.get("tipster", "") + " $" + str(ap.get("monto", "")) + "\n" + ap.get("pick", "")[:100] + "\nRes: " + e
        await update.message.reply_text(txt, reply_markup=teclado_resultado(i))

async def pendientes_cmd(update, context):
    datos = cargar()
    pendientes = [(i, x) for i, x in enumerate(datos) if x.get("resultado") == "PENDIENTE"]
    if not pendientes:
        await update.message.reply_text("Sin pendientes")
        return
    for idx, ap in pendientes[-10:]:
        txt = "#" + str(idx) + " " + ap.get("fecha", "") + " " + ap.get("tipster", "") + " $" + str(ap.get("monto", ""))
        await update.message.reply_text(txt, reply_markup=teclado_resultado(idx))

async def mensaje(update, context):
    msg = update.message
    texto = (msg.text or msg.caption or "").strip()
    if not texto:
        return
    context.user_data["chat_id"] = update.effective_chat.id
    datos = cargar()

    if texto == "BALANCE":
        v = len([x for x in datos if x.get("resultado") == "VERDE"])
        r = len([x for x in datos if x.get("resultado") == "ROJO"])
        p = len([x for x in datos if x.get("resultado") == "PENDIENTE"])
        await update.message.reply_text("Total:" + str(len(datos)) + " V:" + str(v) + " R:" + str(r) + " P:" + str(p))
        return
    if texto == "PENDIENTES":
        await pendientes_cmd(update, context)
        return
    if "TIPSTERS" in texto:
        await tipsters_7_cmd(update, context)
        return
    if "LISTADO" in texto:
        await listado_cmd(update, context)
        return

    match_num = re.search(r"\d+(\.\d+)?", texto)
    es_numero = bool(re.fullmatch(r"\s*\$?\s*\d+(\.\d+)?\s*", texto))

    if context.user_data.get("esperando_tipster"):
        tipster = texto[:50]
        monto = context.user_data.get("monto")
        pick = context.user_data.get("pick")
        nuevo = {"fecha": datetime.now().strftime("%d/%m %H:%M"), "tipster": tipster, "monto": monto, "pick": pick, "resultado": "PENDIENTE"}
        datos.append(nuevo)
        guardar(datos)
        idx = len(datos)-1
        context.user_data.pop("esperando_tipster", None)
        await update.message.reply_text("GUARDADA #" + str(idx) + " " + tipster + " $" + str(monto), reply_markup=teclado_resultado(idx))
        await verificar_alertas(context, tipster)
        return

    if context.user_data.get("esperando_monto"):
        if match_num:
            monto = float(match_num.group(0))
            context.user_data["monto"] = monto
            context.user_data["esperando_monto"] = False
            context.user_data["esperando_tipster"] = True
            await update.message.reply_text("$" + str(monto) + " OK - Ahora TIPSTER:")
            return