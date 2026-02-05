import { MapContainer, TileLayer } from "react-leaflet";
import { useDriverStore } from "../../store/useDriverStore";
import { useRideStore } from "../../store/useRideStore";
import DriverMarker from "./DriverMarker";
import RideRoute from "./RideRoute";

const BANGALORE_CENTER: [number, number] = [12.9716, 77.5946];
const DEFAULT_ZOOM = 12;

export default function MapView() {
  const drivers = useDriverStore((s) => s.getAllDrivers());
  const rides = useRideStore((s) => s.getAllRides());

  const activeRides = rides.filter(
    (r) => r.status === "matched" || r.status === "in_progress"
  );

  return (
    <div className="map-container">
      <MapContainer
        center={BANGALORE_CENTER}
        zoom={DEFAULT_ZOOM}
        scrollWheelZoom
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Driver markers */}
        {drivers
          .filter((d) => d.current_lat != null && d.current_lng != null)
          .map((d) => (
            <DriverMarker key={d.id} driver={d} />
          ))}

        {/* Active ride routes */}
        {activeRides.map((ride) => (
          <RideRoute key={ride.id} ride={ride} />
        ))}
      </MapContainer>
    </div>
  );
}
