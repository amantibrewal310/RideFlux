export interface Ride {
  id: string;
  rider_id: string;
  status: string;
  pickup_lat: number;
  pickup_lng: number;
  pickup_address?: string;
  dest_lat: number;
  dest_lng: number;
  dest_address?: string;
  vehicle_type: string;
  payment_method: string;
  surge_multiplier: number;
  estimated_fare?: number;
  matched_driver_id?: string;
  trip_id?: string;
  total_fare?: number;
  created_at: string;
}
