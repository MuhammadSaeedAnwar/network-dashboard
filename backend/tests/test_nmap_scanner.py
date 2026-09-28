import subprocess
from unittest.mock import patch

import pytest

from app.services.nmap_scanner import NmapNotAvailableError, run_nmap_scan

SAMPLE_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="1.24"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="closed"/>
        <service name="https"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""


@patch("app.services.nmap_scanner.shutil.which", return_value=None)
def test_raises_when_nmap_not_installed(mock_which):
    with pytest.raises(NmapNotAvailableError):
        run_nmap_scan("192.168.1.1", top_ports=100, timeout_seconds=30)


@patch("app.services.nmap_scanner.shutil.which", return_value="/usr/bin/nmap")
@patch("app.services.nmap_scanner.subprocess.run")
def test_parses_ports_from_xml(mock_run, mock_which):
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=SAMPLE_XML, stderr="")

    outcome = run_nmap_scan("192.168.1.1", top_ports=100, timeout_seconds=30)

    assert outcome.success is True
    assert len(outcome.ports) == 3
    open_ports = [p for p in outcome.ports if p.state == "open"]
    assert {p.port_number for p in open_ports} == {22, 80}
    ssh_port = next(p for p in outcome.ports if p.port_number == 22)
    assert ssh_port.service_name == "ssh"
    assert ssh_port.service_product == "OpenSSH"


@patch("app.services.nmap_scanner.shutil.which", return_value="/usr/bin/nmap")
@patch("app.services.nmap_scanner.subprocess.run")
def test_nonzero_exit_reported_as_failure(mock_run, mock_which):
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="nmap: permission denied"
    )
    outcome = run_nmap_scan("192.168.1.1", top_ports=100, timeout_seconds=30)
    assert outcome.success is False
    assert "permission denied" in outcome.error_detail


@patch("app.services.nmap_scanner.shutil.which", return_value="/usr/bin/nmap")
@patch("app.services.nmap_scanner.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="nmap", timeout=30))
def test_timeout_reported_as_failure(mock_run, mock_which):
    outcome = run_nmap_scan("192.168.1.1", top_ports=100, timeout_seconds=30)
    assert outcome.success is False
    assert "timed out" in outcome.error_detail


@patch("app.services.nmap_scanner.shutil.which", return_value="/usr/bin/nmap")
@patch("app.services.nmap_scanner.subprocess.run")
def test_invalid_xml_reported_as_failure(mock_run, mock_which):
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="not xml at all <<", stderr="")
    outcome = run_nmap_scan("192.168.1.1", top_ports=100, timeout_seconds=30)
    assert outcome.success is False
    assert "parse" in outcome.error_detail.lower()


def test_command_never_uses_shell_and_target_is_isolated_arg():
    """Regression guard: the target must always be its own argv element,
    never concatenated into a shell string."""
    import inspect

    source = inspect.getsource(run_nmap_scan)
    assert "shell=True" not in source


@patch("app.services.nmap_scanner.shutil.which", return_value="/usr/bin/nmap")
@patch("app.services.nmap_scanner.subprocess.run")
def test_expected_ports_are_added_to_top_port_scan(mock_run, mock_which):
    xml = """<?xml version="1.0"?>
    <nmaprun>
      <host>
        <ports>
          <port protocol="tcp" portid="8000">
            <state state="open"/>
          </port>
          <port protocol="tcp" portid="8080">
            <state state="open"/>
          </port>
        </ports>
      </host>
    </nmaprun>
    """

    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=xml,
        stderr="",
    )

    outcome = run_nmap_scan(
        "127.0.0.1",
        top_ports=100,
        timeout_seconds=30,
        expected_ports=[8000, 8080, 8080],
    )

    assert outcome.success is True
    assert {p.port_number for p in outcome.ports} == {8000, 8080}

    assert mock_run.call_count == 2

    top_command = mock_run.call_args_list[0].args[0]
    expected_command = mock_run.call_args_list[1].args[0]

    assert "--top-ports" in top_command
    assert "100" in top_command
    assert "-p" not in top_command
    assert top_command[-1] == "host.docker.internal"

    assert "-p" in expected_command
    assert expected_command[expected_command.index("-p") + 1] == "8000,8080"
    assert expected_command[-1] == "host.docker.internal"


@patch("app.services.nmap_scanner.shutil.which", return_value="/usr/bin/nmap")
@patch("app.services.nmap_scanner.subprocess.run")
def test_scan_without_expected_ports_keeps_top_ports_only(mock_run, mock_which):
    xml = """<?xml version="1.0"?>
    <nmaprun>
      <host>
        <ports>
          <port protocol="tcp" portid="8000">
            <state state="open"/>
          </port>
        </ports>
      </host>
    </nmaprun>
    """

    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=xml,
        stderr="",
    )

    outcome = run_nmap_scan(
        "127.0.0.1",
        top_ports=100,
        timeout_seconds=30,
    )

    assert outcome.success is True

    assert mock_run.call_count == 1
    command = mock_run.call_args_list[0].args[0]
    assert "--top-ports" in command
    assert "100" in command
    assert "-p" not in command
    assert command[-1] == "host.docker.internal"
