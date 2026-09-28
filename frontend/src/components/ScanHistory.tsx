import { Fragment, useState } from "react";
import type { Scan } from "../types";
import StatusBadge from "./StatusBadge";
import PortTable from "./PortTable";

interface Props {
  scans: Scan[];
}

export default function ScanHistory({ scans }: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (scans.length === 0) {
    return <p className="empty-state">No scans have been run against this host yet.</p>;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Started</th>
          <th>Status</th>
          <th>Top ports</th>
          <th>Open ports found</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {scans.map((s) => {
          const openCount = s.ports.filter((p) => p.state === "open").length;
          const expanded = expandedId === s.id;
          return (
            <Fragment key={s.id}>
              <tr>
                <td>{new Date(s.started_at).toLocaleString()}</td>
                <td>
                  <StatusBadge status={s.status} />
                  {s.error_detail && <div className="error-detail">{s.error_detail}</div>}
                </td>
                <td>{s.top_ports}</td>
                <td>{openCount}</td>
                <td>
                  <button className="secondary" onClick={() => setExpandedId(expanded ? null : s.id)}>
                    {expanded ? "Hide ports" : "Show ports"}
                  </button>
                </td>
              </tr>
              {expanded && (
                <tr>
                  <td colSpan={5}>
                    <PortTable ports={s.ports} />
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
