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
pip install -r backend/requirements.txt
```

Start the API server from the repository root:

```bash
python -m uvicorn backend.main:app --reload
```

Available endpoints:

- `GET /health`
- `GET /assets`

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

By default, the UI calls `http://localhost:8000/assets` and renders the seeded assets in a Tailwind-styled table.

Optional: override API URL by setting `VITE_API_BASE_URL` before starting the frontend.
