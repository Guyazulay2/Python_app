# main.py - FastAPI Network Monitoring Master
# הרצה: uvicorn main:app --reload --host 0.0.0.0 --port 8000
# דרישות: pip install fastapi uvicorn pydantic

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional
import time
import json
import logging
import asyncio

# הגדרת לוגים
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =======================================================
# 1. Pydantic Models (תואם ל-Agent ול-Frontend)
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

class AgentSnapshot(BaseModel):
    timestamp: str
    hostname: str
    connections: List[Connection]
    open_ports: List[int]
    containers: List[DockerContainer]
    dns_queries: List[str]
    network_stats: NetworkStats

class Anomaly(BaseModel):
    timestamp: str
    severity: str
    type: str
    message: str
    details: Optional[Dict[str, Any]] = None

class TopologyNode(BaseModel):
    id: str
    label: str
    ip: str
    status: str
    classification: str

class TopologyEdge(BaseModel):
    source: str
    target: str
    bytes: int

# =======================================================
# 2. Global State & Mock Data (נתוני דמה)
# =======================================================

def create_mock_data():
    """יוצר נתוני דמה להתחלה לפני קבלת Snapshot."""
    mock_connections = [
        Connection(src_ip="172.18.0.3", src_port=54321, dst_ip="172.18.0.2", dst_port=8000, state="ESTABLISHED", bytes_sent=10240, bytes_recv=5120).model_dump(),
        Connection(src_ip="172.18.0.4", src_port=44332, dst_ip="8.8.8.8", dst_port=53, state="CLOSE_WAIT").model_dump(),
    ]
    mock_containers = [
        DockerContainer(id="abc1", name="backend", image="python:3.10", ip_address="172.18.0.2", ports=["8000/tcp"], networks=["app_net"], status="running", labels={}).model_dump(),
        DockerContainer(id="def2", name="db", image="postgres", ip_address="172.18.0.3", ports=["5432/tcp"], networks=["app_net"], status="running", labels={}).model_dump(),
    ]
    mock_ports = [{"port": 8000, "container": "backend"}, {"port": 5432, "container": "db"}]
    
    mock_anomalies = [
        Anomaly(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            severity="LOW",
            type="Connection Spike",
            message="Initial dummy anomaly for testing.",
            details={"count": 55}
        ).model_dump()
    ]
    
    mock_topology = {
        "nodes": [
            TopologyNode(id="backend", label="Backend Service", ip="172.18.0.2", status="running", classification="App").model_dump(),
            TopologyNode(id="db", label="Postgres DB", ip="172.18.0.3", status="running", classification="Database").model_dump(),
        ],
        "edges": [
            TopologyEdge(source="backend", target="db", bytes=10000).model_dump()
        ]
    }
    
    return {
        "connections": mock_connections, 
        "containers": mock_containers, 
        "ports": mock_ports,
        "anomalies": mock_anomalies,
        "topology": mock_topology,
        "stats": {
            "total_connections": len(mock_connections), 
            "total_containers": len(mock_containers), 
            "total_ports": len(mock_ports),
            "bytes_in_per_sec": 12000,
            "bytes_out_per_sec": 8000
        }
    }

class GlobalState:
    last_snapshot: Dict[str, Any] = create_mock_data()
    previous_network_stats: Optional[NetworkStats] = None
    previous_timestamp: Optional[float] = None
    active_websockets: List[WebSocket] = [] # לניהול חיבורי WebSocket
    
STATE = GlobalState()
app = FastAPI()

# =======================================================
# 3. Middlewares (CORS)
# =======================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================================================
# 4. Agent Endpoint (קליטת נתונים)
# =======================================================

@app.post("/api/agent/data")
async def receive_agent_data(snapshot: AgentSnapshot):
    """קליטת Snapshot מה-Agent ושמירת הנתונים הגולמיים."""
    global STATE
    
    now = time.time()
    
    # חישוב קצב העברת נתונים
    if STATE.previous_network_stats and STATE.previous_timestamp:
        time_diff = now - STATE.previous_timestamp
        
        bytes_recv_diff = snapshot.network_stats.bytes_recv - STATE.previous_network_stats.bytes_recv
        STATE.last_snapshot["stats"]["bytes_in_per_sec"] = round(bytes_recv_diff / time_diff, 2) if time_diff > 0 else 0

        bytes_sent_diff = snapshot.network_stats.bytes_sent - STATE.previous_network_stats.bytes_sent
        STATE.last_snapshot["stats"]["bytes_out_per_sec"] = round(bytes_sent_diff / time_diff, 2) if time_diff > 0 else 0

    # שמירת נתוני Agent
    STATE.last_snapshot["connections"] = snapshot.connections
    STATE.last_snapshot["containers"] = snapshot.containers
    
    # עדכון פורטים לפורמט הנדרש
    STATE.last_snapshot["ports"] = [{"port": p, "container": "System"} for p in snapshot.open_ports]
    
    # עדכון סטטיסטיקות
    STATE.last_snapshot["stats"]["total_connections"] = len(snapshot.connections)
    STATE.last_snapshot["stats"]["total_containers"] = len(snapshot.containers)
    STATE.last_snapshot["stats"]["total_ports"] = len(snapshot.open_ports)
    
    STATE.previous_network_stats = snapshot.network_stats
    STATE.previous_timestamp = now
    
    logger.info(f"Master received data from {snapshot.hostname}. Connections: {len(snapshot.connections)}")
    
    # שידור עדכון לכל ה-WebSockets שמחוברים (לצורך עדכון מיידי ב-Frontend)
    await broadcast_snapshot_update()
    
    return {"message": "Data received and processed successfully"}

async def broadcast_snapshot_update():
    """שולח הודעת 'snapshot' לכל ה-WebSockets הפעילים."""
    message = {"type": "snapshot"}
    dead_connections = []
    for ws in STATE.active_websockets:
        try:
            await ws.send_json(message)
        except RuntimeError:
            dead_connections.append(ws)
    
    # הסרת חיבורים מתים
    for ws in dead_connections:
        STATE.active_websockets.remove(ws)


# =======================================================
# 5. Frontend API Endpoints (ה-6 הנדרשים)
# =======================================================

@app.get("/api/connections")
async def get_connections():
    """Endpoint 1/6: חיבורים פעילים."""
    return {"connections": STATE.last_snapshot["connections"]}

@app.get("/api/containers")
async def get_containers():
    """Endpoint 2/6: מידע על קונטיינרים."""
    return {"containers": STATE.last_snapshot["containers"]}

@app.get("/api/ports")
async def get_ports():
    """Endpoint 3/6: פורטים פתוחים."""
    return {"ports": STATE.last_snapshot["ports"]}

@app.get("/api/anomalies")
async def get_anomalies():
    """Endpoint 4/6: אנומליות ואירועים חריגים."""
    return {"anomalies": STATE.last_snapshot["anomalies"]}

@app.get("/api/stats")
async def get_stats():
    """Endpoint 5/6: סטטיסטיקות כלליות (לכרטיסיות)."""
    return STATE.last_snapshot["stats"]

@app.get("/api/topology")
async def get_topology():
    """Endpoint 6/6: נתוני טופולוגיה (Nodes & Edges)."""
    return STATE.last_snapshot["topology"]

# =======================================================
# 6. WebSocket Endpoint (לעדכונים בזמן אמת)
# =======================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    STATE.active_websockets.append(websocket)
    logger.info("New WebSocket connection accepted.")
    try:
        # לולאה שרצה ושומרת על החיבור פתוח
        while True:
            # מקבלת הודעה אבל לא עושה איתה כלום (רק שומרת על חיבור דו-כיווני)
            await websocket.receive_text()
    except Exception as e:
        logger.warning(f"WebSocket connection closed: {e}")
    finally:
        # ניקוי החיבור כשהוא נסגר
        STATE.active_websockets.remove(websocket)


# =======================================================
# 7. הוראות הרצה
# =======================================================
if __name__ == "__main__":
    import uvicorn
    print("----------------------------------------------------------------------")
    print("🚀 Network Master is running and listening on 0.0.0.0:8000")
    print("----------------------------------------------------------------------")
    # הרצה עם Uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
