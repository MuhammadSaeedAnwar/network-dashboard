import { useEffect, useState } from "react";
import { api } from "./api";
import type { Alert, DashboardSummary, HostSummary } from "./types";
import DashboardCards from "./components/DashboardCards";
import HostList from "./components/HostList";
import AddHostForm from "./components/AddHostForm";
import HostDetail from "./components/HostDetail";
import AlertList from "./components/AlertList";

type View = "dashboard" | "host";

export default function App() {
  const [view, setView] = useState<View>("dashboard");
  const [selectedHostId, setSelectedHostId] = useState<number | null>(null);
  const [hosts, setHosts] = useState<HostSummary[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  async function refresh() {
    try {
      const [h, s, a] = await Promise.all([api.listHosts(), api.dashboardSummary(), api.listAlerts({ resolved: false })]);
      setHosts(h);
      setSummary(s);
      setAlerts(a);
      setLoadError(null);
    } catch {
      setLoadError(
        "Could not reach the backend API. Is it running? See README for docker compose / uvicorn instructions."
      );
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleDelete(id: number) {
    await api.deleteHost(id);
    await refresh();
  }

  async function handleResolve(id: number) {
    await api.resolveAlert(id);
    await refresh();
  }

  if (view === "host" && selectedHostId !== null) {
    return (
      <div className="app-shell">
        <Header />
        <HostDetail
          hostId={selectedHostId}
          onBack={() => {
            setView("dashboard");
            refresh();
          }}
        />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Header />

      {loadError && <div className="error-banner">{loadError}</div>}

      <DashboardCards summary={summary} />

      <div className="panel">
        <h3>Monitored hosts</h3>
        <HostList
          hosts={hosts}
          onSelect={(id) => {
            setSelectedHostId(id);
            setView("host");
          }}
          onDelete={handleDelete}
        />
      </div>

      <AddHostForm onCreated={refresh} />

      <div className="panel">
        <h3>Open alerts</h3>
        <AlertList alerts={alerts} onResolve={handleResolve} />
      </div>
    </div>
  );
}

function Header() {
  return (
    <header className="app-header">
      <h1>Network Troubleshooting &amp; Security Dashboard</h1>
      <p className="subtitle">
        Authorized-only diagnostics and service discovery for hosts you own or are explicitly authorized to test.
      </p>
    </header>
  );
}
