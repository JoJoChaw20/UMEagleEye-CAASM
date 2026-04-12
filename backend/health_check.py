"""
Health check script to verify all components are ready.
"""

import sys
import subprocess
from pathlib import Path


def check_nmap():
    """Check if nmap is installed."""
    try:
        subprocess.run(
            ["nmap", "--version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        return True, "✓ nmap is installed"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "✗ nmap is NOT installed"


def check_docker():
    """Check if Docker is running."""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        output = result.stdout.decode()
        if "postgres" in output and "redis" in output:
            return True, "✓ Docker Compose is running (postgres + redis)"
        else:
            return False, "✗ Docker Compose missing postgres or redis"
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False, "✗ Docker is NOT running"


def check_python_packages():
    """Check if required Python packages are installed."""
    required = ["redis", "nmap", "fastapi", "sqlalchemy", "psycopg"]
    missing = []

    for package in required:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)

    if not missing:
        return True, f"✓ All {len(required)} required packages installed"
    else:
        return False, f"✗ Missing packages: {', '.join(missing)}"


def check_postgresql():
    """Check if PostgreSQL is accessible."""
    try:
        import psycopg
        
        # Connect directly without importing database module
        conn = psycopg.connect(
            "postgresql://umeagleeye_admin:S4cr3tP8ssw0rd@localhost:5432/umeagleeye_db",
            connect_timeout=5
        )
        conn.close()
        return True, "✓ PostgreSQL is accessible"
    except Exception as e:
        return False, f"✗ PostgreSQL NOT accessible: {str(e)[:50]}"


def check_redis():
    """Check if Redis is accessible."""
    try:
        import redis

        r = redis.Redis(
            host="localhost", port=6379, decode_responses=True, socket_connect_timeout=5
        )
        r.ping()
        return True, "✓ Redis is accessible"
    except Exception as e:
        return False, f"✗ Redis NOT accessible: {str(e)[:50]}"


def main():
    """Run all checks."""
    print("\n" + "=" * 60)
    print("UMEagleEye Network Scanner - Health Check")
    print("=" * 60 + "\n")

    checks = [
        ("nmap Installation", check_nmap),
        ("Docker Containers", check_docker),
        ("Python Packages", check_python_packages),
        ("PostgreSQL Connection", check_postgresql),
        ("Redis Connection", check_redis),
    ]

    results = []
    for name, check_fn in checks:
        try:
            passed, message = check_fn()
            results.append((passed, message))
            print(f"{name:.<40} {message}")
        except Exception as e:
            results.append((False, str(e)))
            print(f"{name:.<40} ✗ Error: {str(e)[:40]}")

    print("\n" + "=" * 60)

    passed_count = sum(1 for p, _ in results if p)
    total_count = len(results)

    if passed_count == total_count:
        print(f"✓ All checks passed ({passed_count}/{total_count})\n")
        print("Next steps:")
        print("  1. Terminal 1: python -m backend.scanner_worker")
        print("  2. Terminal 2: python -m uvicorn backend.main:app --reload")
        print("  3. Terminal 3: cd frontend && npm run dev")
        print("  4. Browser: http://localhost:5173\n")
        return 0
    else:
        print(f"✗ {total_count - passed_count} checks failed ({passed_count}/{total_count})\n")
        print("Failed checks:")
        for passed, message in results:
            if not passed:
                print(f"  - {message}")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
