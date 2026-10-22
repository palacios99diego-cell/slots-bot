import json, os, threading
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
            with open(ARCHIVO,"r") as f: return json.load(f)
        except: pass
    return []
def guardar(d):
    with open(ARCHIVO,"w") as f: json.dump(d,f,indent=2)

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    kb = [["📊 BALANCE","🔴 LISTADO ROJOS"]]
    await update.message.reply_text("✅ V18 LISTO - Manda tu pick", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def mensaje(update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    datos = cargar()
    if "BALANCE" in txt:
        await update.message.reply_text(f"💰 {len(datos)} apuestas")
        return
    # Estados
    if context.user_data.get("esperando_tipster"):
        nuevo = {"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":txt, "monto":context.user_data.get("monto"), "pick":context.user_data.get("pick"), "resultado":"PENDIENTE"}
        datos.append(nuevo); guardar(datos)
        idx=len(datos)-1; context.user_data.clear()
        btns=[[InlineKeyboardButton("🟢 VERDE",callback_data=f"win_{idx}"),InlineKeyboardButton("🔴 ROJO",callback_data=f"lose_{idx}")],[InlineKeyboardButton("🟡 NULO",callback_data=f"nulo_{idx}")]]
        await update.message.reply_text(f"✅ GUARDADA\n👤 {txt}\n💰 ${nuevo['monto']}\n📌 {nuevo['pick']}", reply_markup=InlineKeyboardMarkup(btns))
        return
    if context.user_data.get("esperando_monto"):
        try:
            context.user_data["monto"]=float(txt)
            context.user_data["esperando_monto"]=False
            context.user_data["esperando_tipster"]=True
            await update.message.reply_text(f"💰 ${txt} OK, ahora el TIPSTER")
            return
        except: pass
    if len(txt)>2:
        context.user_data["pick"]=txt[:200]
        context.user_data["esperando_monto"]=True
        await update.message.reply_text(f"📌 Pick: {txt[:80]}\nAhora manda MONTO (ej: 70)")
        return

async def callback(update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    datos=cargar(); acc,idx = q.data.split("_"); idx=int(idx)
    if acc=="win": datos[idx]["resultado"]="VERDE"
    elif acc=="lose": datos[idx]["resultado"]="ROJO"
    else: datos[idx]["resultado"]="NULO"
    guardar(datos); await q.edit_message_text(f"{datos[idx]['resultado']} - {datos[idx]['tipster']}")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    print("V18 INICIADO")
    app.run_polling()

if __name__=="__main__": main()