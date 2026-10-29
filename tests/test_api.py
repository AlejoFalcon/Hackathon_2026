"""
API Endpoints and Integration Tests for CTT FISEI Platform.
"""
import sys
import os
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app import app
from database import init_db

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")

    def test_metrics_endpoint(self):
        resp = self.client.get("/api/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_leads", data)
        self.assertIn("hot_leads", data)
        self.assertIn("conversion_rate", data)
        self.assertIn("top_courses", data)

    def test_list_leads_and_filtering(self):
        resp = self.client.get("/api/leads")
        self.assertEqual(resp.status_code, 200)
        leads = resp.json()
        self.assertIsInstance(leads, list)
        self.assertGreater(len(leads), 0)

        # Filter by hot status
        resp_hot = self.client.get("/api/leads?status=A%20PUNTO%20DE%20INSCRIBIRSE")
        self.assertEqual(resp_hot.status_code, 200)
        hot_leads = resp_hot.json()
        for hl in hot_leads:
            self.assertEqual(hl["status"], "A PUNTO DE INSCRIBIRSE")

    def test_courses_endpoint(self):
        resp = self.client.get("/api/courses")
        self.assertEqual(resp.status_code, 200)
        courses = resp.json()
        self.assertGreater(len(courses), 10)
        
        # Check course 19 (GH-600)
        resp_c19 = self.client.get("/api/courses/19")
        self.assertEqual(resp_c19.status_code, 200)
        c19 = resp_c19.json()
        self.assertIn("Agentic AI", c19["title"])

    def test_certificate_verify_endpoint(self):
        # Valid cert
        resp = self.client.get("/api/certificates/verify?query=UTA-CTT-2026-9041")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["certificate"]["student_name"], "Carlos Andrés Morales Ortiz")

        # Invalid cert
        resp_invalid = self.client.get("/api/certificates/verify?query=NONEXISTENT_CODE_XYZ")
        self.assertEqual(resp_invalid.status_code, 200)
        data_inv = resp_invalid.json()
        self.assertFalse(data_inv["found"])

    def test_chat_simulation_endpoint(self):
        payload = {
            "message": "Hola, ¿cuánto cuesta el curso de Cisco CCNA y cómo me inscribo?",
            "user_id": "test_lead_sim_99",
            "user_name": "Estudiante Prueba",
            "user_type": "ESTUDIANTE_UTA"
        }
        resp = self.client.post("/api/chat/simulate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("bot_response", data)
        self.assertIn("analysis", data)
        self.assertEqual(data["analysis"]["intent"], "INTENCION_COMPRA")
        self.assertGreaterEqual(data["analysis"]["intent_score"], 0.85)

    def test_update_lead_status_and_notes(self):
        # Fetch first lead
        leads = self.client.get("/api/leads").json()
        lead_id = leads[0]["id"]

        # Update notes
        resp_note = self.client.post(f"/api/leads/{lead_id}/notes", json={"notes": "Cliente confirmó pago Banco Pichincha"})
        self.assertEqual(resp_note.status_code, 200)

        # Update status to INSCRITO
        resp_status = self.client.post(f"/api/leads/{lead_id}/status", json={"status": "INSCRITO", "notes": "Cierre completado"})
        self.assertEqual(resp_status.status_code, 200)

        # Check detail
        resp_detail = self.client.get(f"/api/leads/{lead_id}")
        self.assertEqual(resp_detail.status_code, 200)
        lead_detail = resp_detail.json()["lead"]
        self.assertEqual(lead_detail["status"], "INSCRITO")

if __name__ == "__main__":
    unittest.main()
