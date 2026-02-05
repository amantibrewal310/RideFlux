import { create } from "zustand";

export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
  createdAt: number;
}

interface NotificationState {
  notifications: Notification[];
  add: (type: Notification["type"], message: string) => void;
  remove: (id: string) => void;
  clear: () => void;
}

let counter = 0;

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],

  add: (type, message) => {
    const id = `notif-${++counter}-${Date.now()}`;
    set((state) => ({
      notifications: [
        ...state.notifications,
        { id, type, message, createdAt: Date.now() },
      ],
    }));

    // Auto-remove after 5 seconds
    setTimeout(() => {
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      }));
    }, 5000);
  },

  remove: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clear: () => set({ notifications: [] }),
}));
