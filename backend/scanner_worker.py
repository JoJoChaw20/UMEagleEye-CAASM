"""
Redis-based network scanner worker.
Listens for scan tasks on Redis and performs nmap-based network scanning.
Stores discovered assets in PostgreSQL.
"""

import json
import logging
import socket
import subprocess
import sys
from datetime import datetime, timezone
from ipaddress import IPv4Address, IPv4Network
from shutil import which
from uuid import uuid4

import nmap
import redis
from sqlalchemy.orm import Session

from backend.database import SessionLocal, engine
from backend.models import Asset, Base, Event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NetworkScanner:
    """Handles network scanning and asset discovery."""

    def __init__(self):
        self.nm = nmap.PortScanner()
        self.db = SessionLocal()

    def scan_network(self, network_range: str) -> dict:
        """
        Scan a network range for active hosts.

        Args:
            network_range: CIDR notation (e.g., "10.0.0.0/24")

        Returns:
            Dictionary of discovered assets
        """
        logger.info(f"Starting network scan for {network_range}")
        try:
            # Perform a ping scan to discover hosts
            self.nm.scan(hosts=network_range, arguments="-sn -T4")
            discovered = {}

            for host in self.nm.all_hosts():
                try:
                    # Check if host is actually in the scan results
                    if host not in self.nm.all_hosts():
                        continue
                    
                    if self.nm[host].state() == "up":
                        logger.info(f"Host discovered: {host}")
                        device_info = self._get_device_info(host)
                        discovered[host] = device_info
                except KeyError as e:
                    logger.warning(f"Host {host} not fully resolved yet, skipping: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing host {host}: {e}")
                    continue

            logger.info(f"Scan complete. Found {len(discovered)} hosts")
            return discovered

        except nmap.PortScannerError as e:
            logger.error(f"Nmap error: {e}")
            raise

    def _get_device_info(self, host: str) -> dict:
        """
        Get detailed information about a device.

        Args:
            host: IP address to scan

        Returns:
            Dictionary with device information
        """
        try:
            hostname = socket.gethostbyaddr(host)[0]
        except (socket.herror, OSError):
            hostname = f"host-{host.replace('.', '-')}"

        # Perform a more detailed port scan
        try:
            self.nm.scan(hosts=host, arguments="-sS -p 22,80,443,3389 -T4")
            ports = []
            if host in self.nm.all_hosts():
                for proto in self.nm[host].all_protocols():
                    for port in self.nm[host][proto].keys():
                        ports.append(
                            {
                                "port": port,
                                "state": self.nm[host][proto][port]["state"],
                                "protocol": proto,
                            }
                        )
        except nmap.PortScannerError as e:
            logger.warning(f"Could not scan ports for {host}: {e}")
            ports = []

        return {
            "hostname": hostname,
            "ip_address": host,
            "ports": ports,
            "scan_time": datetime.now(timezone.utc).isoformat(),
        }

    def store_asset(self, device_info: dict) -> Asset:
        """
        Store discovered device as an Asset in PostgreSQL.

        Args:
            device_info: Dictionary with device information

        Returns:
            Created Asset object
        """
        hostname = device_info["hostname"]
        ip_address = device_info["ip_address"]

        # Check if asset already exists
        existing = (
            self.db.query(Asset)
            .filter_by(ip_address=ip_address)
            .first()
        )

        if existing:
            # Update existing asset
            existing.hostname = hostname
            existing.last_scanned = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"Updated existing asset: {hostname} ({ip_address})")
            return existing

        # Create new asset
        open_ports = [p for p in device_info["ports"] if p["state"] == "open"]
        device_type = self._infer_device_type(
            hostname, open_ports, ip_address
        )
        vendor = self._infer_vendor(hostname, ip_address)

        asset = Asset(
            asset_id=uuid4(),
            hostname=hostname,
            ip_address=ip_address,
            mac_address="00:00:00:00:00:00",  # Placeholder - would need ARP for real MAC
            owner="Network Auto-Discovery",
            device_type=device_type,
            hardware_vendor=vendor,
            os_info=self._infer_os(device_info["ports"]),
            last_boot_time=datetime.now(timezone.utc),
            criticality_score=self._calculate_criticality(
                device_type, open_ports
            ),
            baseline_state={
                "open_ports": open_ports,
                "discovery_method": "nmap",
            },
            last_scanned=datetime.now(timezone.utc),
        )

        self.db.add(asset)
        self.db.commit()
        logger.info(f"Created new asset: {hostname} ({ip_address})")

        # Log discovery event
        event = Event(
            asset_id=asset.asset_id,
            event_type="ASSET_DISCOVERED",
            severity="INFO",
            details={
                "method": "network_scan",
                "discovered_ports": open_ports,
            },
        )
        self.db.add(event)
        self.db.commit()

        return asset

    def _infer_device_type(
        self, hostname: str, ports: list, ip: str
    ) -> str:
        """Infer device type from hostname and open ports."""
        hostname_lower = hostname.lower()

        if any(
            keyword in hostname_lower
            for keyword in ["switch", "router", "gateway", "fw"]
        ):
            return "Network Device"
        if any(
            keyword in hostname_lower
            for keyword in ["server", "srv", "db", "web"]
        ):
            return "Server"
        if any(
            keyword in hostname_lower
            for keyword in ["printer", "scanner"]
        ):
            return "Printer"

        # Infer from ports
        port_numbers = [p["port"] for p in ports]
        if 3389 in port_numbers:
            return "Workstation"
        if 22 in port_numbers:
            return "Server"
        if 80 in port_numbers or 443 in port_numbers:
            return "Web Server"

        return "Unknown Device"

    @staticmethod
    def _infer_vendor(hostname: str, ip: str) -> str:
        """Infer hardware vendor from hostname or IP."""
        hostname_lower = hostname.lower()

        vendors = {
            "dell": "Dell",
            "hp": "HP",
            "lenovo": "Lenovo",
            "cisco": "Cisco",
            "tp-link": "TP-Link",
            "netgear": "Netgear",
        }

        for key, vendor in vendors.items():
            if key in hostname_lower:
                return vendor

        return "Unknown Vendor"

    @staticmethod
    def _infer_os(ports: list) -> str:
        """Infer OS from open ports and habits."""
        port_numbers = [p["port"] for p in ports]

        if 3389 in port_numbers:
            return "Windows (inferred)"
        if 22 in port_numbers:
            return "Linux/Unix (inferred)"

        return "Unknown OS"

    @staticmethod
    def _calculate_criticality(device_type: str, open_ports: list) -> int:
        """Calculate criticality score (1-10)."""
        score = 5  # Base score

        if device_type == "Server":
            score += 3
        elif device_type == "Network Device":
            score += 2

        if len(open_ports) > 5:
            score += 2
        elif len(open_ports) > 2:
            score += 1

        return min(10, score)

    def close(self):
        """Close database connection."""
        self.db.close()


class ScanWorker:
    """Redis-based worker for processing scan tasks."""

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = redis.Redis(
            host=redis_host, port=redis_port, decode_responses=True
        )
        self.scanner = NetworkScanner()
        self.queue_key = "scan_tasks"
        self.result_key = "scan_results"

    def start(self):
        """Start the worker listening for tasks."""
        logger.info("Scanner worker started. Listening for tasks...")

        try:
            while True:
                # Block and wait for a task
                task_data = self.redis_client.blpop(self.queue_key, timeout=30)

                if task_data:
                    _, task_json = task_data
                    task = json.loads(task_json)
                    self._process_task(task)

        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
        finally:
            self.scanner.close()

    def _process_task(self, task: dict):
        """Process a scan task."""
        try:
            task_id = task.get("id", str(uuid4()))
            network_range = task.get("network_range")

            logger.info(
                f"Processing task {task_id}: scan {network_range}"
            )

            if not network_range:
                raise ValueError("network_range not provided")

            # Perform scan
            discovered = self.scanner.scan_network(network_range)

            # Store results
            stored_assets = []
            failed_hosts = []
            
            for ip, device_info in discovered.items():
                try:
                    asset = self.scanner.store_asset(device_info)
                    stored_assets.append(
                        {
                            "asset_id": str(asset.asset_id),
                            "hostname": asset.hostname,
                            "ip_address": str(asset.ip_address),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to store asset for {ip}: {str(e)}")
                    failed_hosts.append({"ip": str(ip), "error": str(e)})

            # Store result in Redis
            result = {
                "task_id": task_id,
                "status": "completed" if stored_assets else "partial",
                "network_range": network_range,
                "discovered_count": len(discovered),
                "stored_assets": stored_assets,
                "failed_hosts": failed_hosts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self.redis_client.set(
                f"{self.result_key}:{task_id}",
                json.dumps(result),
                ex=3600,
            )
            
            if failed_hosts:
                logger.warning(f"Task {task_id} completed with {len(failed_hosts)} failures")
            else:
                logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task failed: {e}", exc_info=True)
            result = {
                "task_id": task_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.redis_client.set(
                f"{self.result_key}:{task_id}", json.dumps(result), ex=3600
            )

    def submit_scan(self, network_range: str) -> str:
        """
        Submit a network scan task.

        Args:
            network_range: CIDR notation (e.g., "10.0.0.0/24")

        Returns:
            Task ID
        """
        task_id = str(uuid4())
        task = {
            "id": task_id,
            "network_range": network_range,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.redis_client.rpush(self.queue_key, json.dumps(task))
        logger.info(f"Submitted scan task {task_id} for {network_range}")

        return task_id

    def get_result(self, task_id: str) -> dict:
        """Get result of a scan task."""
        result_json = self.redis_client.get(f"{self.result_key}:{task_id}")
        if result_json:
            return json.loads(result_json)
        return None


def initialize_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


if __name__ == "__main__":
    # Check if nmap is installed
    nmap_path = which("nmap")
    
    if not nmap_path:
        # On Windows, nmap might be installed but not in PATH, try common locations
        if sys.platform == "win32":
            common_paths = [
                "C:\\Program Files\\Nmap\\nmap.exe",
                "C:\\Program Files (x86)\\Nmap\\nmap.exe",
            ]
            for path in common_paths:
                if subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    timeout=5,
                ).returncode == 0:
                    nmap_path = path
                    logger.info(f"Found nmap at: {nmap_path}")
                    break
    
    if not nmap_path:
        logger.error("nmap is not installed. Please install it:")
        logger.error("  Windows: choco install nmap")
        logger.error("  macOS: brew install nmap")
        logger.error("  Linux: sudo apt-get install nmap")
        sys.exit(1)
    
    logger.info(f"Using nmap from: {nmap_path}")
    initialize_db()
    worker = ScanWorker()
    worker.start()
