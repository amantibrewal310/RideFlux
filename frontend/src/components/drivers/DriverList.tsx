import { useDriverStore } from "../../store/useDriverStore";
import DriverCard from "./DriverCard";

export default function DriverList() {
  const drivers = useDriverStore((s) => s.getAllDrivers());

  if (drivers.length === 0) {
    return <p className="empty-state">No drivers found.</p>;
  }

  return (
    <div className="driver-list">
      {drivers.map((driver) => (
        <DriverCard key={driver.id} driver={driver} />
      ))}
    </div>
  );
}
