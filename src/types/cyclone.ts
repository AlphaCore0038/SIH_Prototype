export interface TrackPoint {
  lat: number;
  lon: number;
  timestamp: string;
  wind?: number;
}

export interface ForecastPoint {
  lat: number;
  lon: number;
  timestamp: string;
  hoursAhead: number;
  wind?: number;
}

export interface CycloneData {
  name: string;
  category: string;
  confidence: number;
  pressure: number;
  movementDir: string;
  movementSpeed: number;
  rainfall: number;
  riskLevel: 'LOW' | 'MODERATE' | 'HIGH' | 'EXTREME';
  track: TrackPoint[];
  current: TrackPoint;
  forecast: ForecastPoint[];
}
