# agent_client.py - Network Agent (מנוקה משגיאות רווחים U+00A0)

import os
import time
import json
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

import requests
import psutil
import docker
import socket

# --- הגדרת לוגים בסיסיים ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- קבלת משתני סביבה ---
MASTER_URL = os.getenv("MASTER_URL", "http://backend:8000/api/agent/data") # ברירת מחדל ל-Compose
AGENT_HOSTNAME = os.getenv("AGENT_HOSTNAME", socket.gethostname())
AGENT_IP = os.getenv("AGENT_IP", "0.0.0.0")
INTERVAL = int(os.getenv("INTERVAL", 5))

# --- אובייקטי לקוח גלובליים ---
docker_client = None
try:
    # אתחול לקוח הדוקר (דורש גישה ל-/var/run/docker.sock)
    docker_client = docker.from_env()
    logger.info("Docker client successfully initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Docker client. Ensure /var/run/docker.sock is mapped. Error: {e}")

# --- פונקציות איסוף נתונים אמיתיים ---

def get_real_connections(agent_ip: str) -> List[Dict[str, Any]]:
    """אוסף חיבורי רשת אמיתיים באמצעות psutil."""
    connections = []
    for conn in psutil.net_connections(kind='inet'):
        
        # התעלם מחיבורים לא שלמים
        if conn.status == 'NONE' or not conn.laddr or not conn.raddr:
            continue
        
        try:
            # psutil.Process עלול להיכשל אם אין הרשאת PID Host
            process_name = psutil.Process(conn.pid).name() if conn.pid else "N/A"
        except (psutil.NoSuchProcess, TypeError, AttributeError):
            process_name = "N/A"

        connections.append({
            "src_ip": conn.laddr.ip,
            "src_port": conn.laddr.port,
            "dst_ip": conn.raddr.ip,
            "dst_port": conn.raddr.port,
            "state": conn.status,
            "bytes_sent": 0,
            "bytes_recv": 0,
            "container": "N/A", 
            "process_name": process_name
        })
    return connections

def get_real_network_stats() -> Dict[str, Any]:
    """אוסף סטטיסטיקות רשת כלליות באמצעות psutil."""
    net_io = psutil.net_io_counters()
    return {
        "BytesSent": net_io.bytes_sent,
        "BytesReceived": net_io.bytes_recv,
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv
    }

def get_real_open_ports() -> List[int]:
    """אוסף פורטים במצב האזנה (LISTEN) באמצעות psutil."""
    open_ports = set()
    try:
        # אוסף את כל חיבורי הרשת שנמצאים במצב האזנה
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr:
                # מוסיף את פורט המקור לרשימה
                open_ports.add(conn.laddr.port)
    except Exception as e:
        logger.error(f"Error collecting open ports data: {e}")
        return []
    
    return list(open_ports)


def get_real_containers() -> List[Dict[str, Any]]:
    """אוסף נתונים על קונטיינרי דוקר פעילים."""
    if not docker_client:
        return []
    
    containers_data = []
    try:
        for container in docker_client.containers.list():
            # איסוף כתובת ה-IP הראשונה שנמצאת
            ip_address = next(iter(container.attrs['NetworkSettings']['Networks'].values()), {}).get('IPAddress', 'N/A')
            
            # איסוף מיפוי פורטים
            ports_list = []
            if container.ports:
                for private_port, public_port_list in container.ports.items():
                    if public_port_list:
                        # מציג את פורט המארח (public)
                        for public_port_info in public_port_list:
                            ports_list.append(f"{private_port} -> {public_port_info.get('HostPort', 'N/A')}")
                    else:
                        ports_list.append(private_port) # פורטים שלא פורסמו

            networks = list(container.attrs['NetworkSettings']['Networks'].keys())
            
            containers_data.append({
                "id": container.short_id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else container.image.short_id,
                "ip_address": ip_address,
                "ports": ports_list,
                "networks": networks,
                "status": container.status,
                "labels": dict(container.labels)
            })
    except Exception as e:
        logger.error(f"Error collecting Docker containers data: {e}")
        return []
    
    return containers_data


def get_real_system_stats() -> Optional[str]:
    """מחזיר כתובת IP מקומית אמיתית של ה-Agent."""
    try:
        # משתמש ב-socket.AF_INET כדי להיות תואם לסביבות קונטיינרים מינימליות
        INET_FAMILY = socket.AF_INET 
    except Exception:
        INET_FAMILY = psutil.AF_INET 
    
    try:
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                # מחפש IPV4 שאינו לולאה חוזרת (127.)
                if snic.family == INET_FAMILY and not snic.address.startswith('127.'):
                    return snic.address
        return None 
    except Exception as e:
        logger.error(f"Error fetching real IP: {e}")
        return None


def create_real_snapshot() -> Optional[Dict[str, Any]]:
    """יוצר Snapshot שלם עם נתונים אמיתיים."""
    
    real_agent_ip = get_real_system_stats()
    if not real_agent_ip:
        logger.warning("Could not determine Agent's IP Address. Using environment variable IP.")
        real_agent_ip = AGENT_IP
    
    # 1. איסוף נתונים
    containers = get_real_containers()
    connections = get_real_connections(real_agent_ip)
    network_stats = get_real_network_stats()
    open_ports = get_real_open_ports()
    
    # 2. בניית ה-Snapshot הסופי
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "hostname": AGENT_HOSTNAME,
        "connections": connections,
        "open_ports": open_ports,
        "containers": containers,
        "dns_queries": [], 
        "network_stats": network_stats
    }
    return snapshot

# --- לוגיקת שליחה ראשית ---

def run_agent():
    """הלולאה הראשית של הסוכן, שולחת Snapshot כל 5 שניות."""
    logger.info(f"🚀 Agent {AGENT_HOSTNAME} starting. Sending real data to: {MASTER_URL}")
    
    while True:
        try:
            snapshot = create_real_snapshot()
            
            if not snapshot:
                logger.error("Snapshot creation failed, skipping send cycle.")
                time.sleep(INTERVAL)
                continue

            response = requests.post(
                MASTER_URL, 
                json=snapshot, 
                timeout=5
            )
            
            # בדיקת התגובה
            if response.status_code == 200:
                logger.info(f"✅ Data sent successfully. Containers: {len(snapshot['containers'])}. Open Ports: {len(snapshot['open_ports'])}")
            elif response.status_code == 422:
                logger.error(f"❌ Pydantic Validation Error (422) on Master. Check Agent data structure. Response: {response.text[:200]}...")
            else:
                logger.error(f"❌ Failed to send data. Status: {response.status_code}, Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"🚨 Connection failed. Master not reachable at {MASTER_URL}. Retrying in {INTERVAL}s...")
        except requests.exceptions.Timeout:
            logger.error(f"🚨 Request timed out. Master took too long to respond. Retrying in {INTERVAL}s...")
        except Exception as e:
            logger.error(f"🚨 An unexpected error occurred: {e}")

        time.sleep(INTERVAL)

if __name__ == "__main__":
    run_agent()