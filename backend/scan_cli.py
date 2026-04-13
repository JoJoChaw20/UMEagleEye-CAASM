"""
CLI utility for triggering and monitoring network scans.
Usage: python -m backend.scan_cli <network_range>
       python -m backend.scan_cli --auto
       python -m backend.scan_cli --auto-all
       python -m backend.scan_cli --list-networks
Example: python -m backend.scan_cli 192.168.1.0/24

        # Scan modes: basic (ping sweep), standard (ping + port scan), aggressive (full scan)
        SCAN_MODES = {
            "basic": {"desc": "Ping sweep only", "args": "-sn"},
            "standard": {"desc": "Ping sweep + top 1000 ports", "args": "-p- -sV"},
            "aggressive": {"desc": "Full scan with OS detection", "args": "-p- -sV -O -A"}
        }
         python -m backend.scan_cli --auto
         python -m backend.scan_cli --auto-all
"""

import json
import socket
import subprocess
import sys
import time
import platform
import re
from ipaddress import IPv4Address, IPv4Network
from typing import Optional

import redis

from backend.scanner_worker import ScanWorker


def get_local_networks() -> list:
    """
    Detect local network interfaces and their CIDR ranges.
    Uses system commands (ipconfig on Windows, ifconfig on Linux/Mac).
    
    Returns:
        List of dicts: {"ip": ip_address, "network": network_range_cidr}
    """
    networks = []
    system = platform.system()
    
    try:
        if system == "Windows":
            # Use ipconfig on Windows
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            
            # Parse IPv4 addresses from ipconfig output
            # Look for lines with "IPv4 Address" that don't contain "169.254" (APIPA)
            for line in output.split('\n'):
                if 'IPv4 Address' in line and ':' in line:
                    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if ip_match:
                        ip = ip_match.group(1)
                        
                        # Skip loopback and APIPA addresses
                        if ip.startswith("127.") or ip.startswith("169.254"):
                            continue
                        
                        # Assume /24 subnet for typical local networks
                        try:
                            network_obj = IPv4Network(f"{ip}/24", strict=False)
                            networks.append({
                                "ip": ip,
                                "network": str(network_obj)
                            })
                        except:
                            pass
        
        else:
            # Use ifconfig on Linux/Mac
            result = subprocess.run(
                ["ifconfig"] if system == "Darwin" else ["ip", "addr"],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            
            # Parse IP addresses
            if system == "Darwin":
                # macOS ifconfig format
                for line in output.split('\n'):
                    if 'inet ' in line and 'inet6' not in line:
                        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            
                            if ip.startswith("127.") or ip.startswith("169.254"):
                                continue
                            
                            try:
                                network_obj = IPv4Network(f"{ip}/24", strict=False)
                                networks.append({
                                    "ip": ip,
                                    "network": str(network_obj)
                                })
                            except:
                                pass
            else:
                # Linux ip addr format
                for line in output.split('\n'):
                    if 'inet ' in line and 'inet6' not in line:
                        # Format: inet 192.168.1.100/24 brd ...
                        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            subnet = ip_match.group(2)
                            
                            if ip.startswith("127.") or ip.startswith("169.254"):
                                continue
                            
                            try:
                                network_obj = IPv4Network(f"{ip}/{subnet}", strict=False)
                                networks.append({
                                    "ip": ip,
                                    "network": str(network_obj)
                                })
                            except:
                                pass
        
        # Remove duplicates while preserving order
        seen = set()
        unique_networks = []
        for net in networks:
            if net["network"] not in seen:
                seen.add(net["network"])
                unique_networks.append(net)
        
        return unique_networks
    
    except subprocess.TimeoutExpired:
        print("Warning: Network detection timed out")
        return []
    except Exception as e:
        print(f"Warning: Error detecting local networks: {e}")
        return []


def list_networks() -> None:
    """Display available local networks for scanning."""
    networks = get_local_networks()
    
    if not networks:
        print("Could not auto-detect local networks.")
        print("\nTo find your network range:")
        print("  Windows: ipconfig - look for 'IPv4 Address'")
        print("  Linux/Mac: ifconfig or ip addr - look for 'inet'")
        print("\nUsage: python -m backend.scan_cli <network_range>")
        print("Example: python -m backend.scan_cli 192.168.1.0/24")
        return
    
    print("📡 Detected Local Networks:\n")
    for i, net in enumerate(networks, 1):
        print(f"  {i}. {net['network']}")
        print(f"     (Your IP: {net['ip']})")
    
    print("\n💡 Use any of these ranges with:")
    print("   python -m backend.scan_cli <network_range>")
    print("\nOr scan all automatically:")
    print("   python -m backend.scan_cli --auto")


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
        print("       python -m backend.scan_cli --auto")
        print("       python -m backend.scan_cli --auto-all")
        print("       python -m backend.scan_cli --list-networks")
        print("\nExamples:")
        print("  python -m backend.scan_cli 10.0.0.0/24")
        print("  python -m backend.scan_cli 192.168.1.0/24")
        print("  python -m backend.scan_cli --auto          (scan primary network)")
        print("  python -m backend.scan_cli --auto-all       (scan all local networks)")
        print("  python -m backend.scan_cli --list-networks (show available networks)")
        sys.exit(1)

    command = sys.argv[1]
    
    # Handle --list-networks flag
    if command == "--list-networks":
        list_networks()
        sys.exit(0)
    
    # Handle --auto-all flag
    if command == "--auto-all":
        networks = get_local_networks()
        if not networks:
            print("✗ Could not auto-detect local networks")
            print("\nPlease use:")
            print("  python -m backend.scan_cli --list-networks")
            print("  python -m backend.scan_cli <network_range>")
            sys.exit(1)
        
        print(f"🔍 Found {len(networks)} local network(s). Scanning all...\n")
        
        total_assets = 0
        for i, net in enumerate(networks, 1):
            network_range = net["network"]
            print(f"📡 Scan {i}/{len(networks)}: {network_range}")
            print("-" * 60)
            
            try:
                worker = ScanWorker()
            except redis.ConnectionError:
                print("Error: Cannot connect to Redis. Is Redis running?")
                sys.exit(1)

            task_id = worker.submit_scan(network_range)
            print(f"   Task ID: {task_id}")
            
            # Monitor until completion
            max_wait = 300  # 5 minutes per scan
            start_time = time.time()

            while time.time() - start_time < max_wait:
                result = worker.get_result(task_id)

                if result:
                    status = result.get("status")

                    if status == "completed" or status == "partial":
                        assets_count = len(result.get('stored_assets', []))
                        total_assets += assets_count
                        
                        print(f"   ✓ Completed: {result.get('discovered_count')} hosts, {assets_count} assets stored")
                        
                        if result.get("stored_assets"):
                            for asset in result["stored_assets"]:
                                print(f"     - {asset['hostname']} ({asset['ip_address']})")
                        break

                    elif status == "failed":
                        print(f"   ✗ Scan failed: {result.get('error')}")
                        break

                time.sleep(2)
            
            print()
        
        print(f"\n✓ All scans completed! Total assets discovered: {total_assets}")
        sys.exit(0)
    
    # Handle --auto flag
    if command == "--auto":
        networks = get_local_networks()
        if not networks:
            print("✗ Could not auto-detect local network")
            print("\nPlease use:")
            print("  python -m backend.scan_cli --list-networks")
            print("  python -m backend.scan_cli <network_range>")
            sys.exit(1)
        
        # Scan the first detected network
        network_range = networks[0]["network"]
        print(f"🔍 Auto-detected network: {network_range}")
        submit_and_monitor(network_range)
    else:
        # Manual network range provided
        network_range = command
        submit_and_monitor(network_range)
