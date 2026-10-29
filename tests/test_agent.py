"""
Unit and integration tests for CTT FISEI AI Agent and Sales Logic.
"""
import sys
import os
import asyncio
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from database import init_db, get_courses, verify_certificate, get_or_create_lead
from llm_agent import detect_intent, match_course, identify_user_type, process_expert_response, generate_agent_response

class TestAIAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        from seed_data import seed_courses, seed_certificates
        seed_courses()
        seed_certificates()
        cls.courses = get_courses()

    def test_intent_detection(self):
        # High buying intent (Hot Lead)
        intent, score = detect_intent("Quiero inscribirme ahora mismo, ¿a qué cuenta del CTT hago la transferencia?")
        self.assertEqual(intent, "INTENCION_COMPRA")
        self.assertGreaterEqual(score, 0.90)

        # Price inquiry
        intent, score = detect_intent("¿Cuánto cuesta el curso de Python para estudiantes?")
        self.assertEqual(intent, "CONSULTA_PRECIO")
        self.assertGreaterEqual(score, 0.70)

        # Schedule inquiry
        intent, score = detect_intent("¿Qué horarios y fechas de inicio tienen para Cisco CCNA?")
        self.assertEqual(intent, "CONSULTA_HORARIO")

        # Certificate inquiry
        intent, score = detect_intent("¿Cómo puedo verificar mi certificado digital con código QR?")
        self.assertEqual(intent, "CONSULTA_CERTIFICADO")

    def test_course_matching(self):
        # Match GH-600 Agentic AI
        c = match_course("Me interesa la certificación de Agentic AI y GitHub Copilot", self.courses)
        self.assertIsNotNone(c)
        self.assertEqual(c["id"], 19)

        # Match Cisco CCNA
        c = match_course("Deseo saber sobre redes de datos cisco ccna switches", self.courses)
        self.assertIsNotNone(c)
        self.assertEqual(c["id"], 16)

        # Match Arduino
        c = match_course("Tienen cursos de Arduino para principiantes", self.courses)
        self.assertIsNotNone(c)
        self.assertIn(c["id"], [13, 20])

    def test_user_type_identification(self):
        self.assertEqual(identify_user_type("Soy estudiante de 6to semestre en la UTA"), "ESTUDIANTE_UTA")
        self.assertEqual(identify_user_type("Soy graduado de la FISEI"), "DOCENTE_GRADUADO_UTA")
        self.assertEqual(identify_user_type("Trabajo en una empresa externa, no soy de la UTA"), "PUBLICO_GENERAL")

    def test_certificate_lookup(self):
        cert = verify_certificate("UTA-CTT-2026-9041")
        self.assertIsNotNone(cert)
        self.assertEqual(cert["student_name"], "Carlos Andrés Morales Ortiz")
        self.assertEqual(cert["status"], "VALIDO")

    def test_hot_lead_progression(self):
        lead = {"id": 999, "intent_score": 0.2, "status": "NUEVO", "user_type": "ESTUDIANTE_UTA"}
        result = process_expert_response(
            "Me convencieron, ¿dónde realizo el pago de los $40 para apartar mi cupo en GH-600?",
            lead,
            self.courses
        )
        self.assertEqual(result["status"], "A PUNTO DE INSCRIBIRSE")
        self.assertGreaterEqual(result["intent_score"], 0.85)
        self.assertIn("docs.google.com/forms", result["response"])

    def test_async_agent_generation(self):
        lead = get_or_create_lead("test_user_async_01", username="test_tester", full_name="Tester Unitario")
        result = asyncio.run(generate_agent_response("Hola, ¿cuáles son los cursos abiertos?", lead))
        self.assertIn("response", result)
        self.assertGreater(len(result["response"]), 50)

if __name__ == "__main__":
    unittest.main()
