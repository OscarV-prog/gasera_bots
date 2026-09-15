import sys
from pathlib import Path

# Forzar UTF-8 en terminal de Windows para emojis y caracteres especiales
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure root directory is on sys.path when running src/app.py directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config.settings import get_settings
from src.channels.web.router import router as web_router
from src.channels.whatsapp.router import router as whatsapp_router
from src.channels.telegram.router import router as telegram_router
from src.channels.instagram.router import router as instagram_router
from src.admin.router import router as admin_router

app = FastAPI(title="Multi-Channel Sales Agent & Petroil Backoffice")

# Configuración de CORS segura y configurable
settings = get_settings()
raw_cors = settings.cors_origins.strip()
allowed_origins = ["*"] if raw_cors == "*" else [o.strip() for o in raw_cors.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Static files for Admin Backoffice
ADMIN_STATIC_DIR = Path(__file__).parent / "admin" / "static"
if ADMIN_STATIC_DIR.exists():
    app.mount("/static/admin", StaticFiles(directory=ADMIN_STATIC_DIR), name="admin_static")

# Uploaded media (Tank readings photos, proof of delivery, etc.)
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "tank_readings").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Admin Backoffice routes (/admin and /api/admin/...)
app.include_router(admin_router, prefix="")

# Web endpoints at root (for the Sales Studio)
app.include_router(web_router, prefix="")

# Webhooks
app.include_router(whatsapp_router, prefix="/webhooks/whatsapp")
app.include_router(whatsapp_router, prefix="/webhook")
app.include_router(telegram_router, prefix="/webhooks/telegram")
app.include_router(instagram_router, prefix="/webhooks/instagram")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Sales Agent & Admin Backoffice starting on http://localhost:3000")
    print("👉 Backoffice Administrativo: http://localhost:3000/admin")
    uvicorn.run("src.app:app", host="0.0.0.0", port=3000, reload=False)
