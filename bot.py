import json, os, re, threading, asyncio
from datetime import datetime
from collections import defaultdict
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN", "")
ARCHIVO = "apuestas.json"
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "V20 OK"

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
        r = ap.get("resultado")
        if r == "ROJO":
            racha += 1
        elif r == "VERDE" or r == "NULO":
            break
    return racha

def ultimos_7(lista):
    resueltas = [x for x in lista if x.get("resultado") in ["VERDE","ROJO","NULO"]]
    ult = resueltas[-7:]
    out = []
    for ap in ult:
        if ap.get("resultado") == "VERDE":
            out.append("G")
        elif ap.get("resultado") == "ROJO":
            out.append("R")
        else:
            out.append("N")
    return " ".join(out) if out else "Sin datos"

def teclado_resultado(idx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("VERDE", callback_data="win_%d" % idx), InlineKeyboardButton("ROJO", callback_data="lose_%d" % idx)],
        [InlineKeyboardButton("NULO", callback_data="nulo_%d" % idx), InlineKeyboardButton("PEND", callback_data="pend_%d" % idx)]
    ])

async def verificar_alertas(context, tipster):
    datos = cargar()
    lista = [x for x in datos if x.get("tipster") == tipster]
    racha = racha_roja(lista)
    chat_id = context.user_data.get("chat_id")
    if not chat_id:
        return
    if racha >= 5:
        texto = "ALERTA " + str(racha) + " ROJAS SEGUIDAS - " + tipster + " - Sigue perdiendo, no apostar hasta que gane"
        await context.bot.send_message(chat_id=chat_id, text=texto)
    elif racha == 3 or racha == 4:
        texto = tipster + " lleva " + str(racha) + " ROJAS"
        await context.bot.send_message(chat_id=chat_id, text=texto)

async def start(update, context):
    context.user_data.clear()
    context.user_data["chat_id"] = update.effective_chat.id
    teclado = [["BALANCE","PENDIENTES"],["TIPSTERS 7","LISTADO"]]
    await update.message.reply_text("V20 LISTO - Manda pick, monto, tipster", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def tipsters_cmd(update, context):
    datos = cargar()
    if not datos:
        await update.message.reply_text("Sin apuestas")
        return
    agrupado = defaultdict(list)
    for x in datos:
        agrupado[x.get("tipster","?")].append(x)
    txt = "TIPSTERS ULTIMAS 7\n\n"
    for tipster, lista in agrupado.items():
        racha = racha_roja(lista)
        emojis = ultimos_7(lista)
        if racha >= 5:
            txt += "ROJO " + tipster.upper() + " " + emojis + " -> " + str(racha) + " ROJAS\n\n"
        elif racha >= 3:
            txt += "ROJO " + tipster + " " + emojis + " -> " + str(racha) + "\n\n"
        else:
            txt += tipster + " " + emojis + " Racha:" + str(racha) + "\n\n"
    await update.message.reply_text(txt)

async def listado_cmd(update, context):
    datos = cargar()
    if not datos:
        await update.message.reply_text("Sin apuestas")
        return
    await update.message.reply_text("ULTIMAS 20:")
    for i in range(max(0,len(datos)-20), len(datos)):
        ap = datos[i]
        txt = "#" + str(i) + " " + ap.get("fecha","") + " " + ap.get("tipster","") + " $" + str(ap.get("monto","")) + " " + ap.get("pick","")[:80]
        await update.message.reply_text(txt, reply_markup=teclado_resultado(i))

async def pendientes_cmd(update, context):
    datos = cargar()
    pend = [(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
    if not pend:
        await update.message.reply_text("Sin pendientes")
        return
    for idx, ap in pend[-10:]:
        await update.message.reply_text("#" + str(idx) + " " + ap.get("tipster","") + " $" + str(ap.get("monto","")), reply_markup=teclado_resultado(idx))

async def mensaje(update, context):
    msg = update.message
    texto = (msg.text or msg.caption or "").strip()
    if not texto:
        return
    context.user_data["chat_id"] = update.effective_chat.id
    datos = cargar()

    if texto == "BALANCE":
        v = len([x for x in datos if x.get("resultado")=="VERDE"])
        r = len([x for x in datos if x.get("resultado")=="ROJO"])
        await update.message.reply_text("Total %d V:%d R:%d" % (len(datos), v, r))
        return
    if texto == "PENDIENTES":
        await pendientes_cmd(update, context)
        return
    if "TIPSTERS" in texto:
        await tipsters_cmd(update, context)
        return
    if "LISTADO" in texto:
        await listado_cmd(update, context)
        return

    m = re.search(r"\d+(\.\d+)?", texto)
    es_num = bool(re.fullmatch(r"\s*\$?\s*\d+(\.\d+)?\s*", texto))

    if context.user_data.get("esperando_tipster"):
        tipster = texto[:50]
        monto = context.user_data.get("monto")
        pick = context.user_data.get("pick")
        nuevo = {"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
        datos.append(nuevo)
        guardar(datos)
        idx = len(datos)-1
        context.user_data.pop("esperando_tipster", None)
        await update.message.reply_text("Guardada #" + str(idx), reply_markup=teclado_resultado(idx))
        await verificar_alertas(context, tipster)
        return

    if context.user_data.get("esperando_monto"):
        if m:
            monto = float(m.group(0))
            context.user_data["monto"] = monto
            context.user_data["esperando_monto"] = False
            context.user_data["esperando_tipster"] = True
            await update.message.reply_text("Monto $" + str(monto) + " OK, ahora TIPSTER:")
            return
        else:
            await update.message.reply_text("Manda monto ej 70")
            return

    if len(texto) > 3 and not es_num:
        if texto in ["BALANCE","PENDIENTES","TIPSTERS 7","LISTADO"]:
            return
        context.user_data["pick"] = texto[:500]
        context.user_data["esperando_monto"] = True
        await update.message.reply_text("Pick OK, manda MONTO:")
        return

async def callback(update, context):
    q = update.callback_query
    await q.answer()
    datos = cargar()
    try:
        acc, idx = q.data.split("_")
        idx = int(idx)
        if acc == "win":
            datos[idx]["resultado"] = "VERDE"
        elif acc == "lose":
            datos[idx]["resultado"] = "ROJO"
        elif acc == "nulo":
            datos[idx]["resultado"] = "NULO"
        else:
            datos[idx]["resultado"] = "PENDIENTE"
        guardar(datos)
        tipster = datos[idx].get("tipster","?")
        await q.edit_message_text("Resultado " + datos[idx]["resultado"] + " #" + str(idx) + " " + tipster, reply_markup=teclado_resultado(idx))
        if acc == "lose":
            await verificar_alertas(context, tipster)
    except Exception as e:
        print(e)

def build_app():
    if not TOKEN:
        print("BOT_TOKEN vacio!")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, mensaje))
    return app

def main():
    print("V20 INICIADO", flush=True)
    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()
    build_app().run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()