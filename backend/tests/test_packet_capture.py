import subprocess
from unittest.mock import patch

from app.services.packet_capture import capture_summary


@patch("app.services.packet_capture.shutil.which", return_value=None)
def test_unavailable_when_tshark_missing(mock_which):
    result = capture_summary("192.168.1.1", "any", 5, 200)
    assert result.available is False
    assert "not installed" in result.detail


@patch("app.services.packet_capture.shutil.which", return_value="/usr/bin/tshark")
@patch("app.services.packet_capture.subprocess.run")
def test_parses_protocol_counts(mock_run, mock_which):
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout="eth:ip:tcp\neth:ip:tcp\neth:ip:udp:dns\n",
        stderr="",
    )
    result = capture_summary("192.168.1.1", "eth0", 5, 200)
    assert result.available is True
    assert result.packet_count == 3
    assert result.protocol_counts == {"tcp": 2, "dns": 1}


@patch("app.services.packet_capture.shutil.which", return_value="/usr/bin/tshark")
@patch("app.services.packet_capture.subprocess.run", side_effect=PermissionError)
def test_permission_denied_reported_gracefully(mock_run, mock_which):
    result = capture_summary("192.168.1.1", "eth0", 5, 200)
    assert result.available is False
    assert "Permission" in result.detail
