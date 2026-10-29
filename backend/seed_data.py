"""
Seed script to populate CTT FISEI courses, certificates, sample leads, and conversation history.
"""
import json
import os
import re
from datetime import datetime, timedelta
from database import get_db, init_db

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "courses_catalog.json")

def categorize_course(title: str) -> str:
    t = title.upper()
    if "AI" in t or "INTELIGENCIA ARTIFICIAL" in t or "AGENTIC" in t or "DATOS" in t:
        return "Inteligencia Artificial"
    elif "CCNA" in t or "REDES" in t:
        return "Redes y Telecomunicaciones"
    elif "PYTHON" in t or "JAVASCRIPT" in t or "NODE" in t:
        return "Programación y Software"
    elif "ARDUINO" in t or "PLC" in t or "CONTROL INDUSTRIAL" in t:
        return "Electrónica y Automatización"
    elif "CIBERSEGURIDAD" in t or "DEFENSA" in t or "HACKER" in t or "AMENAZAS" in t:
        return "Ciberseguridad"
    elif "PROTECCIÓN DE DATOS" in t or "LEY" in t:
        return "Legislación y Gestión TI"
    return "Tecnología General"

def parse_prices(details: dict):
    # Defaults
    price_uta = 40.0
    price_staff = 50.0
    price_general = 60.0
    
    precios_arr = details.get("Precios_Detalle", [])
    for p in precios_arr:
        # e.g. "Estudiantes UTA (hasta último período): $120,00"
        m = re.search(r'\$(\d+[\.,]?\d*)', p)
        if m:
            val = float(m.group(1).replace(',', '.'))
            p_lower = p.lower()
            if "estudiante" in p_lower:
                price_uta = val
            elif "graduado" in p_lower or "docente" in p_lower:
                price_staff = val
            elif "general" in p_lower or "público" in p_lower:
                price_general = val
    return price_uta, price_staff, price_general

def seed_courses():
    if not os.path.exists(CATALOG_PATH):
        print("Catalog not found, skipping course seed.")
        return

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    conn = get_db()
    cursor = conn.cursor()

    for item in catalog:
        cid = item["id"]
        code = item.get("code", f"CTT-FISEI-{cid:02d}")
        title = item["title"]
        desc = item.get("description", "")
        category = categorize_course(title)
        details = item.get("details", {})
        
        hours_str = details.get("Horas de capacitación", "32")
        hours_m = re.search(r'(\d+)', hours_str)
        hours = int(hours_m.group(1)) if hours_m else 32
        
        modality = details.get("Modalidad", "Virtual")
        schedule = details.get("Horario", "Sábados de 08:00 a 14:00")
        start_date = details.get("Fecha del curso", "Noviembre 2026")
        reg_deadline = details.get("Fechas de inscripciones", "Hasta 13 de Noviembre 2026")
        
        p_uta, p_staff, p_gen = parse_prices(details)
        instructors = json.dumps(item.get("instructors", ["Ingenieros CTT-FISEI"]), ensure_ascii=False)
        syllabus = json.dumps(item.get("syllabus", []), ensure_ascii=False)
        materials = json.dumps(item.get("materials", []), ensure_ascii=False)
        reg_url = item.get("registration_url", "https://ctt-talleresfisei.uta.edu.ec/contact.php")
        status = item.get("status", "ABIERTO")

        cursor.execute("""
        INSERT INTO courses (
            id, code, title, description, category, hours, modality, schedule, 
            start_date, end_date, registration_deadline, price_uta_student, 
            price_uta_staff, price_general, instructors, syllabus, materials, 
            registration_url, status, inquiries_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            category = excluded.category,
            hours = excluded.hours,
            modality = excluded.modality,
            schedule = excluded.schedule,
            start_date = excluded.start_date,
            registration_deadline = excluded.registration_deadline,
            price_uta_student = excluded.price_uta_student,
            price_uta_staff = excluded.price_uta_staff,
            price_general = excluded.price_general,
            instructors = excluded.instructors,
            syllabus = excluded.syllabus,
            materials = excluded.materials,
            registration_url = excluded.registration_url,
            status = excluded.status
        """, (
            cid, code, title, desc, category, hours, modality, schedule, 
            start_date, reg_deadline, p_uta, p_staff, p_gen, 
            instructors, syllabus, materials, reg_url, status
        ))
    
    conn.commit()
    conn.close()
    print(f"Seeded {len(catalog)} courses.")

def seed_certificates():
    conn = get_db()
    cursor = conn.cursor()
    sample_certs = [
        ("UTA-CTT-2026-9041", "Carlos Andrés Morales Ortiz", "1804567890", "Preparación GitHub Certified: Agentic AI Developer (GH-600)", "2026-10-15", 32, 9.6, "https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php?code=9041"),
        ("UTA-CTT-2026-8821", "María Belén Salazar Ramos", "1803241598", "CCNA: Introducción a las redes – Preparación Cisco", "2026-09-28", 70, 9.8, "https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php?code=8821"),
        ("UTA-CTT-2026-7734", "David Fernando Pérez Jácome", "0502987412", "Fundamentos de Python 1", "2026-08-10", 32, 9.2, "https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php?code=7734"),
        ("UTA-CTT-2026-6512", "Jessica Paulina Castro Vaca", "1809988776", "Inteligencia Artificial para la Gestión de Recursos Humanos", "2026-07-22", 32, 10.0, "https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php?code=6512"),
        ("UTA-CTT-2026-5419", "Erick Mateo Villacís Guevara", "1801122334", "La Ley de Protección de Datos en el Ecuador", "2026-06-30", 32, 9.4, "https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php?code=5419")
    ]
    for c in sample_certs:
        cursor.execute("""
        INSERT INTO certificates (cert_code, student_name, student_cedula, course_name, issue_date, hours, grade, qr_verification_url, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'VALIDO')
        ON CONFLICT(cert_code) DO NOTHING
        """, c)
    conn.commit()
    conn.close()
    print("Seeded sample certificates.")

def seed_sample_leads():
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if leads already exist
    cursor.execute("SELECT COUNT(*) FROM leads")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    now = datetime.now()
    
    sample_leads_data = [
        {
            "telegram_id": "10023451",
            "username": "kevin_uta_dev",
            "full_name": "Kevin Marcelo Caiza",
            "phone": "0998765432",
            "email": "kcaiza@uta.edu.ec",
            "user_type": "ESTUDIANTE_UTA",
            "interested_course_id": 19, # GH-600 Agentic AI
            "intent_score": 0.95,
            "status": "A PUNTO DE INSCRIBIRSE",
            "sentiment": "URGENTE",
            "closure_probability": "ALTA",
            "notes": "Estudiante de 8vo semestre FISEI. Confirmó que pagará $40 hoy por transferencia Banco del Pichincha. Requiere validar cupo.",
            "last_message": "Perfecto, soy estudiante de la UTA. ¿A qué cuenta del CTT hago la transferencia para enviar el comprobante de los $40?",
            "delta_hours": 1,
            "conversation": [
                ("user", "Buenas tardes, quiero saber sobre el curso de GitHub Certified: Agentic AI Developer", "CONSULTA_CURSO"),
                ("bot", "¡Hola Kevin! 👋 Excelente elección. El curso **Preparación GitHub Certified: Agentic AI Developer (GH-600)** inicia el 14 de noviembre de 2026 (32 horas, 100% virtual por Zoom). Aprenderás Git/GitHub, GitHub Actions, Copilot y creación de agentes con Model Context Protocol (MCP). ¿Eres estudiante o graduado de la UTA?", "RESPUESTA_CURSO"),
                ("user", "Sí, soy estudiante de FISEI en la UTA. ¿Cuánto me costaría y qué horario tiene?", "CONSULTA_PRECIO"),
                ("bot", "¡Genial! Al ser estudiante activo de la UTA tienes subsidio institucional: el costo es de tan solo **$40,00** (público general $60,00). El horario es los sábados de 08:00 a 14:00 (14, 21, 28 de nov y 5 de dic). Además, recibes certificado digital con QR del CTT-FISEI. Los cupos son limitados a 25 personas.", "RESPUESTA_PRECIO"),
                ("user", "Perfecto, soy estudiante de la UTA. ¿A qué cuenta del CTT hago la transferencia para enviar el comprobante de los $40?", "INTENCION_COMPRA")
            ]
        },
        {
            "telegram_id": "10023452",
            "username": "ana_redes",
            "full_name": "Ing. Ana Lucía Paredes",
            "phone": "0987123456",
            "email": "anaparedes@gmail.com",
            "user_type": "PUBLICO_GENERAL",
            "interested_course_id": 16, # CCNA Cisco
            "intent_score": 0.88,
            "status": "A PUNTO DE INSCRIBIRSE",
            "sentiment": "POSITIVO",
            "closure_probability": "ALTA",
            "notes": "Trabaja en telecomunicaciones. Preguntó por laboratorios presenciales de switches y routers los sábados.",
            "last_message": "¿Hasta cuándo tengo para registrarme en el formulario de CCNA y apartar el puesto?",
            "delta_hours": 2,
            "conversation": [
                ("user", "Hola, me interesa el curso de CCNA Redes Cisco. ¿Es presencial?", "CONSULTA_CURSO"),
                ("bot", "¡Hola Ana! Un gusto saludarte. El curso **CCNA: Introducción a las redes** es modalidad **Híbrida** (70 horas de capacitación): sesiones virtuales los viernes de 19:00 a 21:00 y prácticas en laboratorio con switches y routers reales en el Campus Huachi los sábados de 08:00 a 13:00.", "RESPUESTA_CURSO"),
                ("user", "Me parece muy bien, no soy de la UTA, ¿cuál es el precio para público externo?", "CONSULTA_PRECIO"),
                ("bot", "Para público en general la inversión es de **$180,00** (incluye acceso a Cisco NetAcad, laboratorios equipados y certificado digital con código QR oficial).", "RESPUESTA_PRECIO"),
                ("user", "¿Hasta cuándo tengo para registrarme en el formulario de CCNA y apartar el puesto?", "INTENCION_COMPRA")
            ]
        },
        {
            "telegram_id": "10023453",
            "username": "diego_prog",
            "full_name": "Diego Alexander Torres",
            "phone": "0991122334",
            "email": "diegotorres@outlook.com",
            "user_type": "DOCENTE_GRADUADO_UTA",
            "interested_course_id": 21, # Python 2
            "intent_score": 0.65,
            "status": "INTERESADO",
            "sentiment": "NEUTRAL",
            "closure_probability": "MEDIA",
            "notes": "Graduado UTA. Ya tomó Python 1 el año pasado y quiere seguir con Python 2.",
            "last_message": "¿Qué temas ven en Fundamentos de Python 2? ¿Ven programación orientada a objetos?",
            "delta_hours": 5,
            "conversation": [
                ("user", "Buenas, ¿tienen abierto Fundamentos de Python 2?", "CONSULTA_CURSO"),
                ("bot", "¡Hola Diego! Sí, el curso **Fundamentos de Python 2** (40 horas) se encuentra actualmente con inscripciones abiertas. Al ser graduado de la UTA cuentas con tarifa preferencial de $50.", "RESPUESTA_CURSO"),
                ("user", "¿Qué temas ven en Fundamentos de Python 2? ¿Ven programación orientada a objetos?", "CONSULTA_PENSUM")
            ]
        },
        {
            "telegram_id": "10023454",
            "username": "carolina_m",
            "full_name": "Dra. Carolina Morales",
            "phone": "0965544332",
            "email": "carolina.hr@empresa.com",
            "user_type": "PUBLICO_GENERAL",
            "interested_course_id": 15, # IA RRHH
            "intent_score": 1.0,
            "status": "INSCRITO",
            "sentiment": "POSITIVO",
            "closure_probability": "ALTA",
            "notes": "Venta cerrada y pagada. Registrada en Google Forms y agregada al aula virtual de Moodle.",
            "last_message": "¡Listo! Ya llené el formulario de inscripción y subí el comprobante. Gracias por la atención.",
            "delta_hours": 12,
            "conversation": [
                ("user", "Deseo inscribirme en IA para Recursos Humanos", "INTENCION_COMPRA"),
                ("bot", "¡Bienvenida Dra. Carolina! El curso de IA para Gestión de RRHH tiene un costo de $60 para público en general (32 horas). Puedes registrarte en el siguiente enlace oficial: https://docs.google.com/forms/d/e/1FAIpQLSeWhh69h-nGZYQvWkFIyR1riMYBOc61CC7YmWL49XBo64I3zA/viewform", "RESPUESTA_INSCRIPCION"),
                ("user", "¡Listo! Ya llené el formulario de inscripción y subí el comprobante. Gracias por la atención.", "CONFIRMACION_INSCRIPCION")
            ]
        },
        {
            "telegram_id": "10023455",
            "username": "patricio_rob",
            "full_name": "Patricio Robalino",
            "phone": "",
            "email": "",
            "user_type": "NO_DEFINIDO",
            "interested_course_id": 20, # Arduino
            "intent_score": 0.35,
            "status": "NUEVO",
            "sentiment": "NEUTRAL",
            "closure_probability": "BAJA",
            "notes": "Consultó sobre materiales para Arduino.",
            "last_message": "¿El curso de Arduino incluye el kit de sensores o hay que comprarlo aparte?",
            "delta_hours": 18,
            "conversation": [
                ("user", "Hola, me gustaría saber sobre el curso de certificación de Arduino", "CONSULTA_CURSO"),
                ("bot", "¡Hola Patricio! El curso **Preparación Arduino Certification Program** tiene 32 horas de duración. Te prepara para la certificación oficial abordando circuitos, programación de microcontroladores y proyectos prácticos.", "RESPUESTA_CURSO"),
                ("user", "¿El curso de Arduino incluye el kit de sensores o hay que comprarlo aparte?", "CONSULTA_MATERIALES")
            ]
        },
        {
            "telegram_id": "10023456",
            "username": "sofia_cert",
            "full_name": "Sofía Cárdenas",
            "phone": "0989988771",
            "email": "sofia.c@correo.com",
            "user_type": "DOCENTE_GRADUADO_UTA",
            "interested_course_id": None,
            "intent_score": 0.20,
            "status": "SEGUIMIENTO_PENDIENTE",
            "sentiment": "NEUTRAL",
            "closure_probability": "BAJA",
            "notes": "Preguntó cómo verificar un certificado antiguo del CTT FISEI.",
            "last_message": "¿Dónde puedo verificar la validez de mi certificado que obtuve el semestre anterior?",
            "delta_hours": 24,
            "conversation": [
                ("user", "¿Dónde puedo verificar la validez de mi certificado que obtuve el semestre anterior?", "CONSULTA_CERTIFICADO"),
                ("bot", "¡Hola Sofía! Puedes validar cualquier certificado oficial del CTT-FISEI directamente en el portal: https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php ingresando el código único de tu documento.", "RESPUESTA_CERTIFICADO")
            ]
        }
    ]

    for lead_info in sample_leads_data:
        delta = timedelta(hours=lead_info["delta_hours"])
        lead_time = (now - delta).isoformat()
        
        cursor.execute("""
        INSERT INTO leads (
            telegram_id, username, full_name, phone, email, user_type,
            interested_course_id, intent_score, status, sentiment,
            last_message, last_interaction, created_at, notes, closure_probability
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_info["telegram_id"],
            lead_info["username"],
            lead_info["full_name"],
            lead_info["phone"],
            lead_info["email"],
            lead_info["user_type"],
            lead_info["interested_course_id"],
            lead_info["intent_score"],
            lead_info["status"],
            lead_info["sentiment"],
            lead_info["last_message"],
            lead_time,
            lead_time,
            lead_info["notes"],
            lead_info["closure_probability"]
        ))
        lead_id = cursor.lastrowid

        # Insert conversation
        for sender, msg, intent in lead_info["conversation"]:
            cursor.execute("""
            INSERT INTO conversations (lead_id, sender, message, detected_intent, detected_entities, timestamp)
            VALUES (?, ?, ?, ?, '{}', ?)
            """, (lead_id, sender, msg, intent, lead_time))

        # If hot or closed, insert a sales action
        if lead_info["status"] == "A PUNTO DE INSCRIBIRSE":
            cursor.execute("""
            INSERT INTO sales_actions (lead_id, action_type, details, timestamp)
            VALUES (?, 'OFERTA_ENVIADA', 'Prospecto con alta intención de compra. Se compartieron datos bancarios y formulario.', ?)
            """, (lead_id, lead_time))
        elif lead_info["status"] == "INSCRITO":
            cursor.execute("""
            INSERT INTO sales_actions (lead_id, action_type, details, timestamp)
            VALUES (?, 'INSCRIPCION_CONFIRMADA', 'Pago validado. Venta cerrada exitosamente.', ?)
            """, (lead_id, lead_time))

    # Update inquiries count on courses
    cursor.execute("UPDATE courses SET inquiries_count = 14 WHERE id = 19")
    cursor.execute("UPDATE courses SET inquiries_count = 11 WHERE id = 16")
    cursor.execute("UPDATE courses SET inquiries_count = 7 WHERE id = 21")
    cursor.execute("UPDATE courses SET inquiries_count = 5 WHERE id = 20")
    cursor.execute("UPDATE courses SET inquiries_count = 8 WHERE id = 15")

    conn.commit()
    conn.close()
    print("Seeded sample leads and conversation history.")

def run_seed():
    print("Initializing Database...")
    init_db()
    print("Seeding Courses...")
    seed_courses()
    print("Seeding Certificates...")
    seed_certificates()
    print("Seeding Sample Leads & Conversations...")
    seed_sample_leads()
    print("Seeding Completed Successfully!")

if __name__ == "__main__":
    run_seed()
