import { useNotificationStore } from "../../store/useNotificationStore";
import type { Notification } from "../../store/useNotificationStore";

const TYPE_CLASS: Record<Notification["type"], string> = {
  info: "toast--info",
  success: "toast--success",
  warning: "toast--warning",
  error: "toast--error",
};

export default function Toast() {
  const notifications = useNotificationStore((s) => s.notifications);
  const remove = useNotificationStore((s) => s.remove);

  if (notifications.length === 0) return null;

  return (
    <div className="toast-container">
      {notifications.map((n) => (
        <div key={n.id} className={`toast ${TYPE_CLASS[n.type]}`}>
          <span className="toast-message">{n.message}</span>
          <button
            className="toast-close"
            onClick={() => remove(n.id)}
            aria-label="Close notification"
          >
            x
          </button>
        </div>
      ))}
    </div>
  );
}
