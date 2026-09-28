import type { HostSummary } from "../types";
import StatusBadge from "./StatusBadge";

interface Props {
  hosts: HostSummary[];
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}

export default function HostList({ hosts, onSelect, onDelete }: Props) {
  if (hosts.length === 0) {
    return <p className="empty-state">No hosts yet. Add one below to get started.</p>;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Address</th>
          <th>Status</th>
          <th>Latency</th>
          <th>Open ports</th>
          <th>Alerts</th>
          <th>Last checked</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {hosts.map((h) => (
          <tr key={h.id}>
            <td>
              <a className="link" onClick={() => onSelect(h.id)}>
                {h.name}
              </a>
            </td>
            <td>{h.address}</td>
            <td>
              <StatusBadge status={h.latest_status} />
            </td>
            <td>{h.latest_latency_ms != null ? `${h.latest_latency_ms.toFixed(1)} ms` : "—"}</td>
            <td>{h.open_port_count ?? "—"}</td>
            <td>{h.open_alert_count > 0 ? <span className="alert-count">{h.open_alert_count}</span> : "0"}</td>
            <td>{h.last_checked_at ? new Date(h.last_checked_at).toLocaleString() : "never"}</td>
            <td>
              <button className="secondary" onClick={() => onDelete(h.id)}>
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
