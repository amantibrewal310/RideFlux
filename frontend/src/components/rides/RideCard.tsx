import { useState } from "react";
import type { Ride } from "../../types/ride";
import RideStatusBadge from "./RideStatusBadge";
import {
  acceptRide,
  cancelRide,
  startTrip,
  endTrip,
  createPayment,
} from "../../api/http";
import { useRideStore } from "../../store/useRideStore";
import { useNotificationStore } from "../../store/useNotificationStore";

interface Props {
  ride: Ride;
}

/** Haversine distance in meters */
function haversineM(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): number {
  const R = 6_371_000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export default function RideCard({ ride }: Props) {
  const timeAgo = formatTimeAgo(ride.created_at);
  const updateRide = useRideStore((s) => s.updateRide);
  const notify = useNotificationStore((s) => s.add);
  const [busy, setBusy] = useState(false);

  async function handleAction(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } catch (err) {
      notify("error", (err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function renderActions() {
    switch (ride.status) {
      case "matching":
        return (
          <div className="ride-card-actions">
            <button
              className="btn btn-sm btn-danger"
              disabled={busy}
              onClick={() =>
                handleAction(async () => {
                  await cancelRide(ride.id);
                  updateRide({ id: ride.id, status: "cancelled" });
                })
              }
            >
              Cancel
            </button>
          </div>
        );

      case "offered":
        return (
          <div className="ride-card-actions">
            {ride.matched_driver_id && (
              <button
                className="btn btn-sm btn-success"
                disabled={busy}
                onClick={() =>
                  handleAction(async () => {
                    await acceptRide(ride.matched_driver_id!, ride.id, true);
                    updateRide({ id: ride.id, status: "accepted" });
                  })
                }
              >
                Accept
              </button>
            )}
            {ride.matched_driver_id && (
              <button
                className="btn btn-sm btn-warning"
                disabled={busy}
                onClick={() =>
                  handleAction(async () => {
                    await acceptRide(ride.matched_driver_id!, ride.id, false);
                    updateRide({ id: ride.id, status: "matching" });
                  })
                }
              >
                Decline
              </button>
            )}
            <button
              className="btn btn-sm btn-danger"
              disabled={busy}
              onClick={() =>
                handleAction(async () => {
                  await cancelRide(ride.id);
                  updateRide({ id: ride.id, status: "cancelled" });
                })
              }
            >
              Cancel
            </button>
          </div>
        );

      case "accepted":
        return (
          <div className="ride-card-actions">
            <button
              className="btn btn-sm btn-success"
              disabled={busy}
              onClick={() =>
                handleAction(async () => {
                  const trip = await startTrip(ride.id);
                  updateRide({
                    id: ride.id,
                    status: "in_progress",
                    trip_id: trip.id,
                  });
                })
              }
            >
              Start Trip
            </button>
            <button
              className="btn btn-sm btn-danger"
              disabled={busy}
              onClick={() =>
                handleAction(async () => {
                  await cancelRide(ride.id);
                  updateRide({ id: ride.id, status: "cancelled" });
                })
              }
            >
              Cancel
            </button>
          </div>
        );

      case "in_progress":
      case "in_trip":
        return (
          <div className="ride-card-actions">
            <button
              className="btn btn-sm btn-accent"
              disabled={busy || !ride.trip_id}
              onClick={() =>
                handleAction(async () => {
                  const straightLine = haversineM(
                    ride.pickup_lat,
                    ride.pickup_lng,
                    ride.dest_lat,
                    ride.dest_lng
                  );
                  const distanceM = Math.round(straightLine * 1.3);
                  const durationS = Math.round((distanceM / 1000 / 25) * 3600);
                  const trip = await endTrip(ride.trip_id!, distanceM, durationS);
                  updateRide({
                    id: ride.id,
                    status: "completed",
                    total_fare: trip.total_fare,
                  });
                })
              }
            >
              End Trip
            </button>
          </div>
        );

      case "completed":
        return (
          <div className="ride-card-actions">
            {ride.total_fare != null && (
              <span className="ride-card-total">
                Total: INR {ride.total_fare.toFixed(0)}
              </span>
            )}
            <button
              className="btn btn-sm btn-success"
              disabled={busy || !ride.trip_id}
              onClick={() =>
                handleAction(async () => {
                  await createPayment({
                    trip_id: ride.trip_id!,
                    payment_method: ride.payment_method,
                  });
                  updateRide({ id: ride.id, status: "paid" });
                  notify("success", "Payment processed!");
                })
              }
            >
              Pay
            </button>
          </div>
        );

      default:
        return null;
    }
  }

  return (
    <div className="card ride-card">
      <div className="ride-card-header">
        <span className="ride-card-id" title={ride.id}>
          #{ride.id.slice(0, 8)}
        </span>
        <RideStatusBadge status={ride.status} />
      </div>

      <div className="ride-card-body">
        <div className="ride-card-route">
          <div className="ride-card-point">
            <span className="dot dot--green" />
            <span>
              {ride.pickup_address ??
                `${ride.pickup_lat.toFixed(4)}, ${ride.pickup_lng.toFixed(4)}`}
            </span>
          </div>
          <div className="ride-card-point">
            <span className="dot dot--red" />
            <span>
              {ride.dest_address ??
                `${ride.dest_lat.toFixed(4)}, ${ride.dest_lng.toFixed(4)}`}
            </span>
          </div>
        </div>

        <div className="ride-card-meta">
          <span className="ride-card-vehicle">{ride.vehicle_type}</span>
          <span className="ride-card-fare">
            {ride.estimated_fare != null
              ? `INR ${ride.estimated_fare.toFixed(0)}`
              : "--"}
          </span>
          {ride.matched_driver_id && (
            <span className="ride-card-driver" title={ride.matched_driver_id}>
              Driver: {ride.matched_driver_id.slice(0, 8)}
            </span>
          )}
          <span className="ride-card-time">{timeAgo}</span>
        </div>
      </div>

      {renderActions()}
    </div>
  );
}

function formatTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
