# UMEagleEye Infrastructure

This folder contains a Docker Compose stack for PostgreSQL and Redis.

## Folder structure

- `docker-compose.yml` : service definitions
- `.env` : local environment values used by Docker Compose
- `data/postgres_data/` : PostgreSQL bind mount data
- `data/redis_data/` : Redis bind mount data

## For users downloading the project

1. Install Docker Desktop (Windows) and make sure Docker Engine is running.
2. Open a terminal in this `UMEagleEye` folder.
3. Review and update values in `.env` before the first startup.
4. Start the stack:

   ```bash
   docker compose up -d
   ```

5. Check status:

   ```bash
   docker compose ps
   ```

6. Service endpoints:
   - PostgreSQL: `localhost:5432`
   - Redis: `localhost:6379`

## Common commands

Start or recreate containers:

```bash
docker compose up -d
```

Stop containers:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f
```

Reset local data (deletes database contents in `data/`):

```bash
docker compose down
```

Then delete files under:

- `data/postgres_data/`
- `data/redis_data/`

## Notes

- This project uses bind mounts (`./data/...`) instead of named volumes.

## Phase 1 seed script

The Python seeder lives in `backend/` and will drop, recreate, and populate the PostgreSQL schema with mock assets, connections, SBOMs, events, advisories, and posture metrics.

Install the dependencies:

```bash
pip install -r backend/requirements.txt
```

Run the seed script from the repository root:

```bash
python -m backend.seed_db
```

The script reads the Docker Compose credentials from `.env` by default and connects to `localhost:5432`.

## Phase 2 API and frontend

### FastAPI backend

Install backend dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

Start the API server from the repository root:

```bash
python -m uvicorn backend.main:app --reload
```

Available endpoints:

- `GET /health` - Health check
- `GET /assets` - List all discovered assets
- `POST /scans/submit` - Submit a network scan
- `GET /scans/{task_id}` - Get scan results

### Network Scanner Worker

The scanner worker uses Redis and nmap to automatically discover network devices.

**Prerequisites:**
- Install nmap (required for network scanning)
  - **Windows:**
    - Option 1 (requires admin): `choco install nmap` in elevated shell
    - Option 2 (no admin needed): Download installer from https://nmap.org/download and run it
    - Verify: `nmap --version` in a new terminal
  - **macOS:** `brew install nmap`
  - **Linux:** `sudo apt-get install nmap`

**Start the scanner worker** (new terminal):

```bash
python -m backend.scanner_worker
```

The worker will listen on Redis for scan tasks and store discovered assets in PostgreSQL.

**Submit a scan via CLI:**

```bash
# Auto-detect and scan your primary local network (easiest!)
python -m backend.scan_cli --auto

# Scan ALL local networks nearby (discover all devices!)
python -m backend.scan_cli --auto-all

# List available local networks to see all IP ranges
python -m backend.scan_cli --list-networks

# Scan a specific network range
python -m backend.scan_cli 10.0.0.0/24
python -m backend.scan_cli 192.168.1.0/24
```

**Submit a scan via API:**

```bash
curl -X POST http://localhost:8000/scans/submit \
  -H "Content-Type: application/json" \
  -d '{"network_range": "10.0.0.0/24"}'
```

**Get scan results:**

```bash
curl http://localhost:8000/scans/{task_id}
```

### React frontend (Vite)

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the Vite dev server:

```bash
npm run dev
```

The frontend includes:
- **Executive Dashboard** with key metrics (total assets, critical assets, average criticality)
- **Asset Trend Charts** showing discovery growth over 7 days
- **Device Distribution Pie Chart** showing asset types
- **Asset Inventory Table** with detailed asset information
- **Real-time Updates** pulling latest data from the API

Visit **http://localhost:5173** to view the dashboard.

Optional: override API URL by setting `VITE_API_BASE_URL` before starting the frontend.

### Port Drift Detection

Detect unauthorized port changes and security deviations across scans.

**How it works:**
- Compares current open ports against baseline from previous scans
- Generates `PORT_DRIFT` events when new ports open or close
- Creates `BASELINE_SNAPSHOT` events to track port state history
- Can be run manually or scheduled via cron/Task Scheduler

**Run drift detection:**

```bash
# Check assets scanned in the last 24 hours (default)
python -m backend.drift_detector

# Check assets scanned in the last 48 hours
python -m backend.drift_detector --hours 48
```

**Output example:**
```json
{
  "status": "completed",
  "timestamp": "2026-04-13T10:50:00+00:00",
  "assets_scanned": 5,
  "total_drift_events": 2,
  "assets_with_drift": [
    {
      "hostname": "DESKTOP-ABC",
      "ip_address": "192.168.1.100",
      "drifts": 1
    }
  ]
}
```

**Drift Event Types:**
- `NEW_PORTS`: One or more ports opened (severity: WARNING/CRITICAL)
- `CLOSED_PORTS`: Ports closed (severity: INFO)
- `BASELINE_SNAPSHOT`: Baseline capture for historical comparison

**Schedule Daily Drift Detection (Windows):**

To run drift detection automatically every day at 2:00 AM:

```powershell
$pythonExe = "c:\FYP\UMEagleEye-CAASM\.venv\Scripts\python.exe"
$workDir = "c:\FYP\UMEagleEye-CAASM"
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "-m backend.drift_detector --hours 24" -WorkingDirectory $workDir
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "UMEagleEye-DriftDetection" -Action $action -Trigger $trigger -Description "Daily drift detection for UMEagleEye infrastructure" -Force
```

**Manage the scheduled task:**

```powershell
# View task details (status, next run time, etc.)
Get-ScheduledTask -TaskName "UMEagleEye-DriftDetection"

# Run it immediately (instead of waiting until 2 AM)
Start-ScheduledTask -TaskName "UMEagleEye-DriftDetection"

# Disable the task (pauses scheduled runs)
Disable-ScheduledTask -TaskName "UMEagleEye-DriftDetection"

# Delete the task
Unregister-ScheduledTask -TaskName "UMEagleEye-DriftDetection" -Confirm:$false
```

**Schedule Daily Drift Detection (Linux/macOS):**

Use cron to run at 2:00 AM daily:

```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * * cd /path/to/UMEagleEye-CAASM && python -m backend.drift_detector --hours 24
```

## Telegram Bot Integration

The Telegram bot sends notifications about infrastructure events.

**Setup:**

1. Create a Telegram bot with [@BotFather](https://t.me/botfather)
2. Get your chat ID with [@userinfobot](https://t.me/userinfobot)
3. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN=your_bot_token_here
   export TELEGRAM_CHAT_ID=your_chat_id_here
   ```

**Features:**
- Notification when new assets are discovered
- Alerts for critical assets (criticality ≥ 8)
- Scan completion reports
- Daily summary reports

**Test the bot:**

```bash
python -m backend.telegram_bot
```

To integrate with the scanner, use:
```python
from backend.telegram_bot import get_telegram_bot

bot = get_telegram_bot()
if bot:
    bot.notify_asset_discovered("DESKTOP-123", "192.168.1.100", "Workstation")
```
