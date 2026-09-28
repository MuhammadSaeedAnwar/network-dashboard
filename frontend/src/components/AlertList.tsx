import type { Alert } from "../types";

interface Props {
  alerts: Alert[];
  onResolve: (id: number) => void;
}

export default function AlertList({ alerts, onResolve }: Props) {
  if (alerts.length === 0) {
    return <p className="empty-state">No alerts.</p>;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Raised</th>
          <th>Severity</th>
          <th>Source</th>
          <th>Message</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {alerts.map((a) => (
          <tr key={a.id} className={a.resolved ? "resolved-row" : ""}>
            <td>{new Date(a.raised_at).toLocaleString()}</td>
            <td>
              <span className={`severity-pill severity-${a.severity}`}>{a.severity}</span>
            </td>
            <td>{a.source}</td>
            <td>{a.message}</td>
            <td>
              {!a.resolved && (
                <button className="secondary" onClick={() => onResolve(a.id)}>
                  Resolve
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
