interface Props {
  status: "connected" | "connecting" | "disconnected";
}

const COLOR_MAP: Record<Props["status"], string> = {
  connected: "var(--color-green)",
  connecting: "var(--color-yellow)",
  disconnected: "var(--color-red)",
};

export default function StatusIndicator({ status }: Props) {
  return (
    <span
      className="status-indicator"
      style={{ backgroundColor: COLOR_MAP[status] }}
      title={status}
    />
  );
}
