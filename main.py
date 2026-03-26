import logging
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import pytz
from dotenv import load_dotenv

# ============ CONFIGURACIÓN ============
TOKEN = os.getenv('TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
ZONA_HORARIA_STR = os.getenv('ZONA_HORARIA', 'America/Bogota')
ZONA_HORARIA = pytz.timezone(ZONA_HORARIA_STR)


# Cargar variables de entorno desde .env
load_dotenv()

# Archivo para guardar la configuración
CONFIG_FILE = "bot_config.json"

# Configuración por defecto
DEFAULT_CONFIG = {
    "horarios": [2, 6, 8, 12, 25],
    "mensajes": [
        "🌅 ¡Buenos días! Espero que todos tengan un excelente día lleno de éxitos. 💪",
        "☀️ ¡Hola a todos! Recuerden que cada día es una nueva oportunidad. ¡Aprovechenla! 🌟",
        "🎉 ¡Saludos para toda la comunidad! Gracias por ser parte de este espacio. 🙌",
        "💫 ¡Hola! Les deseamos un día maravilloso lleno de bendiciones. ✨",
        "🌟 ¡Buen día! Que hoy sea un día productivo y lleno de alegría. 😊"
    ],
    "link": None,  # Link que se mostrará en los mensajes
    "link_text": "🔗 Visítanos aquí",  # Texto del link
    "mostrar_hora": False,  # Mostrar u ocultar la hora
    "activo": True  # Bot activo o no
}

# Cargar configuración
def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Asegurar que todas las claves existan
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    return DEFAULT_CONFIG.copy()

def guardar_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# Cargar configuración inicial
config = cargar_config()

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estadísticas
estadisticas = {
    'total_saludos': 0,
    'ultimo_saludo': None
}

# Estados para configuración
USER_STATES = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Menú principal"""
    keyboard = [
        [InlineKeyboardButton("📊 Ver estado", callback_data="status")],
        [InlineKeyboardButton("⚙️ Configuración", callback_data="config_menu")],
        [InlineKeyboardButton("📝 Ver mensajes", callback_data="ver_mensajes")],
        [InlineKeyboardButton("🔗 Ver link", callback_data="ver_link")],
        [InlineKeyboardButton("⏰ Próximo saludo", callback_data="proximo")],
        [InlineKeyboardButton("📢 Enviar saludo ahora", callback_data="enviar_ahora")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Bot de Saludos Configurable* 🤖\n\n"
        "Puedes personalizar los saludos, horarios y enlaces.\n\n"
        f"📅 *Horarios:* {', '.join(map(str, config['horarios']))} horas\n"
        f"🔗 *Link configurado:* {'✅ Sí' if config['link'] else '❌ No'}\n"
        f"⏰ *Mostrar hora:* {'✅ Sí' if config['mostrar_hora'] else '❌ No'}\n"
        f"🎯 *Estado:* {'🟢 Activo' if config['activo'] else '🔴 Inactivo'}\n\n"
        "Usa los botones para configurar:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los botones del menú"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "status":
        await mostrar_status(query)
    elif data == "config_menu":
        await mostrar_menu_config(query)
    elif data == "ver_mensajes":
        await ver_mensajes(query)
    elif data == "ver_link":
        await ver_link(query)
    elif data == "proximo":
        await mostrar_proximo(query)
    elif data == "enviar_ahora":
        await enviar_saludo_manual(query, context)
    elif data == "config_horarios":
        await configurar_horarios(query)
    elif data == "config_mensajes":
        await configurar_mensajes(query)
    elif data == "config_link":
        await configurar_link(query)
    elif data == "toggle_hora":
        await toggle_mostrar_hora(query)
    elif data == "toggle_activo":
        await toggle_activo(query)
    elif data == "agregar_mensaje":
        await solicitar_mensaje(query)
    elif data == "eliminar_mensajes":
        await eliminar_mensajes(query)
    elif data == "back":
        await start_callback(query)
    elif data == "reset_config":
        await reset_config(query)

async def mostrar_status(query):
    """Muestra el estado actual del bot"""
    status_text = (
        "📊 *Estado del Bot* 📊\n\n"
        f"🎯 *Estado:* {'🟢 Activo' if config['activo'] else '🔴 Inactivo'}\n"
        f"📅 *Horarios:* {', '.join(map(str, config['horarios']))} horas\n"
        f"📝 *Mensajes configurados:* {len(config['mensajes'])}\n"
        f"🔗 *Link:* {'✅ Configurado' if config['link'] else '❌ No configurado'}\n"
        f"⏰ *Mostrar hora:* {'✅ Sí' if config['mostrar_hora'] else '❌ No'}\n"
        f"💬 *Total saludos enviados:* {estadisticas['total_saludos']}\n"
        f"⏱️ *Último saludo:* {estadisticas['ultimo_saludo'] or 'Ninguno'}\n\n"
        f"📌 *Canal:* {CHANNEL_ID}"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Volver", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        status_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def mostrar_menu_config(query):
    """Muestra el menú de configuración"""
    keyboard = [
        [InlineKeyboardButton("⏰ Configurar horarios", callback_data="config_horarios")],
        [InlineKeyboardButton("📝 Configurar mensajes", callback_data="config_mensajes")],
        [InlineKeyboardButton("🔗 Configurar link", callback_data="config_link")],
        [InlineKeyboardButton(f"⏱️ Mostrar hora: {'✅' if config['mostrar_hora'] else '❌'}", callback_data="toggle_hora")],
        [InlineKeyboardButton(f"🎯 Activar/Desactivar: {'🟢' if config['activo'] else '🔴'}", callback_data="toggle_activo")],
        [InlineKeyboardButton("🔄 Resetear configuración", callback_data="reset_config")],
        [InlineKeyboardButton("◀️ Volver", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ *Configuración del Bot* ⚙️\n\n"
        "Selecciona qué quieres configurar:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def ver_mensajes(query):
    """Muestra los mensajes configurados"""
    if not config['mensajes']:
        texto = "📝 *No hay mensajes configurados*\n\nUsa la configuración para agregar mensajes."
    else:
        texto = "📝 *Mensajes configurados:*\n\n"
        for i, msg in enumerate(config['mensajes'], 1):
            texto += f"{i}. {msg[:100]}...\n\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Agregar mensaje", callback_data="agregar_mensaje")],
        [InlineKeyboardButton("🗑️ Eliminar mensajes", callback_data="eliminar_mensajes")],
        [InlineKeyboardButton("◀️ Volver", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        texto,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def ver_link(query):
    """Muestra el link configurado"""
    if config['link']:
        texto = f"🔗 *Link configurado:*\n\n{config['link_text']}: {config['link']}"
    else:
        texto = "🔗 *No hay link configurado*\n\nUsa la configuración para agregar un link."
    
    keyboard = [[InlineKeyboardButton("◀️ Volver", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        texto,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def mostrar_proximo(query):
    """Muestra el próximo horario de saludo"""
    proximo = await calcular_proximo_saludo()
    texto = f"⏰ *Próximo saludo programado:*\n\n{proximo}\n\n📅 *Horarios:* {', '.join(map(str, config['horarios']))} horas"
    
    keyboard = [[InlineKeyboardButton("◀️ Volver", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        texto,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def configurar_horarios(query):
    """Inicia la configuración de horarios"""
    USER_STATES[query.from_user.id] = "esperando_horarios"
    
    keyboard = [[InlineKeyboardButton("◀️ Cancelar", callback_data="config_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⏰ *Configurar Horarios*\n\n"
        f"Horarios actuales: {', '.join(map(str, config['horarios']))}\n\n"
        "Envía los nuevos horarios separados por espacios.\n"
        "Ejemplo: `2 6 8 12 25`\n\n"
        "*Nota:* Los números representan horas (0-23) y 25 representa 1 AM",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def configurar_mensajes(query):
    """Muestra opciones para configurar mensajes"""
    keyboard = [
        [InlineKeyboardButton("➕ Agregar mensaje", callback_data="agregar_mensaje")],
        [InlineKeyboardButton("🗑️ Eliminar mensajes", callback_data="eliminar_mensajes")],
        [InlineKeyboardButton("◀️ Volver", callback_data="config_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 *Configurar Mensajes*\n\n"
        f"Total de mensajes: {len(config['mensajes'])}\n\n"
        "Selecciona una opción:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def configurar_link(query):
    """Inicia la configuración del link"""
    USER_STATES[query.from_user.id] = "esperando_link"
    
    keyboard = [[InlineKeyboardButton("◀️ Cancelar", callback_data="config_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔗 *Configurar Link*\n\n"
        f"Link actual: {config['link'] or 'No configurado'}\n\n"
        "Envía el link en el siguiente formato:\n"
        "`URL|Texto del link`\n\n"
        "Ejemplo:\n"
        "`https://t.me/mi_canal|📢 Visita nuestro canal`\n\n"
        "O solo la URL para usar el texto por defecto.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def toggle_mostrar_hora(query):
    """Activa/desactiva mostrar la hora"""
    config['mostrar_hora'] = not config['mostrar_hora']
    guardar_config(config)
    
    await query.answer(f"Mostrar hora: {'Activado' if config['mostrar_hora'] else 'Desactivado'}")
    await mostrar_menu_config(query)

async def toggle_activo(query):
    """Activa/desactiva el bot"""
    config['activo'] = not config['activo']
    guardar_config(config)
    
    estado = "activado" if config['activo'] else "desactivado"
    await query.answer(f"Bot {estado}")
    await mostrar_menu_config(query)

async def solicitar_mensaje(query):
    """Solicita un nuevo mensaje"""
    USER_STATES[query.from_user.id] = "esperando_mensaje"
    
    keyboard = [[InlineKeyboardButton("◀️ Cancelar", callback_data="config_mensajes")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 *Agregar nuevo mensaje*\n\n"
        "Envía el mensaje que quieres agregar.\n"
        "Puede incluir emojis y formato.\n\n"
        "Ejemplo: `🌟 ¡Hola comunidad! ¡Qué tengan un excelente día! 🌟`",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def eliminar_mensajes(query):
    """Permite eliminar mensajes"""
    if not config['mensajes']:
        await query.answer("No hay mensajes para eliminar")
        await ver_mensajes(query)
        return
    
    keyboard = []
    for i, msg in enumerate(config['mensajes'], 1):
        keyboard.append([InlineKeyboardButton(f"🗑️ {i}. {msg[:30]}...", callback_data=f"del_msg_{i-1}")])
    keyboard.append([InlineKeyboardButton("◀️ Volver", callback_data="ver_mensajes")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑️ *Selecciona el mensaje a eliminar:*",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def reset_config(query):
    """Resetea la configuración a valores por defecto"""
    global config
    config = DEFAULT_CONFIG.copy()
    guardar_config(config)
    
    await query.answer("Configuración reseteada a valores por defecto")
    await mostrar_menu_config(query)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes de texto para configuración"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in USER_STATES:
        return
    
    state = USER_STATES[user_id]
    
    if state == "esperando_horarios":
        try:
            # Procesar horarios
            horarios = [int(x.strip()) for x in text.split()]
            # Validar horarios
            horarios_validos = []
            for h in horarios:
                if 0 <= h <= 23 or h == 25:
                    horarios_validos.append(h)
                else:
                    await update.message.reply_text(f"⚠️ Hora {h} inválida. Ignorada.")
            
            if horarios_validos:
                config['horarios'] = sorted(set(horarios_validos))  # Eliminar duplicados
                guardar_config(config)
                await update.message.reply_text(f"✅ Horarios actualizados: {', '.join(map(str, config['horarios']))}")
            else:
                await update.message.reply_text("❌ No se recibieron horarios válidos")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}\nFormato inválido. Usa números separados por espacios.")
        
        del USER_STATES[user_id]
        
    elif state == "esperando_mensaje":
        # Agregar nuevo mensaje
        config['mensajes'].append(text)
        guardar_config(config)
        await update.message.reply_text(f"✅ Mensaje agregado correctamente.\nTotal: {len(config['mensajes'])} mensajes")
        del USER_STATES[user_id]
        
    elif state == "esperando_link":
        try:
            if '|' in text:
                url, texto_link = text.split('|', 1)
                config['link'] = url.strip()
                config['link_text'] = texto_link.strip()
            else:
                config['link'] = text.strip()
                config['link_text'] = DEFAULT_CONFIG['link_text']
            
            guardar_config(config)
            await update.message.reply_text(f"✅ Link configurado:\n{config['link_text']}: {config['link']}")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}\nFormato inválido.")
        
        del USER_STATES[user_id]

async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la eliminación de mensajes"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("del_msg_"):
        index = int(query.data.split("_")[2])
        if 0 <= index < len(config['mensajes']):
            eliminado = config['mensajes'].pop(index)
            guardar_config(config)
            await query.answer(f"Mensaje eliminado: {eliminado[:50]}...")
            await ver_mensajes(query)

async def enviar_saludo(context: ContextTypes.DEFAULT_TYPE):
    """Envía un saludo al canal"""
    if not config['activo']:
        logger.info("Bot inactivo, no se envía saludo")
        return
    
    try:
        # Seleccionar mensaje aleatorio
        mensaje = random.choice(config['mensajes']) if config['mensajes'] else "¡Saludos a todos! 👋"
        
        # Construir mensaje final
        ahora = datetime.now(ZONA_HORARIA)
        
        # Determinar saludo según hora
        hora = ahora.hour
        if 5 <= hora < 12:
            saludo = "🌅 ¡Buenos días!"
        elif 12 <= hora < 18:
            saludo = "☀️ ¡Buenas tardes!"
        elif 18 <= hora < 24:
            saludo = "🌙 ¡Buenas noches!"
        else:
            saludo = "🌃 ¡Hola!"
        
        mensaje_final = f"{saludo}\n\n{mensaje}\n\n"
        
        # Agregar hora si está configurado
        if config['mostrar_hora']:
            mensaje_final += f"⏰ {ahora.strftime('%H:%M')}\n"
        
        # Agregar link si está configurado
        if config['link']:
            mensaje_final += f"\n{config['link_text']}: {config['link']}"
        
        # Enviar mensaje
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=mensaje_final
        )
        
        # Actualizar estadísticas
        estadisticas['total_saludos'] += 1
        estadisticas['ultimo_saludo'] = ahora.strftime("%H:%M del %d/%m/%Y")
        
        logger.info(f"✅ Saludo enviado a las {ahora.strftime('%H:%M')}")
        
    except Exception as e:
        logger.error(f"❌ Error al enviar saludo: {e}")

async def enviar_saludo_manual(query, context):
    """Envía un saludo manualmente"""
    if not config['activo']:
        await query.answer("El bot está desactivado. Actívalo en configuración.")
        return
    
    await query.answer("Enviando saludo...")
    await enviar_saludo(context)
    await query.edit_message_text("✅ Saludo enviado correctamente")
    await asyncio.sleep(2)
    await start_callback(query)

async def calcular_proximo_saludo():
    """Calcula el próximo horario de saludo"""
    ahora = datetime.now(ZONA_HORARIA)
    hora_actual = ahora.hour
    
    for hora in sorted(config['horarios']):
        if hora > hora_actual:
            proximo = ahora.replace(hour=hora, minute=0, second=0, microsecond=0)
            return proximo.strftime("%H:%M horas del %d/%m/%Y")
    
    primer_horario = min(config['horarios']) if config['horarios'] else 8
    manana = ahora + timedelta(days=1)
    proximo = manana.replace(hour=primer_horario, minute=0, second=0, microsecond=0)
    return proximo.strftime("%H:%M horas del %d/%m/%Y")

async def start_callback(query):
    """Callback para volver al menú principal"""
    keyboard = [
        [InlineKeyboardButton("📊 Ver estado", callback_data="status")],
        [InlineKeyboardButton("⚙️ Configuración", callback_data="config_menu")],
        [InlineKeyboardButton("📝 Ver mensajes", callback_data="ver_mensajes")],
        [InlineKeyboardButton("🔗 Ver link", callback_data="ver_link")],
        [InlineKeyboardButton("⏰ Próximo saludo", callback_data="proximo")],
        [InlineKeyboardButton("📢 Enviar saludo ahora", callback_data="enviar_ahora")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🤖 *Bot de Saludos Configurable* 🤖\n\n"
        f"📅 *Horarios:* {', '.join(map(str, config['horarios']))} horas\n"
        f"🔗 *Link configurado:* {'✅ Sí' if config['link'] else '❌ No'}\n"
        f"⏰ *Mostrar hora:* {'✅ Sí' if config['mostrar_hora'] else '❌ No'}\n"
        f"🎯 *Estado:* {'🟢 Activo' if config['activo'] else '🔴 Inactivo'}\n\n"
        "Selecciona una opción:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def programar_saludos(context: ContextTypes.DEFAULT_TYPE):
    """Programa los saludos en los horarios establecidos"""
    if not config['activo']:
        return
    
    try:
        ahora = datetime.now(ZONA_HORARIA)
        hora_actual = ahora.hour
        minuto_actual = ahora.minute
        
        if minuto_actual <= 1 and hora_actual in config['horarios']:
            clave = f"saludo_{ahora.strftime('%Y%m%d_%H')}"
            if context.job_queue:
                jobs = context.job_queue.jobs()
                ya_enviado = any(job.name == clave for job in jobs if hasattr(job, 'name'))
                
                if not ya_enviado:
                    context.job_queue.run_once(
                        enviar_saludo,
                        1,
                        name=clave
                    )
                    logger.info(f"📅 Saludo programado para las {hora_actual}:00")
                    
    except Exception as e:
        logger.error(f"Error en programar_saludos: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores globales"""
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ Ocurrió un error. Por favor intenta más tarde.")

def main():
    """Función principal"""
    print("🤖 Iniciando Bot de Saludos Configurable...")
    print(f"📅 Horarios: {', '.join(map(str, config['horarios']))}")
    print(f"📝 Mensajes: {len(config['mensajes'])}")
    print(f"🔗 Link: {'✅' if config['link'] else '❌'}")
    print(f"🎯 Estado: {'Activo' if config['activo'] else 'Inactivo'}")
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler, pattern="^(?!del_msg_).*"))
        application.add_handler(CallbackQueryHandler(handle_delete_callback, pattern="^del_msg_"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_error_handler(error_handler)
        
        # Programar saludos
        if application.job_queue:
            application.job_queue.run_repeating(
                programar_saludos,
                interval=60,
                first=10
            )
            print("✅ Programador de saludos activado")
        
        print("✅ Bot iniciado correctamente")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()