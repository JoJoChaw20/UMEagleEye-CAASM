"""
Port Drift Detection Script
Compares scan baselines between scans and generates drift events when new ports open.
Useful for detecting unauthorized service changes or security deviations.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from backend.database import SessionLocal, engine
from backend.models import Asset, Base, Event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_open_ports(baseline_state: dict) -> set:
    """
    Extract open ports from baseline_state.
    
    Args:
        baseline_state: Dictionary with open_ports list
        
    Returns:
        Set of open port numbers
    """
    if not baseline_state:
        return set()
    
    open_ports = baseline_state.get("open_ports", [])
    return {p["port"] for p in open_ports if p.get("state") == "open"}


def detect_port_drift(asset: Asset, db: Session) -> list:
    """
    Detect if new ports have opened since the last scan.
    
    Args:
        asset: Asset to check for drift
        db: Database session
        
    Returns:
        List of drift events created
    """
    drift_events = []
    
    # Get the most recent PORT_DRIFT or BASELINE_SNAPSHOT events
    recent_events = (
        db.query(Event)
        .filter(
            and_(
                Event.asset_id == asset.asset_id,
                Event.event_type.in_(["PORT_DRIFT", "BASELINE_SNAPSHOT"]),
            )
        )
        .order_by(desc(Event.timestamp))
        .limit(2)
        .all()
    )
    
    if not recent_events:
        # First scan - create baseline snapshot
        baseline_snapshot = Event(
            event_id=uuid4(),
            asset_id=asset.asset_id,
            event_type="BASELINE_SNAPSHOT",
            severity="INFO",
            details={
                "open_ports": asset.baseline_state.get("open_ports", []),
                "snapshot_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(baseline_snapshot)
        db.commit()
        logger.info(f"Created baseline snapshot for {asset.hostname}")
        return drift_events
    
    # Compare current baseline with last snapshot
    current_ports = get_open_ports(asset.baseline_state)
    
    last_baseline_event = recent_events[0]
    previous_ports = {
        p["port"]
        for p in last_baseline_event.details.get("open_ports", [])
        if p.get("state") == "open"
    }
    
    # Detect new ports
    new_ports = current_ports - previous_ports
    closed_ports = previous_ports - current_ports
    
    if new_ports:
        logger.warning(
            f"Port drift detected on {asset.hostname} ({asset.ip_address}): "
            f"New ports {new_ports}"
        )
        
        new_port_details = [
            p for p in asset.baseline_state.get("open_ports", [])
            if p.get("port") in new_ports and p.get("state") == "open"
        ]
        
        drift_event = Event(
            event_id=uuid4(),
            asset_id=asset.asset_id,
            event_type="PORT_DRIFT",
            severity="WARNING" if len(new_ports) <= 2 else "CRITICAL",
            details={
                "drift_type": "NEW_PORTS",
                "new_ports": new_port_details,
                "closed_ports": list(closed_ports),
                "previous_ports": list(previous_ports),
                "current_ports": list(current_ports),
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(drift_event)
        db.commit()
        drift_events.append(drift_event)
    
    if closed_ports:
        logger.info(
            f"Ports closed on {asset.hostname} ({asset.ip_address}): {closed_ports}"
        )
        
        closed_port_details = [
            {"port": port, "state": "closed"} for port in closed_ports
        ]
        
        close_event = Event(
            event_id=uuid4(),
            asset_id=asset.asset_id,
            event_type="PORT_DRIFT",
            severity="INFO",
            details={
                "drift_type": "CLOSED_PORTS",
                "closed_ports": closed_port_details,
                "new_ports": list(new_ports),
                "previous_ports": list(previous_ports),
                "current_ports": list(current_ports),
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(close_event)
        db.commit()
        drift_events.append(close_event)
    
    # Create a fresh baseline snapshot after drift detection
    if new_ports or closed_ports:
        baseline_snapshot = Event(
            event_id=uuid4(),
            asset_id=asset.asset_id,
            event_type="BASELINE_SNAPSHOT",
            severity="INFO",
            details={
                "open_ports": asset.baseline_state.get("open_ports", []),
                "snapshot_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(baseline_snapshot)
        db.commit()
    
    return drift_events


def run_drift_detection(hours_lookback: int = 24) -> dict:
    """
    Run drift detection on all assets scanned in the last N hours.
    
    Args:
        hours_lookback: How many hours back to check for changes
        
    Returns:
        Dictionary with detection summary
    """
    db = SessionLocal()
    
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)
        
        # Get assets scanned recently
        recent_assets = (
            db.query(Asset)
            .filter(Asset.last_scanned >= cutoff_time)
            .all()
        )
        
        logger.info(f"Running drift detection on {len(recent_assets)} recently scanned assets")
        
        total_drifts = 0
        assets_with_drift = []
        
        for asset in recent_assets:
            drifts = detect_port_drift(asset, db)
            if drifts:
                total_drifts += len(drifts)
                assets_with_drift.append(
                    {
                        "hostname": asset.hostname,
                        "ip_address": asset.ip_address,
                        "drifts": len(drifts),
                    }
                )
        
        result = {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "assets_scanned": len(recent_assets),
            "total_drift_events": total_drifts,
            "assets_with_drift": assets_with_drift,
        }
        
        logger.info(json.dumps(result, indent=2))
        return result
    
    except Exception as e:
        logger.error(f"Drift detection failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Detect port drift in scanned assets"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Look back N hours for recent scans (default: 24)",
    )
    
    args = parser.parse_args()
    
    result = run_drift_detection(hours_lookback=args.hours)
    exit(0 if result["status"] == "completed" else 1)
