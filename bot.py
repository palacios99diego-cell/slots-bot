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
    return "V27.1 TIPSTER FIX OK"

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
        elif r in ["VERDE","NULO"]:
            break
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
        [InlineKeyboardButton("🟢 VERDE", callback_data=f"win_{idx}"), InlineKeyboardButton("🔴 ROJO", callback_data=f"lose_{idx}")],
        [InlineKeyboardButton("🟡 NULO", callback_data=f"nulo_{idx}"), InlineKeyboardButton("⏳ PEND", callback_data=f"pend_{idx}")]
    ])

async def verificar_alertas(context, tipster):
    datos = cargar()
    lista = [x for x in datos if x.get("tipster") == tipster]
    racha = racha_roja(lista)
    cid = get_chat(context)
    if not cid: return
    if racha >= 5:
        texto = f"🚨 ALERTA {racha} ROJAS SEGUIDAS 🚨\n\n👤 {tipster}\n🔴 Lleva {racha} perdidas"
        await context.bot.send_message(chat_id=cid, text=texto)

async def start(update, context):
    context.user_data.clear()
    context.user_data["chat_id"] = update.effective_chat.id
    save_chat(update.effective_chat.id)
    teclado = [["📊 BALANCE","⏳ PENDIENTES"],["👥 TIPSTERS 7","📋 LISTADO"]]
    await update.message.reply_text("✅ V27.1 ACTIVO", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

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
            txt += f"{i}. 🔴🔴 {tipster.upper()} 🔴🔴\n{emojis}\n⏳ Pendientes: {pendientes}\n➡️ {racha} ROJAS SEGUIDAS 🚨\n\n"
        else:
            txt += f"{i}. 👤 {tipster}\n{emojis}\n⏳ Pendientes: {pendientes}\n➡️ Racha roja: {racha}\n\n"
        i += 1
    await update.message.reply_text(txt)

async def balance_cmd(update, context):
    datos = cargar()
    total = len(datos)
    v = len([x for x in datos if x.get("resultado")=="VERDE"])
    r = len([x for x in datos if x.get("resultado")=="ROJO"])
    p = len([x for x in datos if x.get("resultado")=="PENDIENTE"])
    n = len([x for x in datos if x.get("resultado")=="NULO"])
    txt = f"📊 BALANCE\nTotal: {total}\n🟢 {v} Verdes\n🔴 {r} Rojos\n⏳ {p} Pendientes\n🟡 {n} Nulos\n\nUsa ⏳ PENDIENTES para editar"
    await update.message.reply_text(txt)

async def mostrar_pendientes_paginadas(chat_id, context, pagina=0):
    datos_filtrados = context.user_data.get("pend_filtradas")
    titulo_filtro = context.user_data.get("pend_titulo", "TODAS")
    if not datos_filtrados:
        await context.bot.send_message(chat_id=chat_id, text="✅ Sin pendientes")
        return
    total = len(datos_filtrados)
    total_paginas = (total + PEND_POR_PAGINA -1) // PEND_POR_PAGINA
    pagina = max(0, min(pagina, total_paginas-1))
    inicio = pagina * PEND_POR_PAGINA
    sub = datos_filtrados[inicio:inicio+PEND_POR_PAGINA]
    txt = f"⏳ {titulo_filtro}: {total} pendientes\nPágina {pagina+1}/{total_paginas} ({inicio+1} al {min(inicio+PEND_POR_PAGINA, total)})\n\n"
    for idx, ap in sub:
        txt += f"#{idx} {ap.get('tipster','')} ${ap.get('monto','')}\n{ap.get('pick','')[:80]}\n\n"
    keyboard = []
    for idx, ap in sub:
        keyboard.append([
            InlineKeyboardButton(f"🟢 {idx}", callback_data=f"win_{idx}"),
            InlineKeyboardButton(f"🔴 {idx}", callback_data=f"lose_{idx}"),
            InlineKeyboardButton(f"🟡 {idx}", callback_data=f"nulo_{idx}")
        ])
    nav = []
    if pagina > 0: nav.append(InlineKeyboardButton("⬅️ ANTERIOR", callback_data=f"pg_{pagina-1}"))
    if pagina < total_paginas -1: nav.append(InlineKeyboardButton("SIGUIENTE ➡️", callback_data=f"pg_{pagina+1}"))
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("⬅️ VOLVER A TIPSTERS", callback_data="pend_menu")])
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(keyboard))

async def pendientes_cmd(update, context, filtro_texto=None):
    datos = cargar()
    pend = [(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
    if not pend:
        await update.message.reply_text("✅ Sin pendientes")
        return
    if filtro_texto:
        filtro_texto = filtro_texto.lower().strip()
        filtradas = [(i,x) for i,x in pend if filtro_texto in x.get("tipster","").lower()]
        if not filtradas:
            await update.message.reply_text(f"No hay pendientes de '{filtro_texto}'")
            return
        context.user_data["pend_filtradas"] = filtradas
        context.user_data["pend_titulo"] = filtro_texto.upper()
        await mostrar_pendientes_paginadas(update.effective_chat.id, context, 0)
        return
    conteo = Counter([x[1].get("tipster","Sin tipster") for x in pend])
    txt = f"📊 Tienes {len(pend)} pendientes\n\n👇 Elige TIPSTER para editar:"
    keyboard = []
    for tipster, cant in conteo.most_common():
        safe = tipster[:30]
        keyboard.append([InlineKeyboardButton(f"{safe} ({cant})", callback_data=f"tip_{tipster[:40]}")])
    keyboard.append([InlineKeyboardButton(f"📋 VER LAS {len(pend)} TODAS", callback_data="tip_ALL")])
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(keyboard))

async def mensaje(update, context):
    msg = update.message
    texto = (msg.text or msg.caption or "").strip()
    if not texto: return
    context.user_data["chat_id"] = update.effective_chat.id
    save_chat(update.effective_chat.id)
    datos = cargar()
    if texto in ["📊 BALANCE","BALANCE"]:
        await balance_cmd(update, context)
        return
    if texto.startswith("⏳ PENDIENTES") or texto.startswith("PENDIENTES"):
        resto = texto.replace("⏳ PENDIENTES","").replace("PENDIENTES","").strip()
        filtro = resto if resto else None
        await pendientes_cmd(update, context, filtro_texto=filtro)
        return
    if "TIPSTERS" in texto or "LISTADO" in texto:
        await tipsters_cmd(update, context)
        return
    m_rapido = re.match(r"^(VERDE|ROJO|NULO|PEND)\s+(\d+)", texto.upper())
    if m_rapido:
        acc = m_rapido.group(1)
        idx = int(m_rapido.group(2))
        if 0 <= idx < len(datos):
            mapa = {"VERDE":"VERDE","ROJO":"ROJO","NULO":"NULO","PEND":"PENDIENTE"}
            datos[idx]["resultado"] = mapa[acc]
            guardar(datos)
            await update.message.reply_text(f"✅ #{idx} ahora {mapa[acc]} ({datos[idx].get('tipster','')})")
            if acc == "ROJO":
                await verificar_alertas(context, datos[idx].get("tipster","?"))
            return
    m = re.search(r"\d+(\.\d+)?", texto)
    es_num = bool(re.fullmatch(r"\s*\$?\s*\d+(\.\d+)?\s*", texto))
    if context.user_data.get("esperando_tipster"):
        tipster = texto[:50]
        monto = context.user_data.get("monto")
        pick = context.user_data.get("pick")
        pendientes_mismo = [x for x in datos if x.get("tipster","").lower() == tipster.lower() and x.get("resultado") == "PENDIENTE"]
        if pendientes_mismo:
            await update.message.reply_text(f"⚠️ YA TIENES {len(pendientes_mismo)} PENDIENTE(S) DE 👤 {tipster}")
        nuevo = {"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
        datos.append(nuevo)
        guardar(datos)
        idx = len(datos)-1
        context.user_data.pop("esperando_tipster", None)
        await update.message.reply_text(f"✅ Guardada #{idx} 👤 {tipster}", reply_markup=teclado_resultado(idx))
        return
    if context.user_data.get("esperando_monto"):
        if m:
            monto = float(m.group(0))
            context.user_data["monto"] = monto
            context.user_data["esperando_monto"] = False
            context.user_data["esperando_tipster"] = True
            await update.message.reply_text(f"💰 ${monto} OK - Ahora TIPSTER:")
            return
        return
    if len(texto) > 3 and not es_num:
        if texto in ["📊 BALANCE","BALANCE","⏳ PENDIENTES","PENDIENTES","👥 TIPSTERS 7","TIPSTERS 7","📋 LISTADO","LISTADO"]: return
        context.user_data["pick"] = texto[:500]
        context.user_data["esperando_monto"] = True
        await update.message.reply_text("📌 Pick OK, manda MONTO:")
        return

async def callback(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data
    datos = cargar()
    if data == "pend_menu":
        try: await q.delete_message()
        except: pass
        pend = [(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
        if not pend:
            await context.bot.send_message(chat_id=q.message.chat_id, text="✅ Sin pendientes")
            return
        conteo = Counter([x[1].get("tipster","Sin tipster") for x in pend])
        txt = f"📊 Tienes {len(pend)} pendientes\n\n👇 Elige TIPSTER:"
        keyboard = []
        for tipster, cant in conteo.most_common():
            keyboard.append([InlineKeyboardButton(f"{tipster[:30]} ({cant})", callback_data=f"tip_{tipster[:40]}")])
        keyboard.append([InlineKeyboardButton(f"📋 VER LAS {len(pend)} TODAS", callback_data="tip_ALL")])
        await context.bot.send_message(chat_id=q.message.chat_id, text=txt, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data.startswith("tip_"):
        tipster_filtro = data[4:]
        pend = [(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
        if tipster_filtro == "ALL":
            filtradas = pend
            titulo = "TODAS"
        else:
            filtradas = [(i,x) for i,x in pend if tipster_filtro.lower() in x.get("tipster","").lower()]
            titulo = tipster_filtro.upper()
        context.user_data["pend_filtradas"] = filtradas
        context.user_data["pend_titulo"] = titulo
        try: await q.delete_message()
        except: pass
        await mostrar_pendientes_paginadas(q.message.chat_id, context, 0)
        return
    if data.startswith("pg_"):
        try:
            pagina = int(data.split("_")[1])
            try: await q.delete_message()
            except: pass
            await mostrar_pendientes_paginadas(q.message.chat_id, context, pagina)
        except: pass
        return
    try:
        acc, idx = data.split("_")
        idx = int(idx)
        if acc == "win": datos[idx]["resultado"] = "VERDE"
        elif acc == "lose": datos[idx]["resultado"] = "ROJO"
        elif acc == "nulo": datos[idx]["resultado"] = "NULO"
        else: datos[idx]["resultado"] = "PENDIENTE"
        guardar(datos)
        tipster = datos[idx].get("tipster","?")
        await q.edit_message_text(f"✅ {datos[idx]['resultado']} #{idx} {tipster}", reply_markup=teclado_resultado(idx))
        if acc == "lose": await verificar_alertas(context, tipster)
    except Exception as e:
        print(f"Error callback: {e}")

def build_app():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pendientes", pendientes_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, mensaje))
    return app

def main():
    print("V27.1 INICIADO - TIPSTER + PAGINACION FIX", flush=True)
    try: loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()
    build_app().run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()