interface StatusBadgeProps {
  status: string;
}

const COLORS: Record<string, string> = {
  ok: "#1a7f37",
  warning: "#9a6700",
  critical: "#cf222e",
  unknown: "#6e7781",
  completed: "#1a7f37",
  running: "#9a6700",
  failed: "#cf222e",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const color = COLORS[status] || "#6e7781";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: "12px",
        fontSize: "0.75rem",
        fontWeight: 600,
        color: "#fff",
        backgroundColor: color,
        textTransform: "uppercase",
        letterSpacing: "0.02em",
      }}
    >
      {status}
    </span>
  );
}
