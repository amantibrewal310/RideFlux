export interface Driver {
  id: string;
  name: string;
  email: string;
  phone?: string;
  vehicle_type: string;
  status: string;
  current_lat?: number;
  current_lng?: number;
  rating: number;
  created_at: string;
}
