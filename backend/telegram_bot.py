"""
Telegram Bot Service for CTT FISEI UTA.
Powered by python-telegram-bot (v20+ async) and integrated with the AI Agent engine.
"""
import os
import asyncio
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from database import (
    get_or_create_lead,
    update_lead,
    log_message,
    get_system_config,
    get_courses,
    get_course_by_id,
    verify_certificate
)
from llm_agent import generate_agent_response

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

bot_app: Optional[Application] = None
bot_task: Optional[asyncio.Task] = None

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🤖 IA Agéntica (GH-600)", callback_data="course_19"),
            InlineKeyboardButton("🌐 Cisco CCNA Redes", callback_data="course_16")
        ],
        [
            InlineKeyboardButton("📚 Ver Todos los Cursos", callback_data="all_courses"),
            InlineKeyboardButton("🏷️ Precios y Subsidio UTA", callback_data="pricing_info")
        ],
        [
            InlineKeyboardButton("🎓 Validar Certificado QR", callback_data="check_cert"),
            InlineKeyboardButton("✍️ Inscribirme Ahora", callback_data="register_hot")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = str(user.id)
    username = user.username or ""
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or username

    lead = get_or_create_lead(chat_id, username=username, full_name=full_name)
    welcome_text = (
        f"🏛️ **¡Bienvenido a CTT - FISEI UTA, {user.first_name}!**\n\n"
        f"Soy tu **Asesor de Admisiones e Inteligencia Artificial** del Centro de Capacitación Tecnológica de la Facultad de Ingeniería en Sistemas, Electrónica e Industrial.\n\n"
        f"Estamos aquí para potenciar tus competencias profesionales con certificaciones avaladas oficialmente por la **Universidad Técnica de Ambato**.\n\n"
        f"💡 Puedes preguntarme lo que desees sobre:\n"
        f"• **Horarios y fechas** de inicio\n"
        f"• **Precios con descuento** para estudiantes y graduados UTA\n"
        f"• **Pensum y temarios** detallados\n"
        f"• **Validación oficial** de certificados digitales con QR\n\n"
        f"¿Por dónde te gustaría empezar?"
    )
    
    log_message(lead["id"], "user", "/start", "SALUDO_INICIAL")
    log_message(lead["id"], "bot", welcome_text, "BIENVENIDA")
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💡 **Comandos y Funciones del Asesor CTT-FISEI:**\n\n"
        "• `/start` - Menú principal y cursos destacados\n"
        "• `/cursos` - Listado de cursos tecnológicos abiertos\n"
        "• `/precios` - Tarifas y subsidios para la comunidad UTA\n"
        "• `/certificado <código>` - Validar certificado institucional\n"
        "• `/inscribirme` - Formulario oficial de matrícula\n\n"
        "O simplemente escribe tu consulta como si hablaras con un asesor humano."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def cursos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    courses = get_courses(status="ABIERTO")
    lines = ["🎓 **Cursos Abiertos Temporada 2026 - CTT FISEI:**\n"]
    keyboard = []
    
    for c in courses[:6]:
        p_uta = c.get("price_uta_student", 40)
        p_gen = c.get("price_general", 60)
        lines.append(f"• **{c['title']}**\n  ⏱️ {c['hours']}h | 💻 {c['modality']} | 💰 ${p_uta:.2f} (UTA) / ${p_gen:.2f}\n")
        keyboard.append([InlineKeyboardButton(f"ℹ️ {c['title'][:32]}...", callback_data=f"course_{c['id']}")])
    
    lines.append("\nToca cualquier curso para ver el temario, horarios y apartar tu cupo.")
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")])
    
    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def certificado_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    lead = get_or_create_lead(str(user.id), username=user.username or "", full_name=user.first_name or "")
    
    if not args:
        msg = (
            "🔍 **Validación de Certificados Oficiales CTT-FISEI**\n\n"
            "Por favor escribe el comando seguido de tu código de certificado o cédula, ejemplo:\n"
            "`/certificado UTA-CTT-2026-9041`\n\n"
            "O valida directamente en el portal web: [Portal de Validación UTA](https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php)"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    query_str = " ".join(args)
    cert = verify_certificate(query_str)
    if cert:
        reply = (
            f"✅ **Certificado Verificado con Éxito**\n\n"
            f"👤 **Estudiante:** {cert['student_name']}\n"
            f"🆔 **Cédula:** {cert.get('student_cedula', 'Registrada')}\n"
            f"🎓 **Curso:** {cert['course_name']}\n"
            f"⏱️ **Carga Horaria:** {cert['hours']} Horas Académicas\n"
            f"📅 **Fecha:** {cert['issue_date']}\n"
            f"🌟 **Calificación:** {cert['grade']}/10.0\n"
            f"🛡️ **Estado:** **{cert['status']} (Auténtico con QR)**\n\n"
            f"🔗 [Enlace de Verificación Institucional]({cert['qr_verification_url']})"
        )
    else:
        reply = (
            f"⚠️ No se encontró registro con el código `{query_str}` en el sistema inmediato.\n\n"
            f"Verifica que el código esté bien escrito o consulta directamente en:\n"
            f"https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php"
        )
    
    log_message(lead["id"], "user", f"/certificado {query_str}", "CONSULTA_CERTIFICADO")
    log_message(lead["id"], "bot", reply, "RESPUESTA_CERTIFICADO")
    await update.message.reply_text(reply, parse_mode="Markdown")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    lead = get_or_create_lead(str(user.id), username=user.username or "", full_name=user.first_name or "")

    if data == "main_menu":
        await query.edit_message_text(
            "🏛️ **Centro de Capacitación Tecnológica CTT - FISEI UTA**\n\n¿En qué te puedo asesorar hoy?",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    elif data.startswith("course_"):
        cid = int(data.split("_")[1])
        c = get_course_by_id(cid)
        if c:
            update_lead(lead["id"], interested_course_id=cid, status="INTERESADO")
            reg_url = c.get("registration_url", "https://docs.google.com/forms/d/e/1FAIpQLSeWhh69h-nGZYQvWkFIyR1riMYBOc61CC7YmWL49XBo64I3zA/viewform")
            kb = [
                [InlineKeyboardButton("✍️ Inscribirme en este Curso", url=reg_url)],
                [
                    InlineKeyboardButton("⏰ Ver Horarios", callback_data=f"sched_{cid}"),
                    InlineKeyboardButton("📚 Ver Temario", callback_data=f"pensum_{cid}")
                ],
                [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
            ]
            text = (
                f"🚀 **{c['title']}**\n\n"
                f"📝 **Descripción:** {c.get('description', '')}\n\n"
                f"⏱️ **Duración:** {c.get('hours', 32)} horas | **Modalidad:** {c.get('modality', 'Virtual')}\n"
                f"📅 **Inicio:** {c.get('start_date', 'Próximamente')}\n"
                f"💰 **Inversión:**\n"
                f"  • Estudiantes UTA: **${c.get('price_uta_student', 40):.2f}**\n"
                f"  • Graduados/Docentes: **${c.get('price_uta_staff', 50):.2f}**\n"
                f"  • Público General: **${c.get('price_general', 60):.2f}**\n\n"
                f"📜 Incluye Certificado digital con QR oficial."
            )
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "pricing_info":
        kb = [
            [InlineKeyboardButton("🤖 IA Agéntica ($40-$60)", callback_data="course_19")],
            [InlineKeyboardButton("🌐 Redes CCNA ($120-$180)", callback_data="course_16")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        text = (
            "🏷️ **Estructura de Precios y Subsidios Universitarios CTT-FISEI:**\n\n"
            "La Universidad Técnica de Ambato subsidia la capacitación tecnológica:\n\n"
            "• **Cursos Estándar (32 a 40 Horas):**\n"
            "  - Estudiantes UTA: **$40,00**\n"
            "  - Graduados / Docentes UTA: **$50,00**\n"
            "  - Público General: **$60,00**\n\n"
            "• **Curso Avanzado Redes Cisco CCNA (70 Horas Híbrido):**\n"
            "  - Estudiantes UTA: **$120,00**\n"
            "  - Graduados / Docentes UTA: **$150,00**\n"
            "  - Público General: **$180,00**\n\n"
            "💡 Todos incluyen acceso a plataforma, laboratorios y certificado QR."
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "register_hot":
        update_lead(lead["id"], intent_score=0.95, status="A PUNTO DE INSCRIBIRSE", closure_probability="ALTA")
        kb = [
            [InlineKeyboardButton("📝 Abrir Formulario Oficial de Registro", url="https://docs.google.com/forms/d/e/1FAIpQLSeWhh69h-nGZYQvWkFIyR1riMYBOc61CC7YmWL49XBo64I3zA/viewform")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        text = (
            "🔥 **¡Asegura tu cupo prioritario ahora!**\n\n"
            "Para inscribirte oficialmente y reservar uno de los 25 cupos:\n"
            "1️⃣ Ingresa al formulario institucional abajo.\n"
            "2️⃣ Realiza el pago/transferencia a la cuenta de la UTA detallada en el formulario.\n"
            "3️⃣ Envía tu comprobante.\n\n"
            "💡 También puedes responder a este chat con tu **Nombre Completo** y **WhatsApp** para que el coordinador de admisiones te asista de inmediato."
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "all_courses":
        await cursos_command(update, context)

    elif data == "check_cert":
        text = (
            "🎓 **Verificación de Certificado CTT-FISEI**\n\n"
            "Envía un mensaje con el código de tu certificado (ej: `UTA-CTT-2026-9041`) o tu número de cédula, "
            "o pulsa abajo para abrir el portal web de la UTA."
        )
        kb = [
            [InlineKeyboardButton("🌐 Abrir Portal de Validación UTA", url="https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = str(user.id)
    text = update.message.text or ""
    username = user.username or ""
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or username

    lead = get_or_create_lead(chat_id, username=username, full_name=full_name)

    # Process through AI Agent
    result = await generate_agent_response(text, lead)

    # Update lead info in database
    update_data = {
        "intent_score": result["intent_score"],
        "status": result["status"],
        "sentiment": result["sentiment"]
    }
    if result.get("user_type") and result["user_type"] != "NO_DEFINIDO":
        update_data["user_type"] = result["user_type"]
    if result.get("phone"):
        update_data["phone"] = result["phone"]
    if result.get("email"):
        update_data["email"] = result["email"]
    if result.get("matched_course_id"):
        update_data["interested_course_id"] = result["matched_course_id"]
    if result["intent_score"] >= 0.8:
        update_data["closure_probability"] = "ALTA"
    elif result["intent_score"] >= 0.5:
        update_data["closure_probability"] = "MEDIA"

    update_lead(lead["id"], **update_data)

    # Log messages
    log_message(lead["id"], "user", text, result["intent"])
    log_message(lead["id"], "bot", result["response"], f"RESPUESTA_{result['intent']}")

    # Build action keyboard if high intent or course inquiry
    kb = []
    if result["intent"] == "INTENCION_COMPRA" or result["intent_score"] >= 0.8:
        kb.append([InlineKeyboardButton("✍️ Registrarme en el Formulario", url="https://docs.google.com/forms/d/e/1FAIpQLSeWhh69h-nGZYQvWkFIyR1riMYBOc61CC7YmWL49XBo64I3zA/viewform")])
    elif result.get("matched_course_id"):
        cid = result["matched_course_id"]
        c = get_course_by_id(cid)
        if c:
            kb.append([InlineKeyboardButton(f"✍️ Inscribirme en {c['code']}", url=c.get("registration_url"))])
    
    kb.append([InlineKeyboardButton("💬 Menú de Opciones", callback_data="main_menu")])

    await update.message.reply_text(
        result["response"],
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

def create_telegram_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cursos", cursos_command))
    app.add_handler(CommandHandler("certificado", certificado_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    return app

async def start_telegram_bot(token: Optional[str] = None):
    global bot_app
    bot_token = token or os.getenv("TELEGRAM_BOT_TOKEN") or get_system_config("TELEGRAM_BOT_TOKEN")
    if not bot_token or bot_token.strip() == "":
        logger.info("No Telegram Bot token configured yet. Telegram bot polling inactive.")
        return False

    try:
        logger.info("Initializing Telegram bot with configured token...")
        bot_app = create_telegram_application(bot_token)
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        logger.info("Telegram Bot started and polling for messages!")
        return True
    except Exception as e:
        logger.error(f"Failed to start Telegram Bot: {e}")
        return False

async def stop_telegram_bot():
    global bot_app
    if bot_app:
        try:
            logger.info("Stopping Telegram Bot...")
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
            bot_app = None
            logger.info("Telegram Bot stopped successfully.")
        except Exception as e:
            logger.error(f"Error stopping Telegram Bot: {e}")
