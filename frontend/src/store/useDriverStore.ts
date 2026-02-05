import { create } from "zustand";
import type { Driver } from "../types/driver";

interface DriverState {
  drivers: Map<string, Driver>;
  setDrivers: (drivers: Driver[]) => void;
  updateDriver: (driver: Partial<Driver> & { id: string }) => void;
  updateDriverLocation: (
    driverId: string,
    lat: number,
    lng: number
  ) => void;
  getAllDrivers: () => Driver[];
}

export const useDriverStore = create<DriverState>((set, get) => ({
  drivers: new Map(),

  setDrivers: (drivers) =>
    set(() => {
      const map = new Map<string, Driver>();
      drivers.forEach((d) => map.set(d.id, d));
      return { drivers: map };
    }),

  updateDriver: (partial) =>
    set((state) => {
      const existing = state.drivers.get(partial.id);
      if (!existing) return state;
      const next = new Map(state.drivers);
      next.set(partial.id, { ...existing, ...partial });
      return { drivers: next };
    }),

  /** High-frequency location update — only touches lat/lng */
  updateDriverLocation: (driverId, lat, lng) =>
    set((state) => {
      const existing = state.drivers.get(driverId);
      if (!existing) return state;
      const next = new Map(state.drivers);
      next.set(driverId, { ...existing, current_lat: lat, current_lng: lng });
      return { drivers: next };
    }),

  getAllDrivers: () => Array.from(get().drivers.values()),
}));
