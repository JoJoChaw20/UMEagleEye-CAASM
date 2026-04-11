from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.database import SessionLocal, engine
from backend.models import Advisory, Asset, Base, Event, NetworkConnection, PostureMetric, Sbom


def seed_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    assets = [
        Asset(
            hostname="web-01",
            ip_address="10.0.10.11",
            mac_address="08:00:27:aa:10:11",
            owner="Platform Team",
            device_type="Server",
            hardware_vendor="Dell",
            os_info="Ubuntu 22.04 LTS",
            last_boot_time=now - timedelta(hours=7),
            criticality_score=9,
            baseline_state={"allowed_ports": [80, 443], "ssh": {"enabled": True}, "packages": ["apache2", "openssh-server"]},
            last_scanned=now - timedelta(hours=1),
        ),
        Asset(
            hostname="ws-01",
            ip_address="10.0.20.21",
            mac_address="08:00:27:bb:20:21",
            owner="Finance User",
            device_type="Workstation",
            hardware_vendor="HP",
            os_info="Windows 11 Enterprise",
            last_boot_time=now - timedelta(hours=5),
            criticality_score=5,
            baseline_state={"allowed_ports": [135, 139, 445], "defender": {"real_time_protection": True}},
            last_scanned=now - timedelta(hours=2),
        ),
        Asset(
            hostname="switch-01",
            ip_address="10.0.1.2",
            mac_address="08:00:27:cc:01:02",
            owner="Network Ops",
            device_type="Switch",
            hardware_vendor="TP-Link",
            os_info="TP-Link Omada Firmware 1.2",
            last_boot_time=now - timedelta(days=3),
            criticality_score=8,
            baseline_state={"vlans": [10, 20, 99], "management_access": "restricted"},
            last_scanned=now - timedelta(hours=3),
        ),
        Asset(
            hostname="db-01",
            ip_address="10.0.10.12",
            mac_address="08:00:27:dd:10:12",
            owner="Data Team",
            device_type="Server",
            hardware_vendor="Lenovo",
            os_info="Ubuntu 22.04 LTS",
            last_boot_time=now - timedelta(hours=12),
            criticality_score=10,
            baseline_state={"allowed_ports": [5432], "postgres": {"ssl": True}},
            last_scanned=now - timedelta(minutes=50),
        ),
        Asset(
            hostname="fw-01",
            ip_address="10.0.0.1",
            mac_address="08:00:27:ee:00:01",
            owner="Security Team",
            device_type="Appliance",
            hardware_vendor="Cisco",
            os_info="Cisco Secure Firewall",
            last_boot_time=now - timedelta(days=7),
            criticality_score=10,
            baseline_state={"allowed_ports": [22, 443], "wan_policy": "deny by default"},
            last_scanned=now - timedelta(minutes=30),
        ),
    ]

    with SessionLocal() as session:
        session.add_all(assets)
        session.commit()

        asset_map = {asset.hostname: asset for asset in assets}

        connections = [
            NetworkConnection(
                source_asset_id=asset_map["web-01"].asset_id,
                target_asset_id=asset_map["switch-01"].asset_id,
                connection_method="Layer_2_Switchport",
                detected_at=now,
            ),
            NetworkConnection(
                source_asset_id=asset_map["ws-01"].asset_id,
                target_asset_id=asset_map["switch-01"].asset_id,
                connection_method="Layer_2_Switchport",
                detected_at=now,
            ),
            NetworkConnection(
                source_asset_id=asset_map["db-01"].asset_id,
                target_asset_id=asset_map["switch-01"].asset_id,
                connection_method="Layer_2_Switchport",
                detected_at=now,
            ),
            NetworkConnection(
                source_asset_id=asset_map["switch-01"].asset_id,
                target_asset_id=asset_map["fw-01"].asset_id,
                connection_method="Routed_Hop",
                detected_at=now,
            ),
        ]
        session.add_all(connections)

        sboms = [
            Sbom(
                asset_id=asset_map["web-01"].asset_id,
                raw_data={
                    "packages": [
                        {"name": "apache2", "version": "2.4.58", "deps": ["libapr1", "libpcre2-8-0"]},
                        {"name": "openssh-server", "version": "9.6p1"},
                    ],
                    "os": "Ubuntu 22.04 LTS",
                },
                generated_at=now,
            ),
            Sbom(
                asset_id=asset_map["ws-01"].asset_id,
                raw_data={
                    "packages": [
                        {"name": "microsoft-edge", "version": "124.0.2478.51"},
                        {"name": "7zip", "version": "24.05"},
                    ],
                    "os": "Windows 11 Enterprise",
                },
                generated_at=now,
            ),
        ]
        session.add_all(sboms)

        events = [
            Event(
                asset_id=asset_map["web-01"].asset_id,
                event_type="port_opened",
                severity="Medium",
                details={"port": 22, "protocol": "tcp", "evidence": "ssh listener detected outside baseline"},
                timestamp=now,
            ),
            Event(
                asset_id=asset_map["web-01"].asset_id,
                event_type="version_downgrade",
                severity="High",
                details={"package": "apache2", "expected": "2.4.58", "observed": "2.4.54"},
                timestamp=now - timedelta(hours=2),
            ),
            Event(
                asset_id=asset_map["ws-01"].asset_id,
                event_type="cve_detected",
                severity="Critical",
                details={"cve": "CVE-2025-12345", "package": "7zip", "status": "exploitable"},
                timestamp=now - timedelta(hours=3),
            ),
            Event(
                asset_id=asset_map["db-01"].asset_id,
                event_type="config_drift",
                severity="High",
                details={"setting": "ssl", "expected": True, "observed": False},
                timestamp=now - timedelta(hours=4),
            ),
            Event(
                asset_id=asset_map["switch-01"].asset_id,
                event_type="unauthorized_vlan",
                severity="Medium",
                details={"vlan": 300, "status": "unexpected on trunk"},
                timestamp=now - timedelta(hours=5),
            ),
            Event(
                asset_id=asset_map["fw-01"].asset_id,
                event_type="firmware_outdated",
                severity="High",
                details={"expected": "Cisco Secure Firewall 7.4", "observed": "Cisco Secure Firewall 7.1"},
                timestamp=now - timedelta(hours=6),
            ),
        ]
        session.add_all(events)
        session.flush()

        advisory = Advisory(
            event_id=events[0].event_id,
            summary="An unexpected SSH service is exposed on the web server.",
            recommended_action="1. Disable the unauthorized SSH listener. 2. Remove the port from host firewall rules. 3. Re-scan the asset to confirm the baseline matches.",
            status="Open",
            created_at=now,
        )
        session.add(advisory)

        metrics = [
            PostureMetric(
                overall_score=85,
                total_critical_assets=2,
                top_risks=["Outdated package on web-01", "Weak segmentation around workstation subnet"],
                timestamp=yesterday,
            ),
            PostureMetric(
                overall_score=70,
                total_critical_assets=3,
                top_risks=["Unauthorized SSH exposure on web-01", "Critical CVE on ws-01", "SSL disabled on db-01"],
                timestamp=now,
            ),
        ]
        session.add_all(metrics)

        session.commit()

    print("Seed complete: 5 assets, 4 connections, 2 SBOMs, 6 events, 1 advisory, 2 posture metrics.")


if __name__ == "__main__":
    seed_database()
