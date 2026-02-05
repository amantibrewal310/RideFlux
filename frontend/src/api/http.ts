import type { Ride } from "../types/ride";
import type { Driver } from "../types/driver";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

/** ------------------------------------------------------------------ */
/*  Generic helpers                                                     */
/** ------------------------------------------------------------------ */

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `HTTP ${response.status} – ${response.statusText}: ${body}`
    );
  }

  // 204 No Content
  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}

/** ------------------------------------------------------------------ */
/*  Rides                                                               */
/** ------------------------------------------------------------------ */

export interface CreateRidePayload {
  rider_id: string;
  pickup_lat: number;
  pickup_lng: number;
  pickup_address?: string;
  dest_lat: number;
  dest_lng: number;
  dest_address?: string;
  vehicle_type: string;
  payment_method: string;
}

export function createRide(payload: CreateRidePayload): Promise<Ride> {
  return request<Ride>("/v1/rides", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getRides(): Promise<Ride[]> {
  return request<Ride[]>("/v1/rides");
}

export function getRide(rideId: string): Promise<Ride> {
  return request<Ride>(`/v1/rides/${rideId}`);
}

/** ------------------------------------------------------------------ */
/*  Drivers                                                             */
/** ------------------------------------------------------------------ */

export function getDrivers(): Promise<Driver[]> {
  return request<Driver[]>("/v1/drivers");
}

export interface UpdateLocationPayload {
  lat: number;
  lng: number;
}

export function updateDriverLocation(
  driverId: string,
  payload: UpdateLocationPayload
): Promise<Driver> {
  return request<Driver>(`/v1/drivers/${driverId}/location`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** ------------------------------------------------------------------ */
/*  Ride lifecycle                                                      */
/** ------------------------------------------------------------------ */

export function acceptRide(
  driverId: string,
  rideId: string,
  accept: boolean = true
): Promise<Ride> {
  return request<Ride>(`/v1/drivers/${driverId}/accept`, {
    method: "POST",
    body: JSON.stringify({ ride_id: rideId, accept }),
  });
}

export function cancelRide(rideId: string): Promise<Ride> {
  return request<Ride>(`/v1/rides/${rideId}/cancel`, {
    method: "POST",
  });
}

/** ------------------------------------------------------------------ */
/*  Trips                                                               */
/** ------------------------------------------------------------------ */

export interface Trip {
  id: string;
  ride_id: string;
  driver_id: string;
  rider_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  distance_m: number;
  duration_s: number;
  base_fare: number;
  distance_fare: number;
  time_fare: number;
  surge_multiplier: number;
  total_fare: number;
  created_at: string;
}

export function startTrip(rideId: string): Promise<Trip> {
  return request<Trip>(`/v1/trips/${rideId}/start`, {
    method: "POST",
  });
}

export function getTrip(tripId: string): Promise<Trip> {
  return request<Trip>(`/v1/trips/${tripId}`);
}

export function endTrip(
  tripId: string,
  distanceM: number,
  durationS: number
): Promise<Trip> {
  return request<Trip>(`/v1/trips/${tripId}/end`, {
    method: "POST",
    body: JSON.stringify({ distance_m: distanceM, duration_s: durationS }),
  });
}

/** Bulk-POST all drivers' DB locations to seed Redis GEO */
export async function refreshDriverLocations(
  drivers: Driver[]
): Promise<void> {
  await Promise.all(
    drivers
      .filter((d) => d.current_lat != null && d.current_lng != null)
      .map((d) =>
        updateDriverLocation(d.id, {
          lat: d.current_lat!,
          lng: d.current_lng!,
        })
      )
  );
}

/** ------------------------------------------------------------------ */
/*  Payments                                                            */
/** ------------------------------------------------------------------ */

export interface CreatePaymentPayload {
  trip_id: string;
  payment_method: string;
}

export function createPayment(
  payload: CreatePaymentPayload
): Promise<{ id: string; status: string }> {
  return request<{ id: string; status: string }>("/v1/payments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
