import type { Driver } from "../../types/driver";

interface Props {
  driver: Driver;
}

const STATUS_CLASS: Record<string, string> = {
  available: "badge--green",
  busy: "badge--yellow",
  offline: "badge--gray",
  on_trip: "badge--indigo",
};

export default function DriverCard({ driver }: Props) {
  const colorClass = STATUS_CLASS[driver.status] ?? "badge--gray";

  return (
    <div className="card driver-card">
      <div className="driver-card-header">
        <span className="driver-card-name">{driver.name}</span>
        <span className={`badge ${colorClass}`}>{driver.status.replace(/_/g, " ")}</span>
      </div>
      <div className="driver-card-body">
        <span className="driver-card-vehicle">{driver.vehicle_type}</span>
        <span className="driver-card-rating">
          {"*".repeat(Math.round(driver.rating))} {driver.rating.toFixed(1)}
        </span>
      </div>
    </div>
  );
}
