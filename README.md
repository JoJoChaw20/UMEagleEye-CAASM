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
