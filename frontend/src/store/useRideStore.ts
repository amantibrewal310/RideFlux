import { create } from "zustand";
import type { Ride } from "../types/ride";

interface RideState {
  rides: Map<string, Ride>;
  setRides: (rides: Ride[]) => void;
  addRide: (ride: Ride) => void;
  updateRide: (ride: Partial<Ride> & { id: string }) => void;
  getRidesByStatus: (status: string) => Ride[];
  getAllRides: () => Ride[];
}

export const useRideStore = create<RideState>((set, get) => ({
  rides: new Map(),

  setRides: (rides) =>
    set(() => {
      const map = new Map<string, Ride>();
      rides.forEach((r) => map.set(r.id, r));
      return { rides: map };
    }),

  addRide: (ride) =>
    set((state) => {
      const next = new Map(state.rides);
      next.set(ride.id, ride);
      return { rides: next };
    }),

  updateRide: (partial) =>
    set((state) => {
      const existing = state.rides.get(partial.id);
      if (!existing) return state;
      const next = new Map(state.rides);
      next.set(partial.id, { ...existing, ...partial });
      return { rides: next };
    }),

  getRidesByStatus: (status) => {
    const rides: Ride[] = [];
    get().rides.forEach((r) => {
      if (r.status === status) rides.push(r);
    });
    return rides;
  },

  getAllRides: () => Array.from(get().rides.values()),
}));
