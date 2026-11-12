# AI Incident Investigator - Deployment & Operations Guide

## 1. Overview
The **AI Incident Investigator** is an asynchronous Python ASGI application running on FastAPI and Uvicorn. It is designed for low-overhead deployment in enterprise container clusters (Kubernetes / OpenShift), Docker environments, or standard Linux/Windows virtual machines.

---

## 2. Docker Deployment

### 2.1 Building the Container Image
```bash
docker build -t ai-incident-investigator:2.0.0 .
```

### 2.2 Running with Docker
```bash
docker run -d \
  --name aegis-investigator \
  -p 8000:8000 \
  --restart unless-stopped \
  ai-incident-investigator:2.0.0
```

### 2.3 Running with Docker Compose
A ready-to-run `docker-compose.yml` file is provided:
```bash
docker-compose up -d
```

To view logs:
```bash
docker-compose logs -f
```

---

## 3. Local Development & Virtual Environment Setup

### 3.1 Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- `pip` or `uv` package manager

### 3.2 Installation Steps
```bash
# Clone the repository
git clone https://github.com/kanimozhiraja14/Ai_investigator.git
cd Ai_investigator

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3.3 Running the Application
```bash
# Option 1: Direct module startup
uvicorn incident_investigator.app.main:app --host 0.0.0.0 --port 8000 --reload

# Option 2: Using the runner script
python incident_investigator/run_investigator.py
```
Access the Enterprise Command Center at: `http://localhost:8000`

---

## 4. Production Hardening Checklist

| Security Control | Recommendation | Enforcement in Code |
|:-----------------|:---------------|:--------------------|
| **Read-Only Mode** | Ensure `READ_ONLY=true` in production | Enforced by `ReadOnlyGuard` in `tools.py` |
| **Reverse Proxy** | Terminate TLS via NGINX, Cloudflare, or AWS ALB | Standard reverse proxy configuration |
| **CORS Policy** | Restrict `allow_origins` to authorized internal domains | Configured in `main.py` CORS middleware |
| **Log Redaction** | Sanitize all passwords, tokens, and PII | Sanitized during evidence ingestion |
| **Process Isolation** | Run container as non-root user (`appuser:10001`) | Configured in `Dockerfile` |

---

## 5. Kubernetes Deployment Manifest (Example)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-incident-investigator
  labels:
    app: ai-incident-investigator
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-incident-investigator
  template:
    metadata:
      labels:
        app: ai-incident-investigator
    spec:
      containers:
      - name: investigator
        image: ai-incident-investigator:2.0.0
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 3
          periodSeconds: 5
        resources:
          limits:
            cpu: "1000m"
            memory: "512Mi"
          requests:
            cpu: "250m"
            memory: "256Mi"
```
