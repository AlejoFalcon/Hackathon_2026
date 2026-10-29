"""
AI Agent & Sales Prospecting Engine for CTT FISEI UTA.
Supports Gemini API, OpenAI API, and an autonomous Expert Domain NLP Engine.
"""
import os
import re
import json
from typing import Dict, Any, Tuple, Optional
from database import get_courses, get_course_by_id, verify_certificate, increment_course_inquiries

SYSTEM_PROMPT = """
Eres el Asesor Virtual Inteligente de Ventas y Atención al Cliente del CTT-FISEI
(Centro de Transferencia y Desarrollo de Tecnologías de la Facultad de Ingeniería en Sistemas,
Electrónica e Industrial de la Universidad Técnica de Ambato - UTA, Ecuador).

Tus objetivos principales son:
1. Brindar información precisa y persuasiva sobre la oferta académica, horarios, temarios (pensum), precios y certificados con validación QR oficial.
2. Identificar el perfil del usuario (Estudiante UTA, Docente/Graduado UTA o Público General) para ofrecerle el descuento y tarifa correspondiente.
3. Guiar proactivamente al prospecto a la inscripción (cerrar ventas), transmitiendo valor académico y urgencia (cupos limitados a 20-25 personas).
4. Asistir en la verificación de certificados digitales oficiales.
5. Capturar datos de contacto (nombre, WhatsApp/teléfono, correo) de clientes altamente interesados para asegurar su cupo.
"""

def extract_phone(text: str) -> Optional[str]:
    # Match Ecuadorian phones: 09XXXXXXXX, +5939XXXXXXXX, or 10 digits
    m = re.search(r'(\+?593\s?9\d{8}|09\d{8}|\b\d{10}\b)', text)
    return m.group(1).replace(" ", "") if m else None

def extract_email(text: str) -> Optional[str]:
    m = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    return m.group(0) if m else None

def identify_user_type(text: str) -> str:
    t = text.lower()
    # Check graduate/teacher first
    if any(w in t for w in ["graduado", "docente", "profesor", "exalumno", "egresado", "alumni"]):
        return "DOCENTE_GRADUADO_UTA"
    # Check student
    if any(w in t for w in ["estudiante", "estudio", "alumno", "fisei", "pregrado", "cursando"]):
        return "ESTUDIANTE_UTA"
    if any(w in t for w in ["externo", "no soy de la uta", "publico general", "particular", "otra universidad", "independiente"]):
        return "PUBLICO_GENERAL"
    return "NO_DEFINIDO"

def match_course(text: str, courses: list) -> Optional[dict]:
    t = text.lower()
    # Direct alias matching
    alias_map = {
        "gh-600": 19, "gh600": 19, "agentic": 19, "agente": 19, "copilot": 19, "mcp": 19, "github": 19,
        "ccna": 16, "cisco": 16, "redes": 16, "switch": 16, "router": 16,
        "linux": 17, "lpi": 17, "essentials": 17,
        "python 1": 18, "python 2": 21, "fundamentos de python": 18,
        "arduino": 20, "microcontrolador": 20, "arduino desde cero": 13,
        "recursos humanos": 15, "rrhh": 15, "ia rrhh": 15,
        "protección de datos": 14, "datos personales": 14, "ley de proteccion": 14,
        "ciberseguridad": 9, "amenazas ciberneticas": 9, "ethical hacker": 6,
        "analisis de datos": 5, "ciencia de datos": 5
    }

    for alias, cid in alias_map.items():
        if alias in t:
            for c in courses:
                if c["id"] == cid:
                    return c

    # Title keyword match
    for c in courses:
        title_words = [w.lower() for w in re.findall(r'\b\w{4,}\b', c["title"]) if w.lower() not in ["preparacion", "para", "desde", "curso"]]
        matches = [w for w in title_words if w in t]
        if len(matches) >= 2:
            return c

    return None

def detect_intent(text: str) -> Tuple[str, float]:
    t = text.lower()
    
    # Check for buying / enrollment intent (Hot Lead)
    high_intent_keywords = [
        "inscrib", "matricul", "registro", "formulario", "comprar", 
        "pagar", "transferencia", "pago", "banco", "cuenta", "deposito", "apartar cupo",
        "guardar cupo", "como me inscribo", "cómo me inscribo", "quiero entrar", "link de inscripcion", "cerrar"
    ]
    if any(k in t for k in high_intent_keywords):
        return "INTENCION_COMPRA", 0.95

    # Check for certificate query
    if any(k in t for k in ["certificado", "verificar", "codigo qr", "código qr", "validez", "diploma", "aprobo", "cedula", "cédula"]):
        return "CONSULTA_CERTIFICADO", 0.40

    # Check for price query
    if any(k in t for k in ["precio", "costo", "cuanto", "cuánto", "cuesta", "valor", "tarifa", "descuento", "paga", "subsidio", "$"]):
        return "CONSULTA_PRECIO", 0.75

    # Check for schedule query
    if any(k in t for k in ["horario", "fecha", "cuando inicia", "cuándo inicia", "dias", "días", "horas", "sabados", "sábados", "viernes", "cronograma", "duracion", "duración"]):
        return "CONSULTA_HORARIO", 0.65

    # Check for syllabus / pensum query
    if any(k in t for k in ["temario", "pensum", "contenido", "que enseñan", "qué enseñan", "modulos", "módulos", "que temas", "materias"]):
        return "CONSULTA_PENSUM", 0.60

    # General course inquiry
    if any(k in t for k in ["curso", "talleres", "oferta", "capacitacion", "capacitación", "certificaciones", "aprender"]):
        return "CONSULTA_CURSO", 0.50

    # Greeting
    if any(k in t for k in ["hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "saludos", "que tal", "qué tal", "inicio"]):
        return "SALUDO_GENERAL", 0.20

    return "CONSULTA_GENERAL", 0.35

def process_expert_response(
    message: str,
    lead: dict,
    courses: list
) -> Dict[str, Any]:
    intent, base_score = detect_intent(message)
    user_type = identify_user_type(message)
    if user_type == "NO_DEFINIDO" and lead.get("user_type"):
        user_type = lead["user_type"]

    phone = extract_phone(message) or lead.get("phone")
    email = extract_email(message) or lead.get("email")
    matched_course = match_course(message, courses)
    
    # If no course matched in message, check lead's previously interested course
    if not matched_course and lead.get("interested_course_id"):
        matched_course = get_course_by_id(lead["interested_course_id"])

    # Calculate final intent score
    intent_score = max(lead.get("intent_score", 0.1), base_score)
    if phone:
        intent_score = min(1.0, intent_score + 0.15)
    if intent == "INTENCION_COMPRA":
        intent_score = max(intent_score, 0.92)

    # Determine lead status
    status = lead.get("status", "NUEVO")
    if intent_score >= 0.80:
        status = "A PUNTO DE INSCRIBIRSE"
    elif intent_score >= 0.50 and status == "NUEVO":
        status = "INTERESADO"

    sentiment = "NEUTRAL"
    if intent_score >= 0.85:
        sentiment = "URGENTE"
    elif "gracias" in message.lower() or "excelente" in message.lower() or "perfecto" in message.lower():
        sentiment = "POSITIVO"

    response_text = ""

    # Check certificate query first if certificate code or search
    if intent == "CONSULTA_CERTIFICADO":
        # Check if message contains a cert code like UTA-CTT or numbers
        cert_match = re.search(r'(UTA-CTT-[\w-]+|\b\d{4,10}\b)', message.upper())
        if cert_match:
            code_query = cert_match.group(1)
            cert = verify_certificate(code_query)
            if cert:
                response_text = (
                    f"✅ **Certificado Oficial CTT-FISEI Encontrado**\n\n"
                    f"🎓 **Estudiante:** {cert['student_name']}\n"
                    f"🆔 **Cédula:** {cert.get('student_cedula', 'Registrada')}\n"
                    f"📘 **Curso:** {cert['course_name']}\n"
                    f"⏱️ **Horas:** {cert['hours']} horas académicas\n"
                    f"📊 **Calificación:** {cert['grade']}/10.0\n"
                    f"📅 **Fecha de Emisión:** {cert['issue_date']}\n"
                    f"🛡️ **Estado:** **{cert['status']} (Aprobado y Verificado)**\n\n"
                    f"🔗 Puedes verificar el código QR oficial en el portal de la UTA: [Verificar en Línea]({cert['qr_verification_url']})\n\n"
                    f"¿Deseas inscribirte en algún curso de nuestra nueva temporada 2026?"
                )
            else:
                response_text = (
                    f"🔍 No encontramos un certificado con el código `{code_query}` en la base inmediata.\n\n"
                    f"Puedes validar directamente en el portal oficial del CTT FISEI ingresando aquí:\n"
                    f"🌐 [Portal de Verificación de Certificados](https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php)\n\n"
                    f"O indícanos tus nombres completos y número de cédula para que nuestro equipo lo revise."
                )
        else:
            response_text = (
                "🎓 **Validación de Certificados CTT - FISEI UTA**\n\n"
                "Todos nuestros certificados cuentan con **código QR único y firma electrónica institucional**.\n\n"
                "Para verificar tu certificado puedes:\n"
                "1️⃣ Escribir aquí tu **código de certificado** (ej: `UTA-CTT-2026-9041`) o tu número de **cédula**.\n"
                "2️⃣ Ingresar directamente a la plataforma educativa: [Verificar Certificado Oficial](https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php)\n\n"
                "¿Tienes a la mano tu código para consultarlo ahora mismo?"
            )

    elif intent == "INTENCION_COMPRA":
        if matched_course:
            increment_course_inquiries(matched_course["id"])
            p_uta = matched_course.get("price_uta_student", 40)
            p_staff = matched_course.get("price_uta_staff", 50)
            p_gen = matched_course.get("price_general", 60)
            reg_url = matched_course.get("registration_url", "https://docs.google.com/forms/d/e/1FAIpQLSeWhh69h-nGZYQvWkFIyR1riMYBOc61CC7YmWL49XBo64I3zA/viewform")

            price_str = f"${p_uta:.2f}" if user_type == "ESTUDIANTE_UTA" else (f"${p_staff:.2f}" if user_type == "DOCENTE_GRADUADO_UTA" else f"${p_gen:.2f}")

            response_text = (
                f"🔥 **¡Excelente decisión! Vamos a asegurar tu cupo en:**\n"
                f"📌 **{matched_course['title']}**\n\n"
                f"💰 **Tu Inversión:** **{price_str}** "
                f"({ 'Tarifa con subsidio Estudiante UTA' if user_type == 'ESTUDIANTE_UTA' else ('Tarifa Docente/Graduado UTA' if user_type == 'DOCENTE_GRADUADO_UTA' else 'Tarifa Público General') })\n\n"
                f"📋 **Pasos para Inscribirte Oficialmente:**\n"
                f"1️⃣ Llena el formulario institucional oficial: 👉 [FORMULARIO DE REGISTRO EN LÍNEA]({reg_url})\n"
                f"2️⃣ Realiza la transferencia o depósito bancario a la cuenta oficial del CTT FISEI (disponible en el formulario).\n"
                f"3️⃣ Sube tu comprobante en el formulario para activar tu acceso al aula virtual.\n\n"
                f"⚠️ *Nota:* Tenemos un cupo máximo de 25 participantes para garantizar calidad práctica. "
                f"Por favor compárteme tu **Nombre Completo** y **WhatsApp** para registrarte en la lista prioritaria del asesor."
            )
        else:
            response_text = (
                "🎯 **¡Perfecto! Estamos listos para inscribirte.**\n\n"
                "¿En cuál de nuestros cursos abiertos deseas registrarte?\n"
                "1️⃣ **GitHub Certified: Agentic AI Developer (GH-600)** - $40-$60 (Virtual Zoom)\n"
                "2️⃣ **CCNA: Introducción a las redes (Cisco)** - $120-$180 (Híbrido Campus Huachi)\n"
                "3️⃣ **Preparación Linux Essentials** - $40-$60\n"
                "4️⃣ **Fundamentos de Python 1 o 2** - $40-$60\n"
                "5️⃣ **Certificación Arduino / Automatización** - $40-$60\n\n"
                "Dime cuál prefieres y si eres estudiante/graduado de la UTA para darte el enlace directo."
            )

    elif intent == "CONSULTA_PRECIO":
        if matched_course:
            increment_course_inquiries(matched_course["id"])
            p_uta = matched_course.get("price_uta_student", 40)
            p_staff = matched_course.get("price_uta_staff", 50)
            p_gen = matched_course.get("price_general", 60)
            reg_url = matched_course.get("registration_url", "https://docs.google.com/forms/d/e/1FAIpQLSeWhh69h-nGZYQvWkFIyR1riMYBOc61CC7YmWL49XBo64I3zA/viewform")

            response_text = (
                f"🏷️ **Precios y Tarifas Oficiales para:**\n"
                f"**{matched_course['title']}**\n\n"
                f"🎓 **Estudiantes UTA (hasta último período):** **${p_uta:.2f}** *(Subsidio universitario)*\n"
                f"🏛️ **Graduados, Docentes y Personal UTA:** **${p_staff:.2f}**\n"
                f"🌐 **Público en General:** **${p_gen:.2f}**\n\n"
                f"✅ **Incluye:**\n"
                f"• {matched_course.get('hours', 32)} horas de capacitación certificada.\n"
                f"• Acceso a plataforma educativa y grabaciones.\n"
                f"• **Certificado digital con código QR oficial** del CTT-FISEI.\n\n"
                f"¿Perteneces a la comunidad UTA para aplicarte el descuento preferencial? "
                f"Si estás listo, puedes inscribirte aquí: [Registrarme ahora]({reg_url})"
            )
        else:
            response_text = (
                "🏷️ **Inversión y Tarifas Académicas CTT - FISEI**\n\n"
                "Nuestros cursos cuentan con tarifas accesibles y subsidio institucional de la Universidad Técnica de Ambato:\n\n"
                "• **Cursos de 32 a 40 horas** (IA Agéntica GH-600, Python, Linux, Arduino, IA RRHH):\n"
                "  - Estudiantes UTA: **$40,00**\n"
                "  - Graduados y Docentes UTA: **$50,00**\n"
                "  - Público General: **$60,00**\n\n"
                "• **Cursos de especialización 70 horas** (CCNA Redes Cisco):\n"
                "  - Estudiantes UTA: **$120,00**\n"
                "  - Graduados y Docentes UTA: **$150,00**\n"
                "  - Público General: **$180,00**\n\n"
                "¿Qué curso te gustaría cursar?"
            )

    elif intent == "CONSULTA_HORARIO":
        if matched_course:
            increment_course_inquiries(matched_course["id"])
            sched = matched_course.get("schedule", "Sábados de 08:00 a 14:00")
            start = matched_course.get("start_date", "Noviembre 2026")
            mod = matched_course.get("modality", "Virtual")
            hours = matched_course.get("hours", 32)
            reg_url = matched_course.get("registration_url")

            response_text = (
                f"⏰ **Cronograma y Horarios:**\n"
                f"**{matched_course['title']}**\n\n"
                f"📅 **Fechas del curso:** {start}\n"
                f"🕒 **Horario de clases:** {sched}\n"
                f"💻 **Modalidad:** **{mod}** ({'Vía Zoom con sesiones grabadas' if 'Virtual' in mod else 'Clases virtuales + prácticas presenciales en Laboratorios Campus Huachi'})\n"
                f"⏱️ **Carga Horaria:** {hours} horas académicas.\n\n"
                f"¡Los cupos son limitados! ¿Te resulta cómodo este horario para apartar tu lugar? 👉 [Inscripción Rápida]({reg_url})"
            )
        else:
            response_text = (
                "⏰ La mayoría de nuestros programas están diseñados para profesionales y estudiantes, "
                "con clases los **fines de semana** (viernes noche virtual y sábados de 08:00 a 14:00) para no interferir con tus actividades laborales o académicas.\n\n"
                "Dime cuál curso te interesa para darte las fechas exactas de inicio."
            )

    elif intent == "CONSULTA_PENSUM":
        if matched_course:
            increment_course_inquiries(matched_course["id"])
            syllabus_raw = matched_course.get("syllabus", "[]")
            syllabus = json.loads(syllabus_raw) if isinstance(syllabus_raw, str) else syllabus_raw
            
            pensum_str = ""
            for i, m in enumerate(syllabus[:5]):
                mod_name = m.get("modulo", f"Módulo {i+1}")
                topics = ", ".join(m.get("temas", []))
                pensum_str += f"🔹 **{mod_name}:** {topics[:120]}...\n" if len(topics) > 120 else f"🔹 **{mod_name}:** {topics}\n"

            if not pensum_str:
                pensum_str = f"🔹 Fundamentos teóricos y arquitectura\n🔹 Talleres prácticos y laboratorios aplicados\n🔹 Proyecto integrador final y evaluación con estándares profesionales.\n"

            response_text = (
                f"📚 **Pensum y Contenido Programático:**\n"
                f"**{matched_course['title']}**\n\n"
                f"{pensum_str}\n"
                f"🏆 **Proyecto Final:** Al finalizar desarrollarás un proyecto práctico y obtendrás el certificado con código QR.\n\n"
                f"¿Deseas conocer los precios o realizar tu inscripción?"
            )
        else:
            response_text = (
                "📚 Nuestros temarios están actualizados a los últimos estándares de la industria tecnológica.\n\n"
                "Contamos con pensums en:\n"
                "• **IA Agéntica (GH-600):** Model Context Protocol (MCP), Copilot, GitHub Actions y Multiagentes.\n"
                "• **Cisco CCNA:** Modelos OSI/TCP-IP, IPv4/IPv6, Switches, Routers y Seguridad.\n"
                "• **Python y Datos:** Programación estructurada, POO, scripts y librerías analíticas.\n\n"
                "Indícame cuál te llama la atención para enviarte el desglose completo."
            )

    elif intent == "CONSULTA_CURSO":
        if matched_course:
            increment_course_inquiries(matched_course["id"])
            p_uta = matched_course.get("price_uta_student", 40)
            p_gen = matched_course.get("price_general", 60)
            reg_url = matched_course.get("registration_url")

            response_text = (
                f"🚀 **{matched_course['title']}**\n\n"
                f"📝 **Descripción:** {matched_course.get('description', 'Capacitación tecnológica avanzada CTT-FISEI.')}\n\n"
                f"⏱️ **Duración:** {matched_course.get('hours', 32)} horas | **Modalidad:** {matched_course.get('modality', 'Virtual')}\n"
                f"🗓️ **Horario:** {matched_course.get('schedule', 'Fines de semana')}\n"
                f"💰 **Inversión:** Desde **${p_uta:.2f}** (Estudiantes UTA) hasta **${p_gen:.2f}** (Público General)\n"
                f"📜 **Certificación:** Certificado digital con QR oficial de la Universidad Técnica de Ambato.\n\n"
                f"👉 [Haz clic aquí para inscribirte]({reg_url})\n\n"
                f"¿Tienes alguna duda sobre los requisitos o las formas de pago?"
            )
        else:
            open_courses = [c for c in courses if c.get("status") == "ABIERTO"][:5]
            list_str = "\n".join([f"• **{c['title']}** ({c['hours']}h, {c['modality']})" for c in open_courses])
            response_text = (
                "🎓 **Cursos Abiertos en CTT - FISEI UTA (2026):**\n\n"
                f"{list_str}\n\n"
                "💡 Todos nuestros cursos incluyen certificación digital con QR avalada por la UTA.\n\n"
                "¿Cuál de estas áreas te gustaría potenciar hoy?"
            )

    else: # SALUDO_GENERAL / CONSULTA_GENERAL
        response_text = (
            "👋 **¡Hola! Bienvenido al Centro de Transferencia y Desarrollo de Tecnologías (CTT - FISEI UTA).**\n\n"
            "Soy tu asistente virtual con IA. Estoy aquí para ayudarte a elegir tu próximo curso, consultar temarios, horarios, precios con subsidio UTA y validar certificados oficiales.\n\n"
            "🔥 **Cursos más solicitados:**\n"
            "1️⃣ **Preparación GitHub Certified: Agentic AI Developer (GH-600)**\n"
            "2️⃣ **CCNA: Introducción a las redes Cisco (Híbrido)**\n"
            "3️⃣ **Preparación Linux Essentials**\n"
            "4️⃣ **Fundamentos de Python 1 y 2**\n"
            "5️⃣ **Certificación Arduino y Automatización**\n\n"
            "¿Sobre cuál de estos cursos te gustaría recibir más información o deseas verificar un certificado?"
        )

    return {
        "response": response_text,
        "intent": intent,
        "intent_score": intent_score,
        "status": status,
        "sentiment": sentiment,
        "user_type": user_type,
        "phone": phone,
        "email": email,
        "matched_course_id": matched_course["id"] if matched_course else lead.get("interested_course_id")
    }

async def generate_agent_response(message: str, lead: dict) -> Dict[str, Any]:
    """
    Main entry point for agent response generation.
    Uses LLM (Gemini or OpenAI) if API keys are configured,
    or our specialized domain engine.
    """
    courses = get_courses()
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    # Baseline domain-expert analysis
    result = process_expert_response(message, lead, courses)

    # If Gemini API Key is available, enhance with generative natural style while retaining our intent logic
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            course_context = "\n".join([f"- ID {c['id']}: {c['title']} (${c.get('price_uta_student', 40)} UTA / ${c.get('price_general', 60)} general, {c.get('hours')}h, {c.get('schedule')})" for c in courses[:8]])
            prompt = f"{SYSTEM_PROMPT}\n\nCursos disponibles:\n{course_context}\n\nLead actual:\n- Nombre: {lead.get('full_name')}\n- Tipo: {result['user_type']}\n- Intención previa: {result['intent']}\n\nMensaje del usuario: {message}\n\nRespuesta sugerida base:\n{result['response']}\n\nGenera una respuesta persuasiva, profesional y motivadora en formato Markdown manteniendo los enlaces y precios exactos."
            
            gen_resp = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            if gen_resp and gen_resp.text:
                result["response"] = gen_resp.text
        except Exception as e:
            print(f"Gemini generation fallback to expert engine: {e}")

    elif openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            prompt = f"{SYSTEM_PROMPT}\nMensaje del usuario: {message}\nRespuesta base: {result['response']}"
            chat_completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            ans = chat_completion.choices[0].message.content
            if ans:
                result["response"] = ans
        except Exception as e:
            print(f"OpenAI fallback to expert engine: {e}")

    return result
