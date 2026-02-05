import { useState } from "react";
import { createRide } from "../../api/http";
import { useRideStore } from "../../store/useRideStore";
import { useNotificationStore } from "../../store/useNotificationStore";
import { BANGALORE_LOCALITIES, type Locality } from "../../data/bangaloreLocalities";

const TEST_RIDER_ID = "a0000000-0000-0000-0000-000000000001";
const VEHICLE_TYPES = ["auto", "mini", "sedan", "suv"];
const PAYMENT_METHODS = ["cash", "card", "wallet"];

export default function RideRequestForm() {
  const addRide = useRideStore((s) => s.addRide);
  const notify = useNotificationStore((s) => s.add);

  const [pickup, setPickup] = useState<Locality | null>(null);
  const [destination, setDestination] = useState<Locality | null>(null);
  const [vehicleType, setVehicleType] = useState("mini");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!pickup || !destination) {
      notify("error", "Please select both pickup and destination");
      return;
    }
    if (pickup.name === destination.name) {
      notify("error", "Pickup and destination must be different");
      return;
    }
    setSubmitting(true);

    try {
      const ride = await createRide({
        rider_id: TEST_RIDER_ID,
        pickup_lat: pickup.lat,
        pickup_lng: pickup.lng,
        pickup_address: pickup.name,
        dest_lat: destination.lat,
        dest_lng: destination.lng,
        dest_address: destination.name,
        vehicle_type: vehicleType,
        payment_method: paymentMethod,
      });
      addRide(ride);
      notify("success", "Ride requested successfully!");
    } catch (err) {
      notify("error", (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="ride-request-form" onSubmit={handleSubmit}>
      <h3 className="form-title">Request a Ride</h3>

      <div className="form-group">
        <label>Pickup</label>
        <div className="locality-grid">
          {BANGALORE_LOCALITIES.map((loc) => (
            <button
              key={loc.name}
              type="button"
              className={`btn-locality${pickup?.name === loc.name ? " btn-locality--active" : ""}`}
              onClick={() => setPickup(loc)}
            >
              {loc.name}
            </button>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label>Destination</label>
        <div className="locality-grid">
          {BANGALORE_LOCALITIES.map((loc) => (
            <button
              key={loc.name}
              type="button"
              className={`btn-locality${destination?.name === loc.name ? " btn-locality--active" : ""}`}
              onClick={() => setDestination(loc)}
            >
              {loc.name}
            </button>
          ))}
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="vehicleType">Vehicle Type</label>
          <select
            id="vehicleType"
            value={vehicleType}
            onChange={(e) => setVehicleType(e.target.value)}
          >
            {VEHICLE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="paymentMethod">Payment</label>
          <select
            id="paymentMethod"
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
          >
            {PAYMENT_METHODS.map((m) => (
              <option key={m} value={m}>
                {m.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button type="submit" className="btn btn-primary" disabled={submitting || !pickup || !destination}>
        {submitting ? "Requesting..." : "Request Ride"}
      </button>
    </form>
  );
}
