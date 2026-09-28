import type { DashboardSummary } from "../types";

interface Props {
  summary: DashboardSummary | null;
}

export default function DashboardCards({ summary }: Props) {
  if (!summary) return null;

  const cards = [
    { label: "Total hosts", value: summary.total_hosts, color: "#1f6feb" },
    { label: "OK", value: summary.hosts_ok, color: "#1a7f37" },
    { label: "Warning", value: summary.hosts_warning, color: "#9a6700" },
    { label: "Critical", value: summary.hosts_critical, color: "#cf222e" },
    { label: "Unknown", value: summary.hosts_unknown, color: "#6e7781" },
    { label: "Open alerts", value: summary.open_alerts, color: "#bf3989" },
    { label: "Total scans run", value: summary.total_scans, color: "#8250df" },
  ];

  return (
    <div className="card-grid">
      {cards.map((c) => (
        <div className="summary-card" key={c.label}>
          <div className="summary-value" style={{ color: c.color }}>
            {c.value}
          </div>
          <div className="summary-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
