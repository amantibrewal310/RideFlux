import { useCallback, useRef, useState } from "react";
import WebSocketClient from "../api/ws";
import { useRideStore } from "../store/useRideStore";
import { useDriverStore } from "../store/useDriverStore";
import { useNotificationStore } from "../store/useNotificationStore";
import { getRides, getDrivers } from "../api/http";
import type { WSMessage, DriverLocationPayload, RideEventPayload, DriverStatusPayload } from "../types/ws";

/** Build WS URL that goes through the Vite dev-server proxy */
const WS_BASE =
  `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/dashboard`;

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const clientRef = useRef<WebSocketClient | null>(null);
  const connectedRef = useRef(false);

  const fetchSnapshot = useCallback(async () => {
    try {
      const [rides, drivers] = await Promise.all([getRides(), getDrivers()]);
      useRideStore.getState().setRides(rides);
      useDriverStore.getState().setDrivers(drivers);
    } catch {
      // snapshot fetch failed; will retry on next reconnect
    }
  }, []);

  const handleMessage = useCallback(
    (msg: WSMessage) => {
      switch (msg.type) {
        case "ride:requested": {
          const d = msg as unknown as Record<string, unknown>;
          const rideId = d.ride_id as string;
          const store = useRideStore.getState();
          if (store.rides.has(rideId)) {
            // Already have this ride from the HTTP response — just merge status
            store.updateRide({ id: rideId, status: "matching" });
          } else {
            // New ride from another source (e.g. another dashboard viewer)
            store.addRide({
              id: rideId,
              rider_id: (d.rider_id as string) ?? "",
              status: "matching",
              pickup_lat: (d.pickup_lat as number) ?? 0,
              pickup_lng: (d.pickup_lng as number) ?? 0,
              dest_lat: (d.dest_lat as number) ?? 0,
              dest_lng: (d.dest_lng as number) ?? 0,
              vehicle_type: (d.vehicle_type as string) ?? "mini",
              payment_method: "cash",
              surge_multiplier: (d.surge_multiplier as number) ?? 1,
              estimated_fare: d.estimated_fare as number | undefined,
              created_at: new Date().toISOString(),
            });
          }
          useNotificationStore.getState().add("info", `New ride requested: ${rideId.slice(0, 8)}`);
          break;
        }
        case "ride:offered": {
          const raw = msg as unknown as Record<string, unknown>;
          const driverId = (raw.matched_driver_id ?? raw.driver_id) as string | undefined;
          const fare = raw.estimated_fare != null ? Number(raw.estimated_fare) : undefined;
          useRideStore.getState().updateRide({
            id: raw.ride_id as string,
            status: "offered",
            matched_driver_id: driverId,
            ...(fare != null && !isNaN(fare) ? { estimated_fare: fare } : {}),
          });
          useNotificationStore
            .getState()
            .add("info", `Ride ${(raw.ride_id as string).slice(0, 8)} => offered`);
          break;
        }
        case "ride:no_drivers": {
          const payload = msg as unknown as RideEventPayload;
          useRideStore.getState().updateRide({
            id: payload.ride_id,
            status: "no_drivers",
          });
          useNotificationStore
            .getState()
            .add("warning", `Ride ${payload.ride_id.slice(0, 8)} => no drivers found`);
          break;
        }
        case "ride:matched": {
          const raw = msg as unknown as Record<string, unknown>;
          const driverId = (raw.matched_driver_id ?? raw.driver_id) as string | undefined;
          useRideStore.getState().updateRide({
            id: raw.ride_id as string,
            status: "accepted",
            matched_driver_id: driverId,
          });
          useNotificationStore
            .getState()
            .add("success", `Ride ${(raw.ride_id as string).slice(0, 8)} => accepted`);
          break;
        }
        case "ride:started": {
          const payload = msg as unknown as RideEventPayload;
          useRideStore.getState().updateRide({
            id: payload.ride_id,
            status: "in_progress",
            trip_id: payload.trip_id,
          });
          useNotificationStore
            .getState()
            .add("success", `Ride ${payload.ride_id.slice(0, 8)} => started`);
          break;
        }
        case "ride:completed": {
          const payload = msg as unknown as RideEventPayload;
          useRideStore.getState().updateRide({
            id: payload.ride_id,
            status: "completed",
            total_fare: payload.total_fare != null ? Number(payload.total_fare) : undefined,
          });
          useNotificationStore
            .getState()
            .add("success", `Ride ${payload.ride_id.slice(0, 8)} => completed`);
          break;
        }
        case "ride:cancelled": {
          const payload = msg as unknown as RideEventPayload;
          useRideStore.getState().updateRide({
            id: payload.ride_id,
            status: "cancelled",
          });
          useNotificationStore
            .getState()
            .add("success", `Ride ${payload.ride_id.slice(0, 8)} => cancelled`);
          break;
        }
        case "driver:location_update": {
          const loc = msg as unknown as DriverLocationPayload;
          useDriverStore.getState().updateDriverLocation(loc.driver_id, loc.lat, loc.lng);
          break;
        }
        case "driver:status_changed": {
          const ds = msg as unknown as DriverStatusPayload;
          useDriverStore.getState().updateDriver({ id: ds.driver_id, status: ds.status });
          break;
        }
        case "pong":
          // heartbeat ack — nothing to do
          break;
        default:
          break;
      }
    },
    []
  );

  const connect = useCallback(() => {
    if (connectedRef.current) return;

    const client = WebSocketClient.getInstance();
    clientRef.current = client;

    client.onMessage((msg) => {
      handleMessage(msg);
    });

    client.connect(WS_BASE);
    connectedRef.current = true;
    setConnected(true);

    // Fetch initial snapshot
    fetchSnapshot();
  }, [handleMessage, fetchSnapshot]);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    connectedRef.current = false;
    setConnected(false);
  }, []);

  return { connected, connect, disconnect };
}
