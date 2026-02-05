import { useDrivers } from "../hooks/useDrivers";
import DriverCard from "../components/drivers/DriverCard";
import LoadingSpinner from "../components/common/LoadingSpinner";

export default function DriversPage() {
  const { drivers, loading, error } = useDrivers();

  return (
    <div className="page-drivers">
      <div className="page-header">
        <h2 className="page-title">Drivers</h2>
        <span className="page-count">{drivers.length} drivers</span>
      </div>

      {loading && <LoadingSpinner />}
      {error && <p className="error-text">Error: {error}</p>}

      <div className="driver-grid">
        {drivers.map((d) => (
          <DriverCard key={d.id} driver={d} />
        ))}
      </div>

      {!loading && drivers.length === 0 && (
        <p className="empty-state">No drivers registered yet.</p>
      )}
    </div>
  );
}
