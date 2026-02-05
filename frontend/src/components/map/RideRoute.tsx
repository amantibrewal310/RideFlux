import { Polyline, CircleMarker, Tooltip } from "react-leaflet";
import type { Ride } from "../../types/ride";

interface Props {
  ride: Ride;
}

export default function RideRoute({ ride }: Props) {
  const pickup: [number, number] = [ride.pickup_lat, ride.pickup_lng];
  const dest: [number, number] = [ride.dest_lat, ride.dest_lng];

  return (
    <>
      {/* Route line */}
      <Polyline
        positions={[pickup, dest]}
        pathOptions={{ color: "#6366f1", weight: 3, dashArray: "8 4" }}
      />

      {/* Pickup marker */}
      <CircleMarker
        center={pickup}
        radius={6}
        pathOptions={{ color: "#22c55e", fillColor: "#22c55e", fillOpacity: 1 }}
      >
        <Tooltip direction="top" permanent={false}>
          Pickup: {ride.pickup_address ?? `${ride.pickup_lat.toFixed(4)}, ${ride.pickup_lng.toFixed(4)}`}
        </Tooltip>
      </CircleMarker>

      {/* Destination marker */}
      <CircleMarker
        center={dest}
        radius={6}
        pathOptions={{ color: "#ef4444", fillColor: "#ef4444", fillOpacity: 1 }}
      >
        <Tooltip direction="top" permanent={false}>
          Dest: {ride.dest_address ?? `${ride.dest_lat.toFixed(4)}, ${ride.dest_lng.toFixed(4)}`}
        </Tooltip>
      </CircleMarker>
    </>
  );
}
