"""
FastAPI Main Application for CTT FISEI AI Agent & Sales Dashboard.
Provides REST API, Real-time Simulation, and Static Dashboard Serving.
"""
import os
import sys
import asyncio
from contextlib import asynccontextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    init_db,
    get_all_leads,
    get_or_create_lead,
    update_lead,
    log_message,
    get_lead_conversations,
    get_courses,
    get_course_by_id,
    get_dashboard_metrics,
    verify_certificate,
    log_sales_action,
    get_sales_actions,
    get_system_config,
    set_system_config
)
from llm_agent import generate_agent_response
from telegram_bot import start_telegram_bot, stop_telegram_bot, bot_app
import scraper

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB is initialized
    init_db()
    # Try to start Telegram bot if token is present
    token = os.getenv("TELEGRAM_BOT_TOKEN") or get_system_config("TELEGRAM_BOT_TOKEN")
    if token and token.strip():
        asyncio.create_task(start_telegram_bot(token))
    yield
    # Shutdown
    await stop_telegram_bot()

app = FastAPI(
    title="CTT-FISEI AI Agent & Sales Dashboard",
    description="Sistema de Agente de IA Prospector y Dashboard de Ventas para CTT FISEI UTA",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatSimulateRequest(BaseModel):
    message: str
    user_id: Optional[str] = "sim_user_01"
    user_name: Optional[str] = "Usuario de Prueba"
    user_type: Optional[str] = "ESTUDIANTE_UTA"

class LeadStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None

class LeadNotesRequest(BaseModel):
    notes: str

class SalesActionRequest(BaseModel):
    action_type: str
    details: str

class ConfigRequest(BaseModel):
    telegram_bot_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

# --- API Endpoints ---

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "system": "CTT FISEI AI Sales Platform",
        "telegram_bot_active": bot_app is not None
    }

@app.get("/api/metrics")
def get_metrics():
    return get_dashboard_metrics()

@app.get("/api/leads")
def list_leads(status: Optional[str] = None, search: Optional[str] = None):
    return get_all_leads(status=status, search=search)

@app.get("/api/leads/{lead_id}")
def get_lead_detail(lead_id: int):
    leads = get_all_leads()
    lead = next((l for l in leads if l["id"] == lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    conversations = get_lead_conversations(lead_id)
    actions = get_sales_actions(lead_id)
    return {
        "lead": lead,
        "conversations": conversations,
        "actions": actions
    }

@app.post("/api/leads/{lead_id}/status")
def update_lead_status(lead_id: int, req: LeadStatusRequest):
    prob_map = {
        "INSCRITO": "ALTA",
        "A PUNTO DE INSCRIBIRSE": "ALTA",
        "INTERESADO": "MEDIA",
        "SEGUIMIENTO_PENDIENTE": "MEDIA",
        "NUEVO": "BAJA",
        "DESCARTADO": "BAJA"
    }
    closure_prob = prob_map.get(req.status, "MEDIA")
    update_data = {"status": req.status, "closure_probability": closure_prob}
    if req.notes is not None:
        update_data["notes"] = req.notes
    
    update_lead(lead_id, **update_data)
    log_sales_action(lead_id, f"CAMBIO_ESTADO_{req.status}", f"Estado actualizado a: {req.status}. {req.notes or ''}")
    return {"success": True, "lead_id": lead_id, "new_status": req.status}

@app.post("/api/leads/{lead_id}/notes")
def save_lead_notes(lead_id: int, req: LeadNotesRequest):
    update_lead(lead_id, notes=req.notes)
    log_sales_action(lead_id, "NOTA_ACTUALIZADA", req.notes)
    return {"success": True, "lead_id": lead_id}

@app.post("/api/leads/{lead_id}/action")
def record_sales_action(lead_id: int, req: SalesActionRequest):
    log_sales_action(lead_id, req.action_type, req.details)
    return {"success": True, "lead_id": lead_id}

@app.get("/api/courses")
def list_courses(category: Optional[str] = None, status: Optional[str] = None):
    return get_courses(category=category, status=status)

@app.get("/api/courses/{course_id}")
def get_course_detail(course_id: int):
    c = get_course_by_id(course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return c

@app.post("/api/courses/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    def run_scrape_and_seed():
        from seed_data import seed_courses
        # Scrape
        courses_scraped = []
        for cid in scraper.course_ids:
            c = scraper.scrape_course(cid)
            if c:
                courses_scraped.append(c)
        import json
        with open(scraper.CATALOG_PATH if hasattr(scraper, 'CATALOG_PATH') else "courses_catalog.json", "w", encoding="utf-8") as f:
            json.dump(courses_scraped, f, ensure_ascii=False, indent=2)
        seed_courses()
    
    background_tasks.add_task(run_scrape_and_seed)
    return {"success": True, "message": "Scraper iniciado en segundo plano para sincronizar cursos de ctt-talleresfisei.uta.edu.ec"}

@app.get("/api/certificates/verify")
def certificate_lookup(query: str = Query(..., min_length=2)):
    cert = verify_certificate(query)
    if cert:
        return {"found": True, "certificate": cert}
    return {
        "found": False,
        "message": f"No se encontró certificado para '{query}'. Verifica en el portal oficial.",
        "official_url": "https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php"
    }

@app.post("/api/chat/simulate")
async def simulate_chat(req: ChatSimulateRequest):
    """
    Simulator endpoint: enables testing the AI Agent in the browser dashboard
    without needing a real Telegram client. Updates lead and database in real-time.
    """
    sim_id = f"sim_{req.user_id}"
    lead = get_or_create_lead(sim_id, username=req.user_name.lower().replace(" ", "_"), full_name=req.user_name)
    
    if req.user_type and lead.get("user_type") == "NO_DEFINIDO":
        update_lead(lead["id"], user_type=req.user_type)
        lead["user_type"] = req.user_type

    # AI Response
    result = await generate_agent_response(req.message, lead)

    # Update lead
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

    update_lead(lead["id"], **update_data)

    # Log messages
    log_message(lead["id"], "user", req.message, result["intent"])
    log_message(lead["id"], "bot", result["response"], f"RESPUESTA_{result['intent']}")

    # Refresh lead state
    all_leads = get_all_leads()
    updated_lead = next((l for l in all_leads if l["id"] == lead["id"]), lead)

    return {
        "bot_response": result["response"],
        "analysis": {
            "intent": result["intent"],
            "intent_score": result["intent_score"],
            "status": result["status"],
            "sentiment": result["sentiment"],
            "user_type": result.get("user_type"),
            "phone": result.get("phone"),
            "matched_course_id": result.get("matched_course_id")
        },
        "lead": updated_lead
    }

@app.get("/api/config")
def get_config():
    tg_token = get_system_config("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    masked_tg = f"{tg_token[:6]}...{tg_token[-4:]}" if len(tg_token) > 10 else ("Configurado" if tg_token else "No configurado")
    
    gemini_key = os.getenv("GEMINI_API_KEY") or get_system_config("GEMINI_API_KEY", "")
    masked_gemini = "Activo (Gemini API)" if gemini_key else "Modo Motor Experto NLP CTT (Activo)"

    return {
        "telegram_bot_token_status": masked_tg,
        "telegram_bot_active": bot_app is not None,
        "ai_engine": masked_gemini,
        "institution": "Centro de Transferencia y Desarrollo de Tecnologías CTT-FISEI UTA",
        "official_site": "https://ctt-talleresfisei.uta.edu.ec/course.php",
        "registration_form": "https://docs.google.com/forms/d/e/1FAIpQLSeWhh69h-nGZYQvWkFIyR1riMYBOc61CC7YmWL49XBo64I3zA/viewform"
    }

@app.post("/api/config")
async def update_config(req: ConfigRequest):
    if req.telegram_bot_token is not None:
        token = req.telegram_bot_token.strip()
        set_system_config("TELEGRAM_BOT_TOKEN", token)
        if token:
            await stop_telegram_bot()
            success = await start_telegram_bot(token)
            if not success:
                return {"success": False, "message": "Token guardado pero no se pudo iniciar el bot. Verifica la validez del token de @BotFather."}

    if req.gemini_api_key is not None:
        set_system_config("GEMINI_API_KEY", req.gemini_api_key.strip())
        os.environ["GEMINI_API_KEY"] = req.gemini_api_key.strip()

    if req.openai_api_key is not None:
        set_system_config("OPENAI_API_KEY", req.openai_api_key.strip())
        os.environ["OPENAI_API_KEY"] = req.openai_api_key.strip()

    return {"success": True, "message": "Configuración actualizada correctamente"}

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
