import json, os, re, threading
from datetime import datetime
from flask import Flask
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVO = "apuestas.json"

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Bot V18 Activo"

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

def start(update, context):
    context.user_data.clear()
    teclado = [["📊 BALANCE","🔴 LISTADO ROJOS"]]
    update.message.reply_text("✅ V18 VIVO - Manda el partido y te respondo al tiro", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

def mensaje(update, context):
    texto = (update.message.text or "").strip()
    datos = cargar()

    if "BALANCE" in texto:
        update.message.reply_text(f"💰 Balance: {len(datos)} apuestas"); return
    if "LISTADO ROJOS" in texto:
        update.message.reply_text("🔴 Listado: revisando..."); return

    es_numero = bool(re.match(r"^\d+(\.\d+)?$", texto))

    if context.user_data.get("esperando_tipster"):
        tipster = texto
        monto = context.user_data.get("monto")
        pick = context.user_data.get("pick")
        nuevo = {"fecha": datetime.now().strftime("%d/%m %H:%M"), "tipster": tipster, "monto": monto, "pick": pick, "resultado": "PENDIENTE"}
        datos.append(nuevo); guardar(datos)
        idx = len(datos)-1
        context.user_data.clear()
        botones = [[InlineKeyboardButton("🟢 VERDE", callback_data=f"win_{idx}"), InlineKeyboardButton("🔴 ROJO", callback_data=f"lose_{idx}")],[InlineKeyboardButton("🟡 NULO", callback_data=f"nulo_{idx}")]]
        update.message.reply_text(f"✅ GUARDADA\n👤 {tipster}\n💰 ${monto}\n📌 {pick}", reply_markup=InlineKeyboardMarkup(botones))
        return

    if context.user_data.get("esperando_monto"):
        if es_numero:
            context.user_data["monto"] = float(texto)
            context.user_data["esperando_monto"] = False
            context.user_data["esperando_tipster"] = True
            update.message.reply_text(f"💰 ${texto} OK, ahora el TIPSTER")
            return
        else:
            update.message.reply_text(f"❌ No es monto. Manda solo el número, ej: 70")
            return

    if not es_numero and len(texto) > 2:
        context.user_data["pick"] = texto[:200]
        context.user_data["esperando_monto"] = True
        update.message.reply_text(f"📌 Pick: {texto[:80]}\n\nAhora manda el MONTO (70)")
        return

    update.message.reply_text(f"Recibido: {texto}")

def callback(update, context):
    q=update.callback_query; q.answer()
    datos=cargar()
    acc, idx = q.data.split("_"); idx=int(idx)
    if acc=="win": datos[idx]["resultado"]="VERDE"
    elif acc=="lose": datos[idx]["resultado"]="ROJO"
    elif acc=="nulo": datos[idx]["resultado"]="NULO"
    guardar(datos)
    q.edit_message_text(f"{'🟢' if acc=='win' else '🔴' if acc=='lose' else '🟡'} {datos[idx]['tipster']} ${datos[idx]['monto']} -> {datos[idx]['resultado']}")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, mensaje))
    print("V18 INICIADO v13")
    updater.start_polling()
    updater.idle()

if __name__=="__main__":
    main()