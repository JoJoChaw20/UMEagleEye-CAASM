from datetime import datetime
from uuid import UUID

import redis
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Asset
from backend.scanner_worker import ScanWorker


class AssetResponse(BaseModel):
    asset_id: UUID
    hostname: str
    ip_address: str
    mac_address: str
    owner: str
    device_type: str
    hardware_vendor: str
    os_info: str
    criticality_score: int
    last_scanned: datetime

    model_config = {"from_attributes": True}

    @field_validator("ip_address", "mac_address", mode="before")
    @classmethod
    def convert_network_fields(cls, value):
        return str(value)


class ScanRequest(BaseModel):
    network_range: str


class ScanResponse(BaseModel):
    task_id: str
    status: str
    message: str


class ScanResultResponse(BaseModel):
    task_id: str
    status: str
    network_range: str = None
    discovered_count: int = None
    stored_assets: list = None
    error: str = None
    timestamp: str = None


class DashboardStatsResponse(BaseModel):
    total_assets: int
    critical_assets: int
    avg_criticality: float
    device_type_distribution: dict
    assets_by_owner: dict


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host="localhost", port=6379, decode_responses=True
    )


# Initialize Redis worker
try:
    redis_client = get_redis_client()
    redis_client.ping()
    scan_worker = ScanWorker()
except redis.ConnectionError:
    scan_worker = None


app = FastAPI(
    title="UMEagleEye API",
    version="0.2.0",
    description="Infrastructure CAASM Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/assets", response_model=list[AssetResponse])
def get_assets(db: Session = Depends(get_db)) -> list[Asset]:
    return db.query(Asset).order_by(Asset.hostname.asc()).all()


@app.post("/scans/submit", response_model=ScanResponse)
def submit_scan(request: ScanRequest) -> dict:
    """Submit a network scan task."""
    if not scan_worker:
        raise HTTPException(
            status_code=503,
            detail="Redis connection failed. Scanner not available.",
        )

    try:
        task_id = scan_worker.submit_scan(request.network_range)
        return {
            "task_id": task_id,
            "status": "submitted",
            "message": f"Scan submitted for {request.network_range}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to submit scan: {str(e)}"
        )


@app.get("/scans/{task_id}", response_model=ScanResultResponse)
def get_scan_result(task_id: str) -> dict:
    """Get the result of a scan task."""
    if not scan_worker:
        raise HTTPException(
            status_code=503,
            detail="Redis connection failed. Scanner not available.",
        )

    result = scan_worker.get_result(task_id)
    if not result:
        raise HTTPException(
            status_code=404, detail=f"Scan task {task_id} not found"
        )

    return result


@app.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)) -> dict:
    """Get dashboard statistics and metrics."""
    assets = db.query(Asset).all()
    
    # Calculate metrics
    total_assets = len(assets)
    critical_assets = sum(1 for a in assets if a.criticality_score >= 8)
    avg_criticality = (
        sum(a.criticality_score for a in assets) / total_assets if total_assets > 0 else 0
    )
    
    # Device type distribution
    device_distribution = {}
    for asset in assets:
        device_type = asset.device_type
        device_distribution[device_type] = device_distribution.get(device_type, 0) + 1
    
    # Owner distribution
    owner_distribution = {}
    for asset in assets:
        owner = asset.owner
        owner_distribution[owner] = owner_distribution.get(owner, 0) + 1
    
    return {
        "total_assets": total_assets,
        "critical_assets": critical_assets,
        "avg_criticality": round(avg_criticality, 2),
        "device_type_distribution": device_distribution,
        "assets_by_owner": owner_distribution,
    }
