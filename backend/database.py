"""
Database module for CTT FISEI Sales & Agent System.
Uses SQLite with WAL mode for fast concurrent read/write.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ctt_database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE,
            title TEXT,
            description TEXT,
            category TEXT,
            hours INTEGER DEFAULT 32,
            modality TEXT DEFAULT 'Virtual',
            schedule TEXT,
            start_date TEXT,
            end_date TEXT,
            registration_deadline TEXT,
            price_uta_student REAL,
            price_uta_staff REAL,
            price_general REAL,
            instructors TEXT,
            syllabus TEXT,
            materials TEXT,
            registration_url TEXT,
            status TEXT DEFAULT 'ABIERTO',
            inquiries_count INTEGER DEFAULT 0
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            user_type TEXT DEFAULT 'NO_DEFINIDO',
            interested_course_id INTEGER,
            intent_score REAL DEFAULT 0.1,
            status TEXT DEFAULT 'NUEVO',
            sentiment TEXT DEFAULT 'NEUTRAL',
            last_message TEXT,
            last_interaction TEXT,
            created_at TEXT,
            notes TEXT DEFAULT '',
            closure_probability TEXT DEFAULT 'BAJA',
            FOREIGN KEY (interested_course_id) REFERENCES courses(id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            sender TEXT,
            message TEXT,
            detected_intent TEXT,
            detected_entities TEXT,
            timestamp TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cert_code TEXT UNIQUE,
            student_name TEXT,
            student_cedula TEXT,
            course_name TEXT,
            issue_date TEXT,
            hours INTEGER,
            grade REAL,
            qr_verification_url TEXT,
            status TEXT DEFAULT 'VALIDO'
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS sales_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            action_type TEXT,
            details TEXT,
            timestamp TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
        """)
    conn.close()

def get_or_create_lead(telegram_id: str, username: str = "", full_name: str = "") -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE telegram_id = ?", (str(telegram_id),))
    row = cursor.fetchone()
    now_iso = datetime.now().isoformat()
    if row:
        lead = dict(row)
        # Update username / full_name if provided and empty
        if (username and not lead["username"]) or (full_name and not lead["full_name"]):
            cursor.execute(
                "UPDATE leads SET username = COALESCE(NULLIF(?, ''), username), full_name = COALESCE(NULLIF(?, ''), full_name) WHERE id = ?",
                (username, full_name, lead["id"])
            )
            conn.commit()
            lead["username"] = username or lead["username"]
            lead["full_name"] = full_name or lead["full_name"]
        conn.close()
        return lead

    # Create new lead
    cursor.execute("""
    INSERT INTO leads (telegram_id, username, full_name, phone, email, user_type, intent_score, status, sentiment, last_interaction, created_at, closure_probability)
    VALUES (?, ?, ?, '', '', 'NO_DEFINIDO', 0.15, 'NUEVO', 'NEUTRAL', ?, ?, 'BAJA')
    """, (str(telegram_id), username or f"user_{telegram_id}", full_name or username or "Interesado", now_iso, now_iso))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM leads WHERE id = ?", (new_id,))
    lead = dict(cursor.fetchone())
    conn.close()
    return lead

def update_lead(lead_id: int, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    if not fields:
        conn.close()
        return
    values.append(lead_id)
    query = f"UPDATE leads SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

def log_message(lead_id: int, sender: str, message: str, detected_intent: str = "GENERAL", detected_entities: dict = None):
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    ent_json = json.dumps(detected_entities or {}, ensure_ascii=False)
    cursor.execute("""
    INSERT INTO conversations (lead_id, sender, message, detected_intent, detected_entities, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (lead_id, sender, message, detected_intent, ent_json, now_iso))
    cursor.execute("UPDATE leads SET last_message = ?, last_interaction = ? WHERE id = ?", (message, now_iso, lead_id))
    conn.commit()
    conn.close()

def get_lead_conversations(lead_id: int) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE lead_id = ? ORDER BY id ASC", (lead_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_all_leads(status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    query = """
    SELECT l.*, c.title as course_title, c.code as course_code
    FROM leads l
    LEFT JOIN courses c ON l.interested_course_id = c.id
    WHERE 1=1
    """
    params = []
    if status and status != "TODOS":
        query += " AND l.status = ?"
        params.append(status)
    if search:
        query += " AND (l.full_name LIKE ? OR l.username LIKE ? OR l.phone LIKE ? OR l.email LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    query += " ORDER BY l.last_interaction DESC"
    cursor.execute(query, tuple(params))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_courses(category: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM courses WHERE 1=1"
    params = []
    if category and category != "TODOS":
        query += " AND category = ?"
        params.append(category)
    if status and status != "TODOS":
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC"
    cursor.execute(query, tuple(params))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_course_by_id(course_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def increment_course_inquiries(course_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE courses SET inquiries_count = inquiries_count + 1 WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()

def log_sales_action(lead_id: int, action_type: str, details: str):
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO sales_actions (lead_id, action_type, details, timestamp)
    VALUES (?, ?, ?, ?)
    """, (lead_id, action_type, details, now_iso))
    conn.commit()
    conn.close()

def get_sales_actions(lead_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    if lead_id:
        cursor.execute("""
        SELECT a.*, l.full_name, l.phone, l.username
        FROM sales_actions a
        JOIN leads l ON a.lead_id = l.id
        WHERE a.lead_id = ?
        ORDER BY a.id DESC
        """, (lead_id,))
    else:
        cursor.execute("""
        SELECT a.*, l.full_name, l.phone, l.username
        FROM sales_actions a
        JOIN leads l ON a.lead_id = l.id
        ORDER BY a.id DESC LIMIT 50
        """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def verify_certificate(query_str: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    q = f"%{query_str.strip()}%"
    cursor.execute("""
    SELECT * FROM certificates 
    WHERE cert_code LIKE ? OR student_cedula LIKE ? OR student_name LIKE ?
    LIMIT 1
    """, (q, q, q))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_dashboard_metrics() -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leads")
    total_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'A PUNTO DE INSCRIBIRSE'")
    hot_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'INSCRITO'")
    closed_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'INTERESADO'")
    interested_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM conversations")
    total_messages = cursor.fetchone()[0]

    cursor.execute("""
    SELECT status, COUNT(*) as count 
    FROM leads 
    GROUP BY status
    """)
    status_distribution = {r["status"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("""
    SELECT user_type, COUNT(*) as count 
    FROM leads 
    GROUP BY user_type
    """)
    user_types = {r["user_type"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("""
    SELECT c.title, c.inquiries_count, COUNT(l.id) as interested_count
    FROM courses c
    LEFT JOIN leads l ON l.interested_course_id = c.id
    WHERE c.status = 'ABIERTO'
    GROUP BY c.id
    ORDER BY (c.inquiries_count + COUNT(l.id)*2) DESC
    LIMIT 6
    """)
    top_courses = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
    SELECT detected_intent, COUNT(*) as count
    FROM conversations
    WHERE sender = 'user' AND detected_intent IS NOT NULL
    GROUP BY detected_intent
    ORDER BY count DESC
    LIMIT 7
    """)
    top_intents = [dict(r) for r in cursor.fetchall()]

    conn.close()

    conversion_rate = round((closed_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "closed_leads": closed_leads,
        "interested_leads": interested_leads,
        "total_messages": total_messages,
        "conversion_rate": conversion_rate,
        "status_distribution": status_distribution,
        "user_types": user_types,
        "top_courses": top_courses,
        "top_intents": top_intents
    }

def get_system_config(key: str, default: str = "") -> str:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_system_config(key: str, value: str):
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO system_config (key, value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """, (key, value, now_iso))
    conn.commit()
    conn.close()
