import { useEffect, useState } from "react";
import { useDriverStore } from "../store/useDriverStore";
import { getDrivers } from "../api/http";
import type { Driver } from "../types/driver";

/**
 * Fetches drivers on mount and returns the current driver list
 * from the Zustand store.
 */
export function useDrivers() {
  const drivers = useDriverStore((s) => s.getAllDrivers());
  const setDrivers = useDriverStore((s) => s.setDrivers);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const list: Driver[] = await getDrivers();
        if (!cancelled) setDrivers(list);
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [setDrivers]);

  return { drivers, loading, error };
}
