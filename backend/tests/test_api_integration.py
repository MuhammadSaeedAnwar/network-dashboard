from unittest.mock import patch

from app.services.network_checks import CheckResult
from app.services.nmap_scanner import NmapNotAvailableError, ParsedPort, ScanOutcome
from tests.conftest import AUTHORIZED_HOST_PAYLOAD


# ---------- Hosts ----------

def test_create_host_requires_authorization_confirmation(client):
    payload = {**AUTHORIZED_HOST_PAYLOAD, "authorized_confirmation": False}
    resp = client.post("/api/hosts", json=payload)
    assert resp.status_code == 422


def test_create_host_rejects_cidr_target(client):
    payload = {**AUTHORIZED_HOST_PAYLOAD, "address": "10.0.0.0/24"}
    resp = client.post("/api/hosts", json=payload)
    assert resp.status_code == 422


def test_create_host_success(client):
    resp = client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["authorized"] is True
    assert body["address"] == AUTHORIZED_HOST_PAYLOAD["address"]


def test_list_hosts_includes_summary_fields(client):
    client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD)
    resp = client.get("/api/hosts")
    assert resp.status_code == 200
    hosts = resp.json()
    assert len(hosts) == 1
    assert hosts[0]["latest_status"] == "unknown"
    assert hosts[0]["open_alert_count"] == 0


def test_get_missing_host_404(client):
    resp = client.get("/api/hosts/999")
    assert resp.status_code == 404


def test_delete_host(client):
    created = client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD).json()
    resp = client.delete(f"/api/hosts/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/hosts/{created['id']}").status_code == 404


# ---------- Checks ----------

@patch("app.routers.checks.run_standard_checks")
def test_run_checks_stores_results_and_raises_alerts(mock_run_checks, client):
    host = client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD).json()
    mock_run_checks.return_value = [
        CheckResult("dns", "192.168.1.1", True, "ok", "resolved", 2.0),
        CheckResult("ping", "192.168.1.1", False, "critical", "unreachable", None),
    ]

    resp = client.post(f"/api/hosts/{host['id']}/checks/run")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) == 2
    assert body["alerts_raised"] == 1

    alerts_resp = client.get("/api/alerts", params={"host_id": host["id"]})
    assert len(alerts_resp.json()) == 1


def test_run_checks_for_missing_host_404(client):
    resp = client.post("/api/hosts/999/checks/run")
    assert resp.status_code == 404


# ---------- Scans ----------

@patch("app.routers.scans.run_nmap_scan")
def test_create_scan_requires_ack(mock_scan, client):
    host = client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD).json()
    resp = client.post(f"/api/hosts/{host['id']}/scans", json={"authorization_ack": False})
    assert resp.status_code == 422
    mock_scan.assert_not_called()


@patch("app.routers.scans.run_nmap_scan")
def test_create_scan_success_stores_ports(mock_scan, client):
    host = client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD).json()
    mock_scan.return_value = ScanOutcome(
        success=True,
        ports=[
            ParsedPort(22, "tcp", "open", "ssh", "OpenSSH", "8.9"),
            ParsedPort(80, "tcp", "open", "http", "nginx", "1.24"),
        ],
    )

    resp = client.post(f"/api/hosts/{host['id']}/scans", json={"authorization_ack": True, "top_ports": 100})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert len(body["ports"]) == 2


@patch("app.routers.scans.run_nmap_scan", side_effect=NmapNotAvailableError("nmap missing"))
def test_create_scan_when_nmap_missing_marks_failed(mock_scan, client):
    host = client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD).json()
    resp = client.post(f"/api/hosts/{host['id']}/scans", json={"authorization_ack": True})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed"
    assert "nmap missing" in body["error_detail"]


def test_top_ports_is_capped_at_config_max(client):
    """Even if a caller requests an enormous top_ports value, the request
    schema itself rejects anything above 1000."""
    host = client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD).json()
    resp = client.post(f"/api/hosts/{host['id']}/scans", json={"authorization_ack": True, "top_ports": 50000})
    assert resp.status_code == 422


# ---------- Alerts ----------

@patch("app.routers.checks.run_standard_checks")
def test_resolve_alert(mock_run_checks, client):
    host = client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD).json()
    mock_run_checks.return_value = [CheckResult("ping", "192.168.1.1", False, "critical", "unreachable", None)]
    client.post(f"/api/hosts/{host['id']}/checks/run")

    alert = client.get("/api/alerts").json()[0]
    resp = client.post(f"/api/alerts/{alert['id']}/resolve")
    assert resp.status_code == 200
    assert resp.json()["resolved"] is True

    unresolved = client.get("/api/alerts", params={"resolved": False}).json()
    assert len(unresolved) == 0


# ---------- Dashboard ----------

def test_dashboard_summary_reflects_hosts(client):
    client.post("/api/hosts", json=AUTHORIZED_HOST_PAYLOAD)
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_hosts"] == 1
    assert body["hosts_unknown"] == 1
