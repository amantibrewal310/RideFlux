/** Types of events sent over the WebSocket */
export type WSEventType =
  | "ride:requested"
  | "ride:matched"
  | "ride:offered"
  | "ride:started"
  | "ride:completed"
  | "ride:cancelled"
  | "ride:no_drivers"
  | "driver:location_update"
  | "driver:status_changed"
  | "pong";

/** Backend sends flat messages: { type, ...fields } */
export interface WSMessage {
  type: WSEventType;
  [key: string]: unknown;
}

export interface DriverLocationPayload {
  driver_id: string;
  lat: number;
  lng: number;
}

export interface RideEventPayload {
  ride_id: string;
  status?: string;
  matched_driver_id?: string;
  estimated_fare?: number;
  trip_id?: string;
  total_fare?: number;
  reason?: string;
}

export interface DriverStatusPayload {
  driver_id: string;
  status: string;
}

export interface SurgeUpdatePayload {
  zone: string;
  multiplier: number;
}
