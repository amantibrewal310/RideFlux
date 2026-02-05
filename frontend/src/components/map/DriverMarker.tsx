import { useEffect, useRef } from "react";
import { Marker, Popup } from "react-leaflet";
import L from "leaflet";
import type { Driver } from "../../types/driver";

interface Props {
  driver: Driver;
}

/** Custom icon for drivers */
const driverIcon = new L.Icon({
  iconUrl:
    "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export default function DriverMarker({ driver }: Props) {
  const markerRef = useRef<L.Marker | null>(null);

  // Imperative position update to avoid React re-render on high-freq location changes
  useEffect(() => {
    if (
      markerRef.current &&
      driver.current_lat != null &&
      driver.current_lng != null
    ) {
      markerRef.current.setLatLng([driver.current_lat, driver.current_lng]);
    }
  }, [driver.current_lat, driver.current_lng]);

  if (driver.current_lat == null || driver.current_lng == null) return null;

  return (
    <Marker
      ref={markerRef}
      position={[driver.current_lat, driver.current_lng]}
      icon={driverIcon}
    >
      <Popup>
        <strong>{driver.name}</strong>
        <br />
        {driver.vehicle_type} &middot; {driver.status}
        <br />
        Rating: {driver.rating.toFixed(1)}
      </Popup>
    </Marker>
  );
}
