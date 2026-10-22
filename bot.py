import json, os, re, threading, asyncio
from datetime import datetime
from collections import defaultdict
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVO = "apuestas.json"
CHAT_FILE = "chat_id.txt"
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "V24 LISTADO CON PEND OK"

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

def save_chat(cid):
    try:
        with open(CHAT_FILE, "w") as f:
            f.write(str(cid))
    except:
        pass

def get_chat(context):
    cid = context.user_data.get("chat_id") if context and context.user_data else None
    if cid:
        return cid
    if os.path.exists(CHAT_FILE):
        try:
            with open(CHAT_FILE, "r") as f:
                return int(f.read().strip())
        except:
            pass
    return None

def racha_roja(lista):
    racha = 0
    for ap in reversed(lista):
        r = ap.get("resultado")
        if r == "ROJO":
            racha += 1
        elif r == "VERDE" or r == "NULO":
            break
    return racha

def ultimos_7_emojis(lista):
    resueltas = [x for x in lista if x.get("resultado") in ["VERDE","ROJO","NULO"]]
    ult = resueltas[-7:]
    out = []
    for ap in ult:
        r = ap.get("resultado")
        if r == "VERDE":
            out.append("🟢")
        elif r == "ROJO":
            out.append("🔴")
        else:
            out.append("🟡")
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
    if not cid:
        return
    if racha >= 5:
        texto = "🚨 ALERTA %d ROJAS SEGUIDAS 🚨\n\n👤 %s\n🔴 Lleva %d perdidas" % (racha, tipster, racha)
        await context.bot.send_message(chat_id=cid, text=texto)

async def start(update, context):
    context.user_data.clear()
    context.user_data["chat_id"] = update.effective_chat.id
    save_chat(update.effective_chat.id)
    teclado = [["📊 BALANCE","⏳ PENDIENTES"],["👥 TIPSTERS 7","📋 LISTADO"]]
    await update.message.reply_text("✅ V24 ACTIVO", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def tipsters_cmd(update, context):
    context.user_data["chat_id"] = update.effective_chat.id
    save_chat(update.effective_chat.id)
    datos = cargar()
    if not datos:
        await update.message.reply_text("Sin apuestas")
        return
    agrupado = defaultdict(list)
    for x in datos:
        agrupado[x.get("tipster","?")].append(x)

    txt = "📋 Listado con últimos 7:\n\n"
    i = 1
    for tipster, lista in agrupado.items():
        racha = racha_roja(lista)
        emojis = ultimos_7_emojis(lista)
        pendientes = len([x for x in lista if x.get("resultado")=="PENDIENTE"])
        
        if racha >= 5:
            txt += "%d. 🔴🔴 %s 🔴🔴\n%s\n⏳ Pendientes: %d\n➡️ %d ROJAS SEGUIDAS 🚨\n\n" % (i, tipster.upper(), emojis, pendientes, racha)
        else:
            txt += "%d. 👤 %s\n%s\n⏳ Pendientes: %d\n➡️ Racha roja: %d\n\n" % (i, tipster, emojis, pendientes, racha)
        i += 1
    
    await update.message.reply_text(txt)

async def balance_cmd(update, context):
    datos = cargar()
    total = len(datos)
    v = len([x for x in datos if x.get("resultado")=="VERDE"])
    r = len([x for x in datos if x.get("resultado")=="ROJO"])
    p = len([x for x in datos if x.get("resultado")=="PENDIENTE"])
    n = len([x for x in datos if x.get("resultado")=="NULO"])
    txt = "📊 BALANCE\nTotal: %d\n🟢 %d Verdes\n🔴 %d Rojos\n⏳ %d Pendientes\n🟡 %d Nulos\n\nUsa ⏳ PENDIENTES para editar" % (total, v, r, p, n)
    await update.message.reply_text(txt)

async def pendientes_cmd(update, context):
    datos = cargar()
    pend = [(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
    if not pend:
        await update.message.reply_text("✅ Sin pendientes")
        return
    for idx, ap in pend[-10:]:
        txt = "⏳ #%d %s $%s\n%s" % (idx, ap.get("tipster",""), str(ap.get("monto","")), ap.get("pick","")[:100])
        await update.message.reply_text(txt, reply_markup=teclado_resultado(idx))

async def mensaje(update, context):
    msg = update.message
    texto = (msg.text or msg.caption or "").strip()
    if not texto:
        return
    context.user_data["chat_id"] = update.effective_chat.id
    save_chat(update.effective_chat.id)
    datos = cargar()

    if texto in ["📊 BALANCE","BALANCE"]:
        await balance_cmd(update, context)
        return
    if "PENDIENTES" in texto:
        await pendientes_cmd(update, context)
        return
    if "TIPSTERS" in texto or "LISTADO" in texto:
        await tipsters_cmd(update, context)
        return

    m = re.search(r"\d+(\.\d+)?", texto)
    es_num = bool(re.fullmatch(r"\s*\$?\s*\d+(\.\d+)?\s*", texto))

    if context.user_data.get("esperando_tipster"):
        tipster = texto[:50]
        monto = context.user_data.get("monto")
        pick = context.user_data.get("pick")
        pendientes_mismo = [x for x in datos if x.get("tipster","").lower() == tipster.lower() and x.get("resultado") == "PENDIENTE"]
        if pendientes_mismo:
            await update.message.reply_text("⚠️ YA TIENES %d PENDIENTE(S) DE 👤 %s" % (len(pendientes_mismo), tipster))
        nuevo = {"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
        datos.append(nuevo)
        guardar(datos)
        idx = len(datos)-1
        context.user_data.pop("esperando_tipster", None)
        await update.message.reply_text("✅ Guardada #%d 👤 %s" % (idx, tipster), reply_markup=teclado_resultado(idx))
        return

    if context.user_data.get("esperando_monto"):
        if m:
            monto = float(m.group(0))
            context.user_data["monto"] = monto
            context.user_data["esperando_monto"] = False
            context.user_data["esperando_tipster"] = True
            await update.message.reply_text("💰 $%s OK - Ahora TIPSTER:" % str(monto))
            return
        return

    if len(texto) > 3 and not es_num:
        if texto in ["📊 BALANCE","BALANCE","⏳ PENDIENTES","PENDIENTES","👥 TIPSTERS 7","TIPSTERS 7","📋 LISTADO","LISTADO"]:
            return
        context.user_data["pick"] = texto[:500]
        context.user_data["esperando_monto"] = True
        await update.message.reply_text("📌 Pick OK, manda MONTO:")
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
        await q.edit_message_text("✅ %s #%d %s" % (datos[idx]["resultado"], idx, tipster), reply_markup=teclado_resultado(idx))
        if acc == "lose":
            await verificar_alertas(context, tipster)
    except:
        pass

def build_app():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, mensaje))
    return app

def main():
    print("V24 INICIADO", flush=True)
    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()
    build_app().run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()