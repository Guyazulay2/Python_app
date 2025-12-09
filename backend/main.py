from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, engine

# יצירת אפליקציה
app = FastAPI()

# CORS - חובה כדי שהפרונט (פורט 80) ידבר עם הבק (פורט 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
REQUEST_COUNT = Counter('app_requests_total', 'Total request count')

@app.get("/api/hello")
def read_root(db: Session = Depends(get_db)):
    REQUEST_COUNT.inc()
    
    # בדיקה אמיתית מול הדאטהבייס
    try:
        result = db.execute(text("SELECT 1"))
        db_status = "Connected"
    except Exception as e:
        db_status = f"Error: {str(e)}"

    return {
        "message": "Full Stack Production App",
        "database_status": db_status,
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
