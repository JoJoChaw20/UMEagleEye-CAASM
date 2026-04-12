"""
SETUP_GUIDE.md - Network Scanner Implementation Guide

This guide walks through setting up and testing the real network scanning capability.
"""

# Network Scanner Setup & Test Guide

## Component Overview

The system consists of three main components:

1. **Redis**: Message queue for scan tasks
2. **PostgreSQL**: Stores discovered assets
3. **Python Scanner Worker**: Performs nmap scans and stores results
4. **FastAPI**: REST API to trigger scans and retrieve results
5. **React Frontend**: Displays discovered assets

## Prerequisites

### 1. Install nmap (Required)

The scanner requires nmap to perform network scanning.

**Windows:**

Option 1 - Chocolatey (requires elevated/admin shell):
```powershell
# Run PowerShell as Administrator
choco install nmap
```

Option 2 - Direct download (no admin needed):
1. Visit https://nmap.org/download
2. Download the Windows installer (.exe)
3. Run the installer
4. Add nmap to PATH or note the installation directory

**macOS:**
```bash
brew install nmap
```

**Linux:**
```bash
sudo apt-get install nmap
```

Verify installation:
```bash
nmap --version
```

If on Windows and nmap is not in PATH, you may need to provide the full path to the executable.

### 2. Install Python Dependencies

```bash
python -m pip install -r backend/requirements.txt
```

This installs:
- `redis`: Python Redis client
- `python-nmap`: Python wrapper for nmap
- `fastapi`: Web framework
- `psycopg`: PostgreSQL driver
- `sqlalchemy`: ORM

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│              Displays discovered assets                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Server                         │
│  GET /assets  POST /scans/submit  GET /scans/{id}       │
└──┬────────────────────────────────────────────────────┬─┘
   │                                                    │
   ↓                                                    ↓
┌─────────────────────┐                   ┌─────────────────────┐
│    PostgreSQL DB    │←────────────────→ │ Redis Task Queue    │
│   (Stores Assets)   │                   │ (Stores Tasks)      │
└─────────────────────┘                   └────────┬────────────┘
                                                    │
                                                    ↓
                                    ┌─────────────────────────┐
                                    │  Scanner Worker Thread  │
                                    │  (python-nmap)          │
                                    │  Discovers network,     │
                                    │  Stores in Postgres     │
                                    └──────────────────────────┘
```

## Step-by-Step Setup

### Step 1: Start PostgreSQL and Redis

```bash
# From repository root
docker compose up -d
```

Verify:
```bash
docker compose ps
```

You should see:
- `umeagleeye-postgres` running on `localhost:5432`
- `umeagleeye-redis` running on `localhost:6379`

### Step 2: Initialize Database

```bash
# Optional: Reset database (removes mock data)
python -m backend.seed_db
```

### Step 3: Start Scanner Worker

Open a new terminal and run:

```bash
python -m backend.scanner_worker
```

You should see:
```
INFO - Scanner worker started. Listening for tasks...
```

The worker is now listening on Redis for scan requests.

### Step 4: Start API Server

Open another new terminal and run:

```bash
python -m uvicorn backend.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 5: Start Frontend

Open another new terminal and run:

```bash
cd frontend
npm install
npm run dev
```

You should see:
```
VITE v... ready in ... ms

➜  Local:   http://localhost:5173/
```

## Testing the System

### Test 1: Submit a Scan (CLI)

```bash
python -m backend.scan_cli 192.168.1.0/24
```

The scanner will:
1. Discover active hosts on the specified network
2. Perform port scans on discovered hosts
3. Store assets in PostgreSQL
4. Display results

### Test 2: Submit a Scan (API)

```bash
# Submit scan
curl -X POST http://localhost:8000/scans/submit \
  -H "Content-Type: application/json" \
  -d '{"network_range": "10.0.0.0/24"}'

# Response:
# {
#   "task_id": "12345678-1234-...",
#   "status": "submitted",
#   "message": "Scan submitted for 10.0.0.0/24"
# }
```

```bash
# Get scan result
curl http://localhost:8000/scans/12345678-1234-...

# Response:
# {
#   "task_id": "12345678-1234-...",
#   "status": "completed",
#   "network_range": "10.0.0.0/24",
#   "discovered_count": 5,
#   "stored_assets": [...]
# }
```

### Test 3: View Assets in Frontend

1. Visit `http://localhost:5173`
2. You should see a table of discovered assets
3. Each asset shows: Hostname, IP, Owner, Device Type, OS, Criticality Score

### Test 4: View Assets via API

```bash
curl http://localhost:8000/assets
```

## Customization

### Scan Different Networks

When testing locally, use your local network:
- Get your local network: `ipconfig` (Windows) or `ifconfig` (macOS/Linux)
- Common local ranges: `192.168.x.0/24`, `10.0.0.0/24`, `172.16.0.0/12`

### Adjust Port Scanning

Edit [backend/scanner_worker.py](backend/scanner_worker.py#L93) to scan different ports:

```python
# Currently scans: 22, 80, 443, 3389
arguments="-sS -p 22,80,443,3389,5432,3306 -T4"
```

### Configure Device Type Detection

Edit `_infer_device_type()` in [backend/scanner_worker.py](backend/scanner_worker.py#L160) to add more device detection rules.

## Troubleshooting

### "nmap is not installed"

Install nmap using the instructions in Prerequisites section above.

If on Windows and you see this error after installing:
- Verify nmap is in your PATH: `nmap --version`
- If it fails, restart your terminal (new PowerShell window)
- If still failing, use the full path to nmap executable or add it to PATH

### "Cannot connect to Redis"

Verify Redis is running:
```bash
docker compose ps
```

If not running:
```bash
docker compose up -d
```

### "Cannot connect to PostgreSQL"

Verify PostgreSQL is running:
```bash
docker compose ps
```

If not running:
```bash
docker compose up -d
```

### Scan is slow or timing out

Large networks take time to scan. Reduce scope:
```bash
# Good for testing
python -m backend.scan_cli 10.0.0.0/28  # Only 14 hosts

# vs. full subnet
python -m backend.scan_cli 10.0.0.0/16  # 65,536 hosts
```

### Assets not appearing in frontend

1. Make sure scan completed: `curl http://localhost:8000/scans/{task_id}`
2. Check API is returning assets: `curl http://localhost:8000/assets`
3. Check frontend console for errors (F12)
4. Verify API URL: Should be `http://localhost:8000` by default

## Next Steps

- Add scheduled scans (e.g., hourly network discovery)
- Implement scan result comparison and change detection
- Add network topology visualization
- Implement threat detection on discovered ports
- Add multi-network support

## Files Created/Modified

- ✅ `backend/scanner_worker.py` - Main scanner implementation
- ✅ `backend/scan_cli.py` - CLI utility for testing
- ✅ `backend/main.py` - Updated with scan API endpoints
- ✅ `backend/requirements.txt` - Added redis and python-nmap
- ✅ `README.md` - Updated with scanner instructions
