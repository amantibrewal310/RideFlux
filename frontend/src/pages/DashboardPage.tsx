import { useState } from "react";
import MapView from "../components/map/MapView";
import RideRequestForm from "../components/rides/RideRequestForm";
import RideList from "../components/rides/RideList";
import DriverList from "../components/drivers/DriverList";
import { useDriverStore } from "../store/useDriverStore";
import { useNotificationStore } from "../store/useNotificationStore";
import { refreshDriverLocations } from "../api/http";

export default function DashboardPage() {
  const drivers = useDriverStore((s) => Array.from(s.drivers.values()));
  const notify = useNotificationStore((s) => s.add);
  const [refreshing, setRefreshing] = useState(false);

  async function handleRefreshLocations() {
    setRefreshing(true);
    try {
      await refreshDriverLocations(drivers);
      notify("success", `Refreshed locations for ${drivers.length} drivers`);
    } catch (err) {
      notify("error", (err as Error).message);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="dashboard-layout">
      {/* Left: Map */}
      <section className="dashboard-map">
        <MapView />
      </section>

      {/* Right: Side panel */}
      <aside className="dashboard-panel">
        <RideRequestForm />

        <div className="panel-section">
          <h3 className="panel-section-title">Recent Rides</h3>
          <RideList />
        </div>

        <div className="panel-section">
          <div className="panel-section-header">
            <h3 className="panel-section-title">Drivers</h3>
            <button
              className="btn btn-sm btn-accent"
              disabled={refreshing}
              onClick={handleRefreshLocations}
            >
              {refreshing ? "Refreshing..." : "Refresh Locations"}
            </button>
          </div>
          <DriverList />
        </div>
      </aside>
    </div>
  );
}
