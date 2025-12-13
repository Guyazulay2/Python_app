# main.py - FastAPI Network Monitoring Master (קוד סופי ומתוקן)

import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# --- FastAPI Imports ---
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session # ייבוא Session ל-Type Hinting

# --- SQLAlchemy / DB Imports ---
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import sessionmaker 
from sqlalchemy.ext.declarative import declarative_base

# --- Prometheus Imports ---
from prometheus_client import make_wsgi_app, Counter
from fastapi.middleware.wsgi import WSGIMiddleware

# --- הגדרות לוגים ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =======================================================
# 1. הגדרת FastAPI (חובה להיות ראשון!)
# =======================================================

app = FastAPI(title="Network Monitor Master") 

# =======================================================
# 2. Pydantic Models (תואם ל-Agent)
# =======================================================

class Connection(BaseModel):
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    state: str
    bytes_sent: int = 0
    bytes_recv: int = 0
    container: Optional[str] = None
    process_name: Optional[str] = None

class DockerContainer(BaseModel):
    id: str
    name: str
    image: str
    ip_address: str
    ports: List[str]
    networks: List[str]
    status: str
    labels: Dict[str, str]

class NetworkStats(BaseModel):
    bytes_sent: int = Field(alias="BytesSent")
    bytes_recv: int = Field(alias="BytesReceived")
    packets_sent: int
    packets_recv: int

# מודל Snapshot הראשי שמתקבל מה-Agent
class AgentSnapshot(BaseModel):
    timestamp: str
    hostname: str
    connections: List[Connection]
    open_ports: List[int]
    containers: List[DockerContainer]
    dns_queries: List[str]
    network_stats: NetworkStats
    
    # מאפשר שימוש בשמות שדות שאינם Pythonic כמו "BytesSent"
    model_config = {'populate_by_name': True} 


# =======================================================
# 3. קונפיגורציית DB ו-SQLAlchemy
# =======================================================

DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_NAME = os.getenv("POSTGRES_DB", "mydb")
# DB_HOST חייב להיות שם השירות של ה-DB ב-docker-compose
DB_HOST = os.getenv("DB_HOST", "db") 

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

Base = declarative_base()

class Snapshot(Base):
    """מודל SQLAlchemy לשמירת Snapshot ב-PostgreSQL."""
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    hostname = Column(String, index=True)
    connections = Column(JSON)
    open_ports = Column(JSON)
    containers = Column(JSON)
    network_stats = Column(JSON)
    dns_queries = Column(JSON)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_size=10, 
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency ל-FastAPI: מחזיר Session DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_db():
    """יצירת טבלאות עם הפעלת האפליקציה"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables successfully created/checked.")
    except Exception as e:
        logger.error(f"Failed to connect or create DB tables: {e}")
        logger.error("DB connection failed. Check DB_HOST and credentials.")

# =======================================================
# 4. Global State & Prometheus
# =======================================================

class GlobalState:
    # מאחסן את ה-Snapshot האחרון שהתקבל
    last_snapshot: Optional[Dict[str, Any]] = None 
    # רשימת חיבורי WebSocket פעילים
    active_websockets: List[WebSocket] = [] 
    
STATE = GlobalState()

# --- הגדרת Prometheus ---
data_received_counter = Counter(
    'master_data_received_total', 
    'Total number of data snapshots received from agents'
)
metrics_app = make_wsgi_app()
app.mount("/metrics", WSGIMiddleware(metrics_app)) 

# =======================================================
# 5. Middlewares (CORS)
# =======================================================
# התיקון הקריטי ל-Frontend: מאפשר גישה מפורט 3000
app.add_middleware(
    CORSMiddleware,
    # חשוב: ניתן לקבע ל-"*" אבל עדיף לרשום את הכתובות המדויקות
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Manager (פונקציית שידור) ---
async def broadcast_snapshot_update(snapshot_data: Dict[str, Any]):
    """שולח את ה-Snapshot המלא לכל ה-WebSockets הפעילים."""
    # שולח הודעה פשוטה ל-Frontend שמבצע משיכת נתונים
    message = json.dumps({"type": "snapshot_update"}) 
    dead_connections = []
    
    for ws in STATE.active_websockets:
        try:
            await ws.send_text(message)
        except (RuntimeError, WebSocketDisconnect):
            dead_connections.append(ws)
    
    # הסרת חיבורים מתים
    for ws in dead_connections:
        if ws in STATE.active_websockets:
            STATE.active_websockets.remove(ws)


# =======================================================
# 6. Agent Endpoint (קליטת נתונים ושמירה ל-DB)
# =======================================================

@app.post("/api/agent/data")
async def receive_agent_data(snapshot: AgentSnapshot, db: Session = Depends(get_db)):
    """קליטת Snapshot מה-Agent, שמירה ל-DB, ושידור ל-Frontend."""
    
    # המרת מודל Pydantic ל-dict
    current_snapshot_data = snapshot.model_dump(by_alias=True)
    
    # 1. שמירת Snapshot ל-DB
    try:
        new_snapshot = Snapshot(
            timestamp=datetime.now(),
            hostname=snapshot.hostname,
            connections=current_snapshot_data.get("connections", []),
            open_ports=current_snapshot_data.get("open_ports", []),
            containers=current_snapshot_data.get("containers", []),
            network_stats=current_snapshot_data.get("network_stats", {}),
            dns_queries=current_snapshot_data.get("dns_queries", []),
        )
        db.add(new_snapshot)
        db.commit()
        db.refresh(new_snapshot)
        
        # 2. עדכון מונה Prometheus
        data_received_counter.inc()
        logger.info(f"Master received data from {snapshot.hostname}. DB Write: OK.")

    except Exception as e:
        logger.error(f"Database insertion failed for {snapshot.hostname}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database insertion failed.")
    
    # 3. עדכון המצב הגלובלי (משמש ל-HTTP GET)
    STATE.last_snapshot = current_snapshot_data

    # 4. שידור עדכון לכל ה-WebSockets
    await broadcast_snapshot_update(current_snapshot_data)
    
    return {"message": "Data received, saved, and broadcasted successfully"}

# =======================================================
# 7. Frontend API Endpoints (משיכת נתונים)
# =======================================================

@app.get("/api/connections")
async def get_connections():
    """Endpoint 1/7: חיבורים פעילים."""
    if not STATE.last_snapshot:
        raise HTTPException(status_code=404, detail="No snapshot data available.")
    return {"connections": STATE.last_snapshot.get("connections", [])}

@app.get("/api/containers")
async def get_containers():
    """Endpoint 2/7: מידע על קונטיינרים."""
    if not STATE.last_snapshot:
        raise HTTPException(status_code=404, detail="No snapshot data available.")
    return {"containers": STATE.last_snapshot.get("containers", [])}

@app.get("/api/ports")
async def get_ports():
    """Endpoint 3/7: פורטים פתוחים."""
    if not STATE.last_snapshot:
        raise HTTPException(status_code=404, detail="No snapshot data available.")
    
    ports_list = STATE.last_snapshot.get("open_ports", [])
    # יצירת מבנה הנתונים הנדרש על ידי ה-Frontend
    formatted_ports = [{"port": p, "container": "System"} for p in ports_list]
    return {"ports": formatted_ports}

@app.get("/api/anomalies")
async def get_anomalies():
    """Endpoint 4/7: אנומליות (כרגע מחזיר רשימה ריקה)."""
    # אם תרצה להוסיף לוגיקת אנומליות בעתיד, היא תבוא לכאן
    return {"anomalies": []} 

@app.get("/api/stats")
async def get_stats():
    """Endpoint 5/7: סטטיסטיקות כלליות."""
    if not STATE.last_snapshot:
        # מחזיר אפסים במקום שגיאה כדי שה-Frontend לא יקרוס
        return {
            "total_connections": 0, "total_containers": 0, "total_ports": 0,
            "bytes_sent": 0, "bytes_recv": 0
        }
        
    stats_raw = STATE.last_snapshot.get("network_stats", {})
    
    return {
        "total_connections": len(STATE.last_snapshot.get("connections", [])),
        "total_containers": len(STATE.last_snapshot.get("containers", [])),
        "total_ports": len(STATE.last_snapshot.get("open_ports", [])),
        # שימוש בשמות השדות כפי שהם ב-Pydantic (עם alias)
        "bytes_sent": stats_raw.get("BytesSent", 0), 
        "bytes_recv": stats_raw.get("BytesReceived", 0)
    }

@app.get("/api/topology")
async def get_topology():
    """Endpoint 6/7: נתוני טופולוגיה (מודלים בסיסיים)."""
    if not STATE.last_snapshot:
        raise HTTPException(status_code=404, detail="No snapshot data available.")

    nodes = []
    # יצירת צומתי טופולוגיה מהקונטיינרים
    for cont in STATE.last_snapshot.get("containers", []):
        nodes.append({
            "id": cont.get('name', cont['id']),
            "label": cont.get('name', 'Unknown'),
            "ip": cont.get('ip_address', 'N/A'),
            "status": cont.get('status', 'N/A'),
            "classification": "Container"
        })

    return {"nodes": nodes, "edges": []}

@app.get("/api/history")
# שימוש ב-Depends(get_db) כדי לקבל Session DB
def get_history(db: Session = Depends(get_db), limit: int = 10): 
    """Endpoint 7/7: מחזיר את ה-Snapshots האחרונים מה-DB."""
    try:
        # שאילתת SQLAlchemy
        history = db.query(Snapshot).order_by(Snapshot.timestamp.desc()).limit(limit).all()
        
        results = [{
            "timestamp": item.timestamp.isoformat(),
            "hostname": item.hostname,
            "connections_count": len(item.connections),
            "containers_count": len(item.containers),
        } for item in history]
        
        return {"status": "ok", "data": results}
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching history.")


# =======================================================
# 8. WebSocket Endpoint 
# =======================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """מטפל בחיבורי WebSocket מול ה-Frontend."""
    await websocket.accept()
    STATE.active_websockets.append(websocket)

    # שליחת ה-Snapshot הראשוני מיד לאחר החיבור
    if STATE.last_snapshot:
        # הודעה מפורטת עם כל הנתונים (או שתשתמש ב-broadcast_snapshot_update)
        await websocket.send_text(json.dumps({"type": "initial_snapshot", "data": STATE.last_snapshot})) 

    try:
        # לולאה שמחזיקה את החיבור פתוח
        while True:
            # ממתין לקבלת הודעות מהלקוח (לא חובה, אבל שומר על הלולאה פעילה)
            await websocket.receive_text()
    except WebSocketDisconnect:
        # ניתוק תקין
        if websocket in STATE.active_websockets:
            STATE.active_websockets.remove(websocket)
    except Exception as e:
        # ניתוק לא תקין
        logger.error(f"WebSocket error: {e}")
        if websocket in STATE.active_websockets:
            STATE.active_websockets.remove(websocket)

# =======================================================
# 9. הוראות הרצה (אם מריצים ישירות ולא דרך uvicorn)
# =======================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)