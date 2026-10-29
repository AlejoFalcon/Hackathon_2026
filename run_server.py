import uvicorn
import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure backend and root are in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from seed_data import run_seed

if __name__ == "__main__":
    print("=" * 70)
    print("[*] INICIANDO SISTEMA CTT-FISEI UTA: AGENTE IA & DASHBOARD DE VENTAS")
    print("=" * 70)
    
    # Initialize DB and seeds if not already done
    run_seed()
    
    port = int(os.getenv("PORT", 8000))
    print(f"\n[+] Dashboard disponible en: http://localhost:{port}/")
    print(f"[+] API Docs disponible en: http://localhost:{port}/docs")
    print(f"[+] Bot de Telegram: Configurable en el panel o mediante TELEGRAM_BOT_TOKEN")
    print("=" * 70 + "\n")
    
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=False)
