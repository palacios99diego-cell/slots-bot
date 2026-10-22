import json, os, re, threading, asyncio
from datetime import datetime
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVO = "apuestas.json"
app_web = Flask(__name__)

@app_web.route("/")
def home(): return "V18 FINAL OK"

def cargar():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO,"r") as f: return json.load(f)
        except: pass
    return []
def guardar(d):
    with open(ARCHIVO,"w") as f: json.dump(d,f,indent=2)

# TECLADO PARA MARCAR RESULTADO
def teclado_resultado(idx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 VERDE", callback_data=f"win_{idx}"), InlineKeyboardButton("🔴 ROJO", callback_data=f"lose_{idx}")],
        [InlineKeyboardButton("🟡 NULO", callback_data=f"nulo_{idx}"), InlineKeyboardButton("⏳ PENDIENTE", callback_data=f"pend_{idx}")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    teclado = [["📊 BALANCE","⏳ PENDIENTES"], ["🔴 ROJOS","🟢 VERDES"]]
    await update.message.reply_text("✅ V18 FINAL\nManda tu apuesta (puedes reenviarla) y te pido MONTO y TIPSTER", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def pendientes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos=cargar()
    pendientes=[(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
    if not pendientes:
        await update.message.reply_text("✅ No tienes pendientes")
        return
    await update.message.reply_text(f"⏳ Tienes {len(pendientes)} pendientes:")
    for idx, ap in pendientes[-10:]: # ultimas 10
        txt=f"⏳ {ap['fecha']}\n👤 {ap['tipster']} 💰 ${ap['monto']}\n📌 {ap['pick'][:80]}"
        await update.message.reply_text(txt, reply_markup=teclado_resultado(idx))

async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto=(update.message.text or "").strip()
    if not texto: return
    datos=cargar()

    # BOTONES DEL TECLADO
    if "BALANCE" in texto:
        v=len([x for x in datos if x["resultado"]=="VERDE"])
        r=len([x for x in datos if x["resultado"]=="ROJO"])
        p=len([x for x in datos if x["resultado"]=="PENDIENTE"])
        n=len([x for x in datos if x["resultado"]=="NULO"])
        await update.message.reply_text(f"📊 BALANCE\nTotal: {len(datos)}\n🟢 {v} Verdes\n🔴 {r} Rojos\n⏳ {p} Pendientes\n🟡 {n} Nulos\n\nUsa ⏳ PENDIENTES para editar")
        return
    if "PENDIENTES" in texto:
        await pendientes_cmd(update, context); return
    if "ROJOS" in texto:
        rojos=[x for x in datos if x["resultado"]=="ROJO"]
        txt="\n".join([f"{x['fecha']} ${x['monto']} {x['tipster']}" for x in rojos[-15:]]) or "Sin rojos"
        await update.message.reply_text(f"🔴 ROJOS:\n{txt}"); return
    if "VERDES" in texto:
        verdes=[x for x in datos if x["resultado"]=="VERDE"]
        txt="\n".join([f"{x['fecha']} ${x['monto']} {x['tipster']}" for x in verdes[-15:]]) or "Sin verdes"
        await update.message.reply_text(f"🟢 VERDES:\n{txt}"); return

    es_numero=bool(re.match(r"^\d+(\.\d+)?$", texto))

    # 3. ESPERANDO TIPSTER -> GUARDA
    if context.user_data.get("esperando_tipster"):
        tipster=texto
        monto=context.user_data.get("monto")
        pick=context.user_data.get("pick")
        nuevo={"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
        datos.append(nuevo); guardar(datos)
        idx=len(datos)-1
        context.user_data.clear()
        await update.message.reply_text(f"✅ GUARDADA COMO PENDIENTE\n👤 {tipster}\n💰 ${monto}\n📌 {pick[:150]}\n\nAhora marca el resultado:", reply_markup=teclado_resultado(idx))
        return

    # 2. ESPERANDO MONTO
    if context.user_data.get("esperando_monto"):
        if es_numero:
            context.user_data["monto"]=float(texto)
            context.user_data["esperando_monto"]=False
            context.user_data["esperando_tipster"]=True
            await update.message.reply_text(f"💰 ${texto} OK\nAhora manda el TIPSTER (ej: Método escalera)")
            return
        else:
            await update.message.reply_text("❌ Solo el número. Ej: 70"); return

    # 1. NUEVO PICK
    if not es_numero and len(texto)>2:
        context.user_data["pick"]=texto[:500]
        context.user_data["esperando_monto"]=True
        context.user_data["esperando_tipster"]=False
        await update.message.reply_text(f"📌 Pick recibido:\n{texto[:120]}\n\nManda el MONTO (ej: 70)")
        return

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    datos=cargar()
    try:
        acc, idx = q.data.split("_"); idx=int(idx)
        if acc=="win": datos[idx]["resultado"]="VERDE"; emoji="🟢 VERDE"
        elif acc=="lose": datos[idx]["resultado"]="ROJO"; emoji="🔴 ROJO"
        elif acc=="nulo": datos[idx]["resultado"]="NULO"; emoji="🟡 NULO"
        else: datos[idx]["resultado"]="PENDIENTE"; emoji="⏳ PENDIENTE"
        guardar(datos)
        ap=datos[idx]
        await q.edit_message_text(f"{emoji}\n👤 {ap['tipster']} 💰 ${ap['monto']}\n📌 {ap['pick'][:100]}\n📅 {ap['fecha']}")
    except: pass

def build_app():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pendientes", pendientes_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    return app

def main():
    print("V18 FINAL INICIADO", flush=True)
    try: loop=asyncio.get_event_loop()
    except: 
        loop=asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()
    build_app().run_polling(drop_pending_updates=True)

if __name__=="__main__": main()