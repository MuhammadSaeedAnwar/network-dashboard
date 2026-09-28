import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { Alert, Host, HealthCheckResult, Scan } from "../types";
import StatusBadge from "./StatusBadge";
import ScanHistory from "./ScanHistory";
import AlertList from "./AlertList";

interface Props {
  hostId: number;
  onBack: () => void;
}

export default function HostDetail({ hostId, onBack }: Props) {
  const [host, setHost] = useState<Host | null>(null);
  const [checks, setChecks] = useState<HealthCheckResult[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [running, setRunning] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanAck, setScanAck] = useState(false);
  const [topPorts, setTopPorts] = useState(100);
  const [error, setError] = useState<string | null>(null);

  async function loadAll() {
    const [h, c, s, a] = await Promise.all([
      api.getHost(hostId),
      api.listChecks(hostId),
      api.listScans(hostId),
      api.listAlerts({ hostId }),
    ]);
    setHost(h);
    setChecks(c);
    setScans(s);
    setAlerts(a);
  }

  useEffect(() => {
    loadAll().catch(() => setError("Failed to load host details."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hostId]);

  async function handleRunChecks() {
    setRunning(true);
    setError(null);
    try {
      await api.runChecks(hostId);
      await loadAll();
    } catch {
      setError("Failed to run diagnostics.");
    } finally {
      setRunning(false);
    }
  }

  async function handleRunScan() {
    if (!scanAck) {
      setError("You must confirm authorization before running a scan.");
      return;
    }
    setScanning(true);
    setError(null);
    try {
      await api.createScan(hostId, topPorts, scanAck);
      setScanAck(false);
      await loadAll();
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.detail as any;
        setError(Array.isArray(detail?.detail) ? detail.detail.map((d: any) => d.msg).join("; ") : detail?.detail || err.message);
      } else {
        setError("Failed to run scan.");
      }
    } finally {
      setScanning(false);
    }
  }

  async function handleResolve(id: number) {
    await api.resolveAlert(id);
    setAlerts(await api.listAlerts({ hostId }));
  }

  if (!host) return <p>Loading...</p>;

  return (
    <div>
      <button className="secondary" onClick={onBack}>
        ← Back to dashboard
      </button>

      <div className="panel">
        <h2>{host.name}</h2>
        <p>
          <strong>Address:</strong> {host.address}
        </p>
        {host.description && <p>{host.description}</p>}
        {host.expected_ports && (
          <p>
            <strong>Expected ports:</strong> {host.expected_ports.join(", ")}
          </p>
        )}
        {error && <div className="error-banner">{error}</div>}
      </div>

      <div className="panel">
        <h3>Network diagnostics</h3>
        <button onClick={handleRunChecks} disabled={running}>
          {running ? "Running..." : "Run diagnostics now"}
        </button>

        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Check</th>
              <th>Target</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((c) => (
              <tr key={c.id}>
                <td>{new Date(c.checked_at).toLocaleString()}</td>
                <td>{c.check_type}</td>
                <td>{c.target}</td>
                <td>
                  <StatusBadge status={c.status} />
                </td>
                <td>{c.latency_ms != null ? `${c.latency_ms.toFixed(1)} ms` : "—"}</td>
                <td>{c.detail}</td>
              </tr>
            ))}
            {checks.length === 0 && (
              <tr>
                <td colSpan={6} className="empty-state">
                  No checks run yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h3>Nmap service discovery scan</h3>
        <div className="warning-banner">
          Only run this against a host you own or are explicitly authorized to
          test — confirmed every time, not just when this host was added.
        </div>
        <label>
          Top ports to scan
          <input
            type="number"
            min={1}
            max={1000}
            value={topPorts}
            onChange={(e) => setTopPorts(parseInt(e.target.value, 10) || 100)}
          />
        </label>
        <label className="checkbox-label">
          <input type="checkbox" checked={scanAck} onChange={(e) => setScanAck(e.target.checked)} />
          I confirm I am authorized to scan {host.address} right now.
        </label>
        <button onClick={handleRunScan} disabled={scanning || !scanAck}>
          {scanning ? "Scanning..." : "Run scan"}
        </button>

        <h4>Scan history</h4>
        <ScanHistory scans={scans} />
      </div>

      <div className="panel">
        <h3>Alerts for this host</h3>
        <AlertList alerts={alerts} onResolve={handleResolve} />
      </div>
    </div>
  );
}
