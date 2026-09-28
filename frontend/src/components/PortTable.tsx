import type { PortResult } from "../types";
import StatusBadge from "./StatusBadge";

interface Props {
  ports: PortResult[];
}

export default function PortTable({ ports }: Props) {
  if (ports.length === 0) {
    return <p className="empty-state">No ports recorded for this scan.</p>;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Port</th>
          <th>Protocol</th>
          <th>State</th>
          <th>Service</th>
          <th>Product</th>
          <th>Version</th>
        </tr>
      </thead>
      <tbody>
        {ports
          .slice()
          .sort((a, b) => a.port_number - b.port_number)
          .map((p) => (
            <tr key={p.id}>
              <td>{p.port_number}</td>
              <td>{p.protocol}</td>
              <td>
                <StatusBadge status={p.state} />
              </td>
              <td>{p.service_name || "—"}</td>
              <td>{p.service_product || "—"}</td>
              <td>{p.service_version || "—"}</td>
            </tr>
          ))}
      </tbody>
    </table>
  );
}
