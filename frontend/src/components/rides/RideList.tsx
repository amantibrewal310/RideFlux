import { useRideStore } from "../../store/useRideStore";
import RideCard from "./RideCard";

interface Props {
  statusFilter?: string;
}

export default function RideList({ statusFilter }: Props) {
  const allRides = useRideStore((s) => s.getAllRides());

  const rides = statusFilter
    ? allRides.filter((r) => r.status === statusFilter)
    : allRides;

  // Most recent first
  const sorted = [...rides].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  if (sorted.length === 0) {
    return <p className="empty-state">No rides found.</p>;
  }

  return (
    <div className="ride-list">
      {sorted.map((ride) => (
        <RideCard key={ride.id} ride={ride} />
      ))}
    </div>
  );
}
