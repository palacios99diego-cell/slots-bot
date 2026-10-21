import json, os, re, threading
from datetime import datetime
from flask import Flask
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

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
def guardar(d):
    with open(ARCHIVO, "w") as f: json.dump(d, f, indent=2)

async def start(update, context):
    context.user_data.clear()
    teclado = [["📊 BALANCE","🔴 LISTADO ROJOS"]]
    await update.message.reply_text("✅ V18 VIVO - Manda el partido y te respondo al tiro", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def mensaje(update, context):
    texto = (update.message.text or "").strip()
    datos = cargar()
    if "BALANCE" in texto:
        await update.message.reply_text(f"💰 Balance: {len(datos)} apuestas"); return
    es_numero = bool(re.match(r"^\d+(\.\d+)?$", texto))
    if context.user_data.get("esperando_tipster"):
        nuevo = {"fecha": datetime.now().strftime("%d/%m %H:%M"), "tipster": texto, "monto": context.user_data.get("monto"), "pick": context.user_data.get("pick"), "resultado": "PENDIENTE"}
        datos.append(nuevo); guardar(datos); idx=len(datos)-1
        context.user_data.clear()
        botones = [[InlineKeyboardButton("🟢 VERDE", callback_data=f"win_{idx}"), InlineKeyboardButton("🔴 ROJO", callback_data=f"lose_{idx}")],[InlineKeyboardButton("🟡 NULO", callback_data=f"nulo_{idx}")]]
        await update.message.reply_text(f"✅ GUARDADA\n👤 {texto}\n💰 ${nuevo['monto']}\n📌 {nuevo['pick']}", reply_markup=InlineKeyboardMarkup(botones)); return
    if context.user_data.get("esperando_monto"):
        if es_numero:
            context.user_data["monto"]=float(texto); context.user_data["esperando_monto"]=False; context.user_data["esperando_tipster"]=True
            await update.message.reply_text(f"💰 ${texto} OK, ahora el TIPSTER"); return
        else:
            await update.message.reply_text(f"❌ Manda solo el número, ej: 70"); return
    if not es_numero and len(texto)>2:
        context.user_data["pick"]=texto[:200]; context.user_data["esperando_monto"]=True
        await update.message.reply_text(f"📌 Pick: {texto[:80]}\n\nAhora manda el MONTO (70)"); return

async def callback(update, context):
    q=update.callback_query; await q.answer()
    datos=cargar(); acc, idx = q.data.split("_"); idx=int(idx)
    if acc=="win": datos[idx]["resultado"]="VERDE"
    elif acc=="lose": datos[idx]["resultado"]="ROJO"
    else: datos[idx]["resultado"]="NULO"
    guardar(datos)
    await q.edit_message_text(f"{datos[idx]['resultado']} - {datos[idx]['tipster']} ${datos[idx]['monto']}")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    print("V18 INICIADO 21.6")
    app.run_polling()

if __name__=="__main__": main()