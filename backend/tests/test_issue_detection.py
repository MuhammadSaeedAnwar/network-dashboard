from app.services.issue_detection import alerts_from_health_checks, alerts_from_scan
from app.services.network_checks import CheckResult
from app.services.nmap_scanner import ParsedPort


def test_no_alerts_for_healthy_checks():
    results = [
        CheckResult("dns", "example.com", True, "ok", "resolved", 5.0),
        CheckResult("ping", "example.com", True, "ok", "reachable", 20.0),
    ]
    assert alerts_from_health_checks(results, latency_warning_ms=150) == []


def test_alert_for_dns_failure():
    results = [CheckResult("dns", "bad.invalid", False, "critical", "failed", None)]
    drafts = alerts_from_health_checks(results, latency_warning_ms=150)
    assert len(drafts) == 1
    assert drafts[0].severity == "critical"
    assert "DNS" in drafts[0].message


def test_alert_for_unreachable_host():
    results = [CheckResult("ping", "10.0.0.5", False, "critical", "unreachable", None)]
    drafts = alerts_from_health_checks(results, latency_warning_ms=150)
    assert len(drafts) == 1
    assert "unreachable" in drafts[0].message


def test_alert_for_high_latency():
    results = [CheckResult("ping", "10.0.0.5", True, "ok", "reachable", 300.0)]
    drafts = alerts_from_health_checks(results, latency_warning_ms=150)
    assert len(drafts) == 1
    assert drafts[0].severity == "warning"
    assert "latency" in drafts[0].message.lower()


def test_no_latency_alert_under_threshold():
    results = [CheckResult("ping", "10.0.0.5", True, "ok", "reachable", 50.0)]
    assert alerts_from_health_checks(results, latency_warning_ms=150) == []


def test_alert_for_http_failure():
    results = [CheckResult("http", "https://example.com", False, "critical", "connection refused", None)]
    drafts = alerts_from_health_checks(results, latency_warning_ms=150)
    assert len(drafts) == 1
    assert "HTTP" in drafts[0].message


def test_no_scan_alerts_without_expected_ports_baseline():
    ports = [ParsedPort(22, "tcp", "open", "ssh", None, None)]
    assert alerts_from_scan(ports, expected_ports=None) == []


def test_scan_alert_for_missing_expected_port():
    ports = [ParsedPort(80, "tcp", "open", "http", None, None)]
    drafts = alerts_from_scan(ports, expected_ports=[22, 80])
    assert len(drafts) == 1
    assert "22" in drafts[0].message
    assert drafts[0].severity == "critical"


def test_scan_alert_for_unexpected_open_port():
    ports = [
        ParsedPort(22, "tcp", "open", "ssh", None, None),
        ParsedPort(3389, "tcp", "open", "ms-wbt-server", None, None),
    ]
    drafts = alerts_from_scan(ports, expected_ports=[22])
    assert len(drafts) == 1
    assert "3389" in drafts[0].message
    assert drafts[0].severity == "warning"


def test_no_alerts_when_scan_matches_expected_exactly():
    ports = [ParsedPort(22, "tcp", "open", "ssh", None, None), ParsedPort(80, "tcp", "open", "http", None, None)]
    assert alerts_from_scan(ports, expected_ports=[22, 80]) == []
