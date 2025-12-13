# Agent Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
# התקנת התלויות
RUN pip install --no-cache-dir -r requirements.txt
COPY agent_client.py .
# הפעלת הסקריפט הראשי
CMD ["python", "agent_client.py"]
