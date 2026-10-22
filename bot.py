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
TIPSTERS_POR_PAGINA = 30

TIPSTERS_BASE = ["A'C PICKS", "ALBERTO 10", "ALEIX TENIS", "ALEJANDRO NUMERO UNO", "ALEX ANALISTA", "ALL SPORT TIPSTERS", "ALLSPORTSPICKS", "ALPHATEAM", "AMBOS ANOTAN", "AMBOS MARCAN", "AMBOS/MARCAN", "ANALISIS J&D", "ANALISIS SEBASTIAN", "ANALISTA DEL DEPORTE", "ANALISTA EL COBRADOR", "ANALISTA EXPERTO", "ANALISTA JUAN", "ANALISTA NBA", "ANDRINOS", "ANGELICA +2.5 GOLES", "ANONIMO TEAM", "APG APUESTA", "APOLO GOL", "APUESTA DEPORTIVA DIARIA", "APUESTA MAGICA", "APUESTAS EINSTEIN", "APUESTAS J'B", "APUESTAS JR", "APUESTAS LOREN", "APUESTAS ML ANALISTAS", "APUESTAS PARA INVERSORES", "APUESTAS TOP", "ARK APUESTAS", "ART EN VERDE", "ASESTIPS", "ASTIPSTER BASKET", "BASKET ANALYST", "BERLIN ANALISTAS", "BEST BET", "BET KING", "BET PANTHER", "BETSEVOLUTION", "BETSUITE", "BILBETS", "BILLY EL NIÑO VIP", "BIOSCA APUESTA", "BRAIS ASTIPSTER", "BREAKINGBETS", "BREAK POINT", "CANAL GRATIS ANDRES", "CAPO BETS", "CASH EN JUEGO", "CAYE BETS", "COACHBETS", "CODIGO FUTBOL", "COEBETS", "DATA SPORT EC", "DAVID D PICKS", "DAVIDBETS", "DC APUESTAS", "DELTA FORCE", "DEPORTES TOP", "DESTRUCTOR BETS", "DIEGO LA VIDA", "DIEGO VALEIRAS", "DINERO EXTRA", "DIOS ANALISTA", "DM7", "DRAGON BALL SPECIAL EVENT", "DRAGON BALL STAKES 10", "DRAGON DE LAS APUESTAS", "DRAGON SPORT FREE", "DUTTI BETS", "EAGKE BETS", "EL CAMPEON", "EL CAZADOR", "EL CHARRO VERDE", "EL CLAN DE LOS PRONOSTICOS", "EL CLUB DE GREEN", "EL DANI ANALISTA", "EL DT GRATIS", "EL GURU DE LAS APUESTAS", "EL INGENIERO", "EL JEQUE", "EL LUPPO", "EL MAESTRO APUESTA", "EL NBA POINT", "EL POTON", "EL PROFE", "EL PROFESOR", "EL SARCO APUESTAS", "EL TIPSTER 100%", "FABIAN ANALISTA", "FIRE STAKE 10", "FREIRE BETS", "FULLBETS", "GALICIA PICKS", "GAME GURU", "GENIS TIPSTER", "GOLES Y RETOS", "GONZALO ASTIPSTERS", "GONZALO MULTIDEPORTES", "GREEN ZONE", "GUAJE", "GURU PRONOSTICOS", "HASSIDO", "HERO OFICIAL", "HUGO GANADOR", "IA ANALISTAS", "IKER POWERBETS", "IMPACTO 365", "INFO WIN", "JAVI MORENO", "JB APUESTAS", "JEFE GROUP", "JJ ANALISTAS", "JOEL BETS", "JOTAS PICKS", "JR TIPS", "JUAN ANLISTA", "JUAN APUESTAS", "JUANESBET", "JUANTE88", "KILLER TENISS", "KRILLIN PICKS", "LABORATORIO DEL GOL", "LA INGENIERA AMBOS", "LATAM ANALISTAS", "LEO TIPS", "LIVES 365", "LUCAS", "LUCIA BETS", "LU APUESTAS", "MAGO DEL TENIS", "MARTINA BETS", "MASTER GOLES", "MATIAS", "MEGA APUESTAS", "MEGA STAKE", "MEJORES. CASAS DE APUESTAS", "METODO ESCALERA", "METODO GOL", "METODO TENNIS", "MG PRO APUESTA", "MIKEL SNIPER", "MILANO", "MONARCA TIPS", "MR GREEN", "MR LIGA PRO", "MRPICKS", "MULTIAPUESTAS", "MULTIPICKS", "NBA KILLER", "NC DEPORTES", "NDO BETS", "NICOLAS PRONOSTICO", "ONLY PICKS", "ONLY VIP TIPSTER", "PABLO RAMIREZ", "PARLEY DE GOLES", "PEDRO EL LOCO", "PICKS El MIRANDA", "PLUTO", "POWER BETS", "PRO ANALYST", "PUTEUS BETS", "RADAR DE GOLES", "RAFAXTOPBET", "REY ANALISTA", "REY ANALISTA BALONCESTO", "ROI CANAL GRATUITO", "RODSTHEIN", "RUIZ APUESTAS", "S.P.R.T.S APSTS", "SAVAGE PICKS", "SEBAS PICKS", "SELU APUESTAS", "SENSEI BETS", "SISTEMA DE FUTBOL", "SITO JR", "SITO NBA", "SPANISH PICKS", "SPIDER ANALISTA", "SPORT' DF", "SR APUESTAS", "STAKE10 DARLING", "STAKE ANALISTAS", "STAKE 10 FUTBOL", "STAKES 10 JB", "STAKE REAL", "SUPER APUESTA", "TEAM PRONOSTICOS", "TEMIS BET", "TIPS COMANDANTE", "TIPS ENIGMA", "TIPS PRO", "TIPS Z MASTER", "TIPSFALCON", "TIPBASE INFO", "TIPSELVERDE TENNIS", "TIPSTER DB", "TIPSTER MILLONARIO", "TIPSTER VERDE FREE", "TITAN ANALYST", "TITAN BETS", "TONII BETS", "TREBOL GOL", "VERDAZO SEGURO", "VIP APUESTAS", "VIP SEPTIEMBRE ANDRES", "W1NNER APUESTAS", "WALL STREET", "WEST PRONOSTICOS", "WETS APUESTA", "WIN Y RUN", "ZCODE ESPAÑOL", "ZEUS ANALISTA", "ZONA ANALISTA"]

@app_web.route("/")
def home():
    return "V28.2 223 TIPSTERS + EDITAR OK"

def cargar():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO, "r") as f:
                return json.load(f)
        except: pass
    return []

def guardar(d):
    with open(ARCHIVO, "w") as f:
        json.dump(d, f, indent=2)

def save_chat(cid):
    try:
        with open(CHAT_FILE, "w") as f: f.write(str(cid))
    except: pass

def get_chat(context):
    cid = context.user_data.get("chat_id") if context and context.user_data else None
    if cid: return cid
    if os.path.exists(CHAT_FILE):
        try:
            with open(CHAT_FILE, "r") as f: return int(f.read().strip())
        except: pass
    return None

def get_all_tipsters():
    datos = cargar()
    file_tips = [x.get("tipster","") for x in datos if x.get("tipster")]
    combinado = TIPSTERS_BASE + file_tips
    seen = {}
    for t in combinado:
        if not t: continue
        k = t.strip().lower()
        if k not in seen: seen[k] = t.strip()
    return sorted(seen.values(), key=lambda x: x.lower())

def racha_roja(lista):
    racha = 0
    for ap in reversed(lista):
        r = ap.get("resultado")
        if r == "ROJO": racha += 1
        elif r in ["VERDE","NULO"]: break
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

async def mostrar_selector_tipsters_guardar(chat_id, context, pagina=0, filtro=None):
    todos = get_all_tipsters()
    if filtro:
        filtro_low = filtro.lower()
        todos = [t for t in todos if filtro_low in t.lower()]
    if not todos:
        todos = get_all_tipsters()
        filtro = None
    total = len(todos)
    total_pag = (total + TIPSTERS_POR_PAGINA -1)//TIPSTERS_POR_PAGINA
    pagina = max(0, min(pagina, total_pag-1))
    inicio = pagina*TIPSTERS_POR_PAGINA
    sub = todos[inicio:inicio+TIPSTERS_POR_PAGINA]
    titulo = f"📋 Elige TIPSTER ({total} total)"
    if filtro: titulo = f"🔍 '{filtro}' - {total} encontrados"
    keyboard = []
    for i in range(0, len(sub), 2):
        fila = []
        for t in sub[i:i+2]:
            fila.append(InlineKeyboardButton(t[:18], callback_data=f"addtip_{t[:40]}"))
        keyboard.append(fila)
    nav=[]
    if pagina>0: nav.append(InlineKeyboardButton("⬅️ Ant", callback_data=f"addpg_{pagina-1}_{filtro or ''}"))
    if pagina<total_pag-1: nav.append(InlineKeyboardButton("Sig ➡️", callback_data=f"addpg_{pagina+1}_{filtro or ''}"))
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("➕ AÑADIR NUEVO TIPSTER", callback_data="addtip_new")])
    keyboard.append([InlineKeyboardButton("❌ CANCELAR", callback_data="addtip_cancel")])
    txt = f"{titulo}\nPágina {pagina+1}/{total_pag}\n\n💡 Escribe parte del nombre para filtrar. Ej: 'ale'\nSi no existe, pulsa ➕"
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(keyboard))

async def mostrar_pendientes_paginadas(chat_id, context, pagina=0):
    datos_filtrados = context.user_data.get("pend_filtradas")
    titulo_filtro = context.user_data.get("pend_titulo", "TODAS")
    if not datos_filtrados:
        await context.bot.send_message(chat_id=chat_id, text="✅ Sin pendientes")
        return
    total = len(datos_filtrados)
    total_paginas = (total + PEND_POR_PAGINA -1)//PEND_POR_PAGINA
    pagina = max(0, min(pagina, total_paginas-1))
    inicio = pagina*PEND_POR_PAGINA
    sub = datos_filtrados[inicio:inicio+PEND_POR_PAGINA]
    txt = f"⏳ {titulo_filtro}: {total} pendientes\nPágina {pagina+1}/{total_paginas} ({inicio+1} al {min(inicio+PEND_POR_PAGINA, total)})\n\n"
    for idx, ap in sub:
        txt += f"#{idx} {ap.get('tipster','')} ${ap.get('monto','')}\n{ap.get('pick','')[:80]}\n\n"
    keyboard=[]
    for idx, ap in sub:
        keyboard.append([
            InlineKeyboardButton(f"🟢 {idx}", callback_data=f"win_{idx}"),
            InlineKeyboardButton(f"🔴 {idx}", callback_data=f"lose_{idx}"),
            InlineKeyboardButton(f"🟡 {idx}", callback_data=f"nulo_{idx}")
        ])
    nav=[]
    if pagina>0: nav.append(InlineKeyboardButton("⬅️ ANTERIOR", callback_data=f"pg_{pagina-1}"))
    if pagina<total_paginas-1: nav.append(InlineKeyboardButton("SIGUIENTE ➡️", callback_data=f"pg_{pagina+1}"))
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("⬅️ VOLVER A TIPSTERS", callback_data="pend_menu")])
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update, context):
    context.user_data.clear()
    context.user_data["chat_id"]=update.effective_chat.id
    save_chat(update.effective_chat.id)
    teclado=[["📊 BALANCE","⏳ PENDIENTES"],["👥 TIPSTERS 7","📋 LISTADO"],["✏️ EDITAR TIPSTERS"]]
    await update.message.reply_text("✅ V28.2 223 TIPSTERS + EDITAR ACTIVO", reply_markup=ReplyKeyboardMarkup(teclado, resize_keyboard=True))

async def tipsters_cmd(update, context):
    context.user_data["chat_id"]=update.effective_chat.id
    save_chat(update.effective_chat.id)
    datos=cargar()
    if not datos:
        await update.message.reply_text("Sin apuestas"); return
    agrupado=defaultdict(list)
    for x in datos: agrupado[x.get("tipster","?")].append(x)
    txt="📋 Listado con últimos 7:\n\n"
    i=1
    for tipster, lista in agrupado.items():
        racha=racha_roja(lista)
        emojis=ultimos_7_emojis(lista)
        pendientes=len([x for x in lista if x.get("resultado")=="PENDIENTE"])
        if racha>=5:
            txt+=f"{i}. 🔴🔴 {tipster.upper()} 🔴🔴\n{emojis}\n⏳ Pendientes: {pendientes}\n➡️ {racha} ROJAS SEGUIDAS 🚨\n\n"
        else:
            txt+=f"{i}. 👤 {tipster}\n{emojis}\n⏳ Pendientes: {pendientes}\n➡️ Racha roja: {racha}\n\n"
        i+=1
    await update.message.reply_text(txt)

async def balance_cmd(update, context):
    datos=cargar()
    total=len(datos)
    v=len([x for x in datos if x.get("resultado")=="VERDE"])
    r=len([x for x in datos if x.get("resultado")=="ROJO"])
    p=len([x for x in datos if x.get("resultado")=="PENDIENTE"])
    n=len([x for x in datos if x.get("resultado")=="NULO"])
    txt=f"📊 BALANCE\nTotal: {total}\n🟢 {v} Verdes\n🔴 {r} Rojos\n⏳ {p} Pendientes\n🟡 {n} Nulos"
    await update.message.reply_text(txt)

async def pendientes_cmd(update, context, filtro_texto=None):
    datos=cargar()
    pend=[(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
    if not pend:
        await update.message.reply_text("✅ Sin pendientes"); return
    if filtro_texto:
        filtro_texto=filtro_texto.lower().strip()
        filtradas=[(i,x) for i,x in pend if filtro_texto in x.get("tipster","").lower()]
        if not filtradas:
            await update.message.reply_text(f"No hay pendientes de '{filtro_texto}'"); return
        context.user_data["pend_filtradas"]=filtradas
        context.user_data["pend_titulo"]=filtro_texto.upper()
        await mostrar_pendientes_paginadas(update.effective_chat.id, context, 0)
        return
    conteo=Counter([x[1].get("tipster","Sin tipster") for x in pend])
    txt=f"📊 Tienes {len(pend)} pendientes\n\n👇 Elige TIPSTER:"
    keyboard=[]
    for tipster, cant in conteo.most_common(50):
        keyboard.append([InlineKeyboardButton(f"{tipster[:28]} ({cant})", callback_data=f"tip_{tipster[:40]}")])
    keyboard.append([InlineKeyboardButton(f"📋 VER LAS {len(pend)} TODAS", callback_data="tip_ALL")])
    keyboard.append([InlineKeyboardButton("🔍 BUSCAR TIPSTER", callback_data="pend_search")])
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(keyboard))

async def mensaje(update, context):
    msg=update.message
    texto=(msg.text or msg.caption or "").strip()
    
    if msg.photo and not texto:
        context.user_data["chat_id"]=update.effective_chat.id
        save_chat(update.effective_chat.id)
        if context.user_data.get("pick"):
            await update.message.reply_text("📸 Foto recibida y guardada con el Pick. Ahora manda el MONTO (ej: 10):")
            context.user_data["tiene_foto"]=True
        else:
            context.user_data["foto_temp"]=True
            await update.message.reply_text("📸 Foto recibida. Mándame ahora el Pick en texto (ej: Over 2.5) y luego el monto:")
        return

    if not texto: return
    context.user_data["chat_id"]=update.effective_chat.id
    save_chat(update.effective_chat.id)
    datos=cargar()

    if texto == "✏️ EDITAR TIPSTERS":
        todos = get_all_tipsters()
        txt = f"✏️ EDITAR TIPSTERS\nTienes {len(todos)} tipsters\n\nPara RENOMBRAR escribe:\n`Viejo -> Nuevo`\nEj: `MARTINA BETS -> MARTINA PRO`\n\nPara BORRAR todas las apuestas de uno escribe:\n`Borrar NOMBRE`\nEj: `Borrar MARTINA BETS`\n\nTipsters con apuestas:"
        conteo = Counter([x.get("tipster","") for x in datos])
        for t,c in conteo.most_common(20):
            txt+=f"\n- {t} ({c})"
        txt+="\n\nEscribe el comando o 'cancelar'"
        context.user_data["esperando_editar"]=True
        await update.message.reply_text(txt)
        return

    if context.user_data.get("esperando_editar"):
        if texto.lower() == "cancelar":
            context.user_data.pop("esperando_editar", None)
            await update.message.reply_text("❌ Edición cancelada")
            return
        if "->" in texto:
            try:
                viejo, nuevo = [x.strip() for x in texto.split("->",1)]
                if not viejo or not nuevo:
                    await update.message.reply_text("Formato mal. Usa: Viejo -> Nuevo")
                    return
                count = 0
                for d in datos:
                    if d.get("tipster","").strip().lower() == viejo.lower():
                        d["tipster"] = nuevo
                        count += 1
                for i, t in enumerate(TIPSTERS_BASE):
                    if t.lower() == viejo.lower():
                        TIPSTERS_BASE[i] = nuevo
                guardar(datos)
                context.user_data.pop("esperando_editar", None)
                await update.message.reply_text(f"✅ Renombrado: '{viejo}' -> '{nuevo}'\n{count} apuestas actualizadas")
                return
            except Exception as e:
                await update.message.reply_text(f"Error: {e}")
                return
        if texto.lower().startswith("borrar "):
            viejo = texto[7:].strip()
            count = len([d for d in datos if d.get("tipster","").lower() == viejo.lower()])
            if count == 0:
                await update.message.reply_text(f"No encontré tipster '{viejo}'")
                return
            context.user_data["borrar_temp"]=viejo
            await update.message.reply_text(f"⚠️ Vas a borrar {count} apuestas de '{viejo}'\nEscribe CONFIRMAR para borrar o 'cancelar'")
            return
        if texto.upper() == "CONFIRMAR" and context.user_data.get("borrar_temp"):
            viejo = context.user_data["borrar_temp"]
            datos_new = [d for d in datos if d.get("tipster","").lower() != viejo.lower()]
            guardar(datos_new)
            context.user_data.pop("esperando_editar", None)
            context.user_data.pop("borrar_temp", None)
            await update.message.reply_text(f"🗑️ Borradas {len(datos)-len(datos_new)} apuestas de '{viejo}'")
            return

    if context.user_data.get("esperando_nuevo_tipster_nombre"):
        nuevo_nombre = texto[:50].strip()
        tipster = nuevo_nombre
        if tipster not in TIPSTERS_BASE: TIPSTERS_BASE.append(tipster)
        monto = context.user_data.get("monto")
        pick = context.user_data.get("pick")
        if context.user_data.get("tiene_foto") or context.user_data.get("foto_temp"): pick = f"[FOTO] {pick}"
        nuevo = {"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
        datos.append(nuevo); guardar(datos)
        idx=len(datos)-1
        context.user_data.pop("esperando_nuevo_tipster_nombre", None)
        context.user_data.pop("esperando_tipster", None)
        context.user_data.pop("tiene_foto", None)
        context.user_data.pop("foto_temp", None)
        await update.message.reply_text(f"✅ Guardada #{idx} 👤 {tipster} (NUEVO)", reply_markup=teclado_resultado(idx))
        return
    if context.user_data.get("esperando_busqueda_pend"):
        context.user_data.pop("esperando_busqueda_pend", None)
        await pendientes_cmd(update, context, filtro_texto=texto)
        return
    if context.user_data.get("esperando_tipster"):
        if len(texto) <= 30 and len(texto) >= 2:
            todos = get_all_tipsters()
            matches = [t for t in todos if texto.lower() in t.lower()]
            if 0 < len(matches) <= 30:
                exact = [t for t in todos if t.lower() == texto.lower()]
                if exact:
                    tipster = exact[0]
                    monto = context.user_data.get("monto")
                    pick = context.user_data.get("pick")
                    if context.user_data.get("tiene_foto"): pick = f"[FOTO] {pick}"
                    nuevo = {"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
                    datos.append(nuevo); guardar(datos)
                    idx=len(datos)-1
                    context.user_data.pop("esperando_tipster", None)
                    context.user_data.pop("tiene_foto", None)
                    await update.message.reply_text(f"✅ Guardada #{idx} 👤 {tipster}", reply_markup=teclado_resultado(idx))
                    return
                else:
                    await mostrar_selector_tipsters_guardar(update.effective_chat.id, context, 0, filtro=texto)
                    return
            elif len(matches) > 30:
                await mostrar_selector_tipsters_guardar(update.effective_chat.id, context, 0, filtro=texto)
                return
            else:
                tipster = texto[:50]
                monto = context.user_data.get("monto")
                pick = context.user_data.get("pick")
                if context.user_data.get("tiene_foto"): pick = f"[FOTO] {pick}"
                nuevo = {"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
                datos.append(nuevo); guardar(datos)
                idx=len(datos)-1
                if tipster not in TIPSTERS_BASE: TIPSTERS_BASE.append(tipster)
                context.user_data.pop("esperando_tipster", None)
                context.user_data.pop("tiene_foto", None)
                await update.message.reply_text(f"✅ Nuevo tipster creado y guardada #{idx} 👤 {tipster}", reply_markup=teclado_resultado(idx))
                return
    if texto in ["📊 BALANCE","BALANCE"]:
        await balance_cmd(update, context); return
    if texto.startswith("⏳ PENDIENTES") or texto.startswith("PENDIENTES"):
        resto=texto.replace("⏳ PENDIENTES","").replace("PENDIENTES","").strip()
        filtro=resto if resto else None
        await pendientes_cmd(update, context, filtro_texto=filtro); return
    if "TIPSTERS" in texto or "LISTADO" in texto:
        await tipsters_cmd(update, context); return
    m_rapido=re.match(r"^(VERDE|ROJO|NULO|PEND)\s+(\d+)", texto.upper())
    if m_rapido:
        acc=m_rapido.group(1); idx=int(m_rapido.group(2))
        if 0 <= idx < len(datos):
            mapa={"VERDE":"VERDE","ROJO":"ROJO","NULO":"NULO","PEND":"PENDIENTE"}
            datos[idx]["resultado"]=mapa[acc]; guardar(datos)
            await update.message.reply_text(f"✅ #{idx} ahora {mapa[acc]} ({datos[idx].get('tipster','')})")
            if acc=="ROJO": await verificar_alertas(context, datos[idx].get("tipster","?"))
            return
    m=re.search(r"\d+(\.\d+)?", texto)
    es_num=bool(re.fullmatch(r"\s*\$?\s*\d+(\.\d+)?\s*", texto))
    if context.user_data.get("esperando_monto"):
        if m:
            monto=float(m.group(0))
            context.user_data["monto"]=monto
            context.user_data["esperando_monto"]=False
            context.user_data["esperando_tipster"]=True
            await mostrar_selector_tipsters_guardar(update.effective_chat.id, context, 0)
            return
        return
    if len(texto) > 3 and not es_num:
        if texto in ["📊 BALANCE","BALANCE","⏳ PENDIENTES","PENDIENTES","👥 TIPSTERS 7","TIPSTERS 7","📋 LISTADO","LISTADO","✏️ EDITAR TIPSTERS"]:
            return
        context.user_data["pick"]=texto[:500]
        context.user_data["esperando_monto"]=True
        if context.user_data.get("foto_temp"):
            context.user_data["tiene_foto"]=True
            context.user_data.pop("foto_temp", None)
            await update.message.reply_text("📌 Pick con foto OK, manda MONTO:")
        else:
            await update.message.reply_text("📌 Pick OK, manda MONTO:")
        return

async def callback(update, context):
    q=update.callback_query
    await q.answer()
    data=q.data
    datos=cargar()
    if data.startswith("addtip_"):
        if data=="addtip_new":
            context.user_data["esperando_nuevo_tipster_nombre"]=True
            await context.bot.send_message(chat_id=q.message.chat_id, text="✍️ Escribe el nombre del nuevo tipster:")
            try: await q.delete_message()
            except: pass
            return
        if data=="addtip_cancel":
            context.user_data.pop("esperando_tipster", None)
            context.user_data.pop("esperando_monto", None)
            await context.bot.send_message(chat_id=q.message.chat_id, text="❌ Cancelado")
            try: await q.delete_message()
            except: pass
            return
        tipster=data[7:]
        monto=context.user_data.get("monto")
        pick=context.user_data.get("pick")
        if context.user_data.get("tiene_foto"): pick = f"[FOTO] {pick}"
        nuevo={"fecha":datetime.now().strftime("%d/%m %H:%M"), "tipster":tipster, "monto":monto, "pick":pick, "resultado":"PENDIENTE"}
        datos.append(nuevo); guardar(datos)
        idx=len(datos)-1
        context.user_data.pop("esperando_tipster", None)
        context.user_data.pop("tiene_foto", None)
        try: await q.delete_message()
        except: pass
        await context.bot.send_message(chat_id=q.message.chat_id, text=f"✅ Guardada #{idx} 👤 {tipster}", reply_markup=teclado_resultado(idx))
        return
    if data.startswith("addpg_"):
        try:
            parts=data.split("_")
            pagina=int(parts[1])
            filtro="_".join(parts[2:]) if len(parts)>2 else ""
            filtro = filtro if filtro else None
            try: await q.delete_message()
            except: pass
            await mostrar_selector_tipsters_guardar(q.message.chat_id, context, pagina, filtro)
        except: pass
        return
    if data=="pend_menu":
        try: await q.delete_message()
        except: pass
        pend=[(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
        if not pend:
            await context.bot.send_message(chat_id=q.message.chat_id, text="✅ Sin pendientes"); return
        conteo=Counter([x[1].get("tipster","Sin tipster") for x in pend])
        txt=f"📊 Tienes {len(pend)} pendientes\n\n👇 Elige TIPSTER:"
        keyboard=[]
        for tipster, cant in conteo.most_common(50):
            keyboard.append([InlineKeyboardButton(f"{tipster[:28]} ({cant})", callback_data=f"tip_{tipster[:40]}")])
        keyboard.append([InlineKeyboardButton(f"📋 VER LAS {len(pend)} TODAS", callback_data="tip_ALL")])
        keyboard.append([InlineKeyboardButton("🔍 BUSCAR TIPSTER", callback_data="pend_search")])
        await context.bot.send_message(chat_id=q.message.chat_id, text=txt, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data=="pend_search":
        context.user_data["esperando_busqueda_pend"]=True
        await context.bot.send_message(chat_id=q.message.chat_id, text="🔍 Escribe el nombre del tipster a buscar en pendientes:")
        try: await q.delete_message()
        except: pass
        return
    if data.startswith("tip_"):
        tipster_filtro=data[4:]
        pend=[(i,x) for i,x in enumerate(datos) if x.get("resultado")=="PENDIENTE"]
        if tipster_filtro=="ALL":
            filtradas=pend; titulo="TODAS"
        else:
            filtradas=[(i,x) for i,x in pend if tipster_filtro.lower() in x.get("tipster","").lower()]
            titulo=tipster_filtro.upper()
        context.user_data["pend_filtradas"]=filtradas
        context.user_data["pend_titulo"]=titulo
        try: await q.delete_message()
        except: pass
        await mostrar_pendientes_paginadas(q.message.chat_id, context, 0)
        return
    if data.startswith("pg_"):
        try:
            pagina=int(data.split("_")[1])
            try: await q.delete_message()
            except: pass
            await mostrar_pendientes_paginadas(q.message.chat_id, context, pagina)
        except: pass
        return
    try:
        acc, idx = data.split("_")
        idx=int(idx)
        if acc=="win": datos[idx]["resultado"]="VERDE"
        elif acc=="lose": datos[idx]["resultado"]="ROJO"
        elif acc=="nulo": datos[idx]["resultado"]="NULO"
        else: datos[idx]["resultado"]="PENDIENTE"
        guardar(datos)
        tipster=datos[idx].get("tipster","?")
        await q.edit_message_text(f"✅ {datos[idx]['resultado']} #{idx} {tipster}", reply_markup=teclado_resultado(idx))
        if acc=="lose": await verificar_alertas(context, tipster)
    except Exception as e:
        print(f"Error callback: {e}")

def build_app():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pendientes", pendientes_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.CAPTION, mensaje))
    return app

def main():
    print("V28.2 223 TIPSTERS + EDITAR + FOTO FIX INICIADO", flush=True)
    try: loop=asyncio.get_event_loop()
    except: loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()
    build_app().run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()