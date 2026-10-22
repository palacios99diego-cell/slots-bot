import json, os, re, threading, asyncio
from datetime import datetime
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVO = "apuestas.json"
app_web = Flask(__name__)
@app_web.route("/")
def home(): return "V18 FIX OK"

def cargar():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO,"r") as f: return json.load(f)
        except: pass
    return []
def guardar(d):
    with open(ARCHIVO,"w") as f: json.dump(d,f,indent=2)

def teclado_resultado(idx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 VERDE", callback_data=f"win_{idx}"), InlineKeyboardButton("🔴 ROJO", callback_data=f"lose_{idx}")],
        [InlineKeyboardButton("🟡 NULO", callback_data=f"nulo_{idx}"), InlineKeyboardButton("⏳ PENDIENTE", callback_data=f"pend_{idx}")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    teclado = [["📊 BALANCE","⏳ PENDIENTES"], ["🔴 ROJOS","🟢 VERDES"]]
    await update.message.reply_text("✅ V18 FIX LISTO\n1. Reenvía la apuesta o escribe el pick\n2. Te pido MONTO\n3. Te pido TIPSTER\n4. Te salen los botones VERDE/ROJO", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def pendientes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos=cargar()
    pendientes=[(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
    if not pendientes:
        await update.message.reply_text("✅ No tienes pendientes"); return
    await update.message.reply_text(f"⏳ {len(pendientes)} pendientes (ultimas 10):")
    for idx, ap in pendientes[-10:]:
        txt=f"⏳ {ap['fecha']}\n👤 {ap['tipster']} 💰 ${ap['monto']}\n📌 {ap['pick'][:120]}"
        await update.message.reply_text(txt, reply_markup=teclado_resultado(idx))

# ESTA ES LA FUNCION QUE ARREGLA TU ERROR
async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lee TEXTO o DESCRIPCION DE FOTO (caption) - esto arregla el reenvío
    msg = update.message
    texto = (msg.text or msg.caption or "").strip()
    if not texto: 
        await update.message.reply_text("Manda el texto de la apuesta")
        return

    datos=cargar()
    print(f"TEXTO: {texto[:50]} | ESTADO: {context.user_data}")

    if "BALANCE" in texto:
        v=len([x for x in datos if x.get("resultado")=="VERDE"])
        r=len([x for x in datos if x.get("resultado")=="ROJO"])
        p=len([x for x in datos if x.get("resultado")=="PENDIENTE"])
        n=len([x for x in datos if x.get("resultado")=="NULO"])
        await update.message.reply_text(f"📊 BALANCE\nTotal: {len(datos)}\n🟢 {v} Verdes\n🔴 {r} Rojos\n⏳ {p} Pendientes\n🟡 {n} Nulos"); return
    if "PENDIENTES" in texto:
        await pendientes_cmd(update, context); return
    if "ROJOS" in texto and len(texto)<10:
        await update.message.reply_text("🔴 ROJOS: "+str([f"{x['tipster']} ${x['monto']}" for x in datos if x.get("resultado")=="ROJO"][-10:])); return
    if "VERDES" in texto and len(texto)<10:
        await update.message.reply_text("🟢 VERDES: "+str([f"{x['tipster']} ${x['monto']}" for x in datos if x.get("resultado")=="VERDE"][-10:])); return

    # Detecta numero aunque venga con $ o espacios
    match_num = re.search(r"\d+(\.\d+)?", texto)
    es_numero = bool(re.fullmatch(r"\s*\$?\s*\d+(\.\d+)?\s*", texto))

    # 3. ESPERANDO TIPSTER
    if context.user_data.get("esperando_tipster"):
        tipster = texto[:50]
        monto = context.user_data.get("monto")
        pick = context.user_data.get("pick")
        nuevo = {"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
        datos.append(nuevo); guardar(datos)
        idx=len(datos)-1
        context.user_data.clear()
        await update.message.reply_text(f"✅ GUARDADA PENDIENTE\n👤 {tipster}\n💰 ${monto}\n📌 {pick[:150]}\n\nMarca el resultado:", reply_markup=teclado_resultado(idx))
        return

    # 2. ESPERANDO MONTO
    if context.user_data.get("esperando_monto"):
        if match_num:
            monto = float(match_num.group(0))
            context.user_data["monto"]=monto
            context.user_data["esperando_monto"]=False
            context.user_data["esperando_tipster"]=True
            await update.message.reply_text(f"💰 ${monto} OK\nAhora el TIPSTER:")
            return
        else:
            await update.message.reply_text("❌ Manda solo el monto, ej: 70"); return

    # 1. NUEVO PICK - cualquier texto largo que no sea numero
    if len(texto) > 3 and not es_numero:
        # Si es el reenvío feo con "HAGA CLICK", limpiamos
        pick_limpio = texto.replace("HAGA CLICK AQUI PARA REGISTRARSE Y RECIBIR BONO MULTIPLICADOR","").strip()
        if "RETO ESCALERA" in pick_limpio:
            pick_limpio = pick_limpio.split("RETO ESCALERA")[0].strip()
        context.user_data["pick"]=pick_limpio[:500]
        context.user_data["esperando_monto"]=True
        context.user_data["esperando_tipster"]=False
        await update.message.reply_text(f"📌 Pick: {pick_limpio[:120]}\n\nManda el MONTO (ej: 70)")
        return

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    datos=cargar()
    try:
        acc, idx = q.data.split("_"); idx=int(idx)
        if acc=="win": datos[idx]["resultado"]="VERDE"; e="🟢 VERDE"
        elif acc=="lose": datos[idx]["resultado"]="ROJO"; e="🔴 ROJO"
        elif acc=="nulo": datos[idx]["resultado"]="NULO"; e="🟡 NULO"
        else: datos[idx]["resultado"]="PENDIENTE"; e="⏳ PENDIENTE"
        guardar(datos)
        ap=datos[idx]
        await q.edit_message_text(f"{e}\n👤 {ap['tipster']} 💰 ${ap['monto']}\n📌 {ap['pick'][:120]}")
    except Exception as ex:
        print(f"Error callback: {ex}")

def build_app():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pendientes", pendientes_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    # ESTO ES LO QUE FALTABA: lee texto Y caption de fotos
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, mensaje))
    return app

def main():
    print("V18 FIX INICIADO", flush=True)
    try: loop=asyncio.get_event_loop()
    except: loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()
    build_app().run_polling(drop_pending_updates=True)

if __name__=="__main__": main()