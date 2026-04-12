"""
CLI utility for triggering and monitoring network scans.
Usage: python -m backend.scan_cli <network_range>
Example: python -m backend.scan_cli 192.168.1.0/24
"""

import json
import sys
import time
from typing import Optional

import redis

from backend.scanner_worker import ScanWorker


def submit_and_monitor(network_range: str) -> None:
    """
    Submit a scan and monitor progress.

    Args:
        network_range: Network in CIDR notation
    """
    try:
        worker = ScanWorker()
    except redis.ConnectionError:
        print("Error: Cannot connect to Redis. Is Redis running?")
        print("Start Redis with: redis-server")
        sys.exit(1)

    print(f"📡 Submitting scan for {network_range}...")
    task_id = worker.submit_scan(network_range)
    print(f"✓ Task ID: {task_id}")
    print("⏳ Scanning network (this may take a moment)...\n")

    # Monitor until completion
    max_wait = 300  # 5 minutes
    start_time = time.time()

    while time.time() - start_time < max_wait:
        result = worker.get_result(task_id)

        if result:
            status = result.get("status")

            if status == "completed" or status == "partial":
                print("✓ Scan completed!\n")
                print(f"  Network: {result.get('network_range')}")
                print(f"  Total hosts discovered: {result.get('discovered_count')}")
                print(f"  Assets stored: {len(result.get('stored_assets', []))}")

                if result.get("failed_hosts"):
                    print(f"  Failed hosts: {len(result.get('failed_hosts'))}")
                    for failed in result.get("failed_hosts", []):
                        print(f"    - {failed.get('ip')}: {failed.get('error')}")

                if result.get("stored_assets"):
                    print("\n  Discovered assets:")
                    for asset in result["stored_assets"]:
                        print(f"    - {asset['hostname']} ({asset['ip_address']})")

                return

            elif status == "failed":
                print(f"✗ Scan failed: {result.get('error')}")
                sys.exit(1)

        time.sleep(2)

    print("✗ Scan timed out")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m backend.scan_cli <network_range>")
        print("Example: python -m backend.scan_cli 10.0.0.0/24")
        sys.exit(1)

    network_range = sys.argv[1]
    submit_and_monitor(network_range)
