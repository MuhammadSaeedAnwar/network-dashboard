import socket
import subprocess
from unittest.mock import MagicMock, patch

from app.services.network_checks import (
    check_dns,
    check_http,
    check_ping,
    check_tcp_port,
)


@patch("app.services.network_checks.socket.gethostbyname", return_value="93.184.216.34")
def test_dns_success(mock_resolve):
    result = check_dns("example.com")
    assert result.success is True
    assert result.status == "ok"


@patch("app.services.network_checks.socket.gethostbyname", side_effect=socket.gaierror("nope"))
def test_dns_failure(mock_resolve):
    result = check_dns("nonexistent.invalid")
    assert result.success is False
    assert result.status == "critical"


@patch("app.services.network_checks.shutil.which", return_value="/bin/ping")
@patch("app.services.network_checks.subprocess.run")
def test_ping_success(mock_run, mock_which):
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="rtt min/avg/max/mdev = 10.0/12.5/15.0/1.0 ms", stderr=""
    )
    result = check_ping("8.8.8.8")
    assert result.success is True
    assert result.latency_ms == 12.5


@patch("app.services.network_checks.shutil.which", return_value=None)
def test_ping_unknown_when_binary_missing(mock_which):
    result = check_ping("8.8.8.8")
    assert result.status == "unknown"


@patch("app.services.network_checks.socket.create_connection")
def test_tcp_port_success(mock_conn):
    mock_conn.return_value.__enter__.return_value = MagicMock()
    result = check_tcp_port("localhost", 80)
    assert result.success is True


@patch("app.services.network_checks.socket.create_connection", side_effect=ConnectionRefusedError)
def test_tcp_port_refused(mock_conn):
    result = check_tcp_port("localhost", 9999)
    assert result.success is False
    assert result.status == "critical"


@patch("app.services.network_checks.urllib.request.urlopen")
def test_http_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response
    result = check_http("https://example.com")
    assert result.success is True


@patch("app.services.network_checks.urllib.request.urlopen")
def test_http_unexpected_status(mock_urlopen):
    mock_response = MagicMock()
    mock_response.getcode.return_value = 500
    mock_urlopen.return_value.__enter__.return_value = mock_response
    result = check_http("https://example.com")
    assert result.success is False
    assert result.status == "warning"
