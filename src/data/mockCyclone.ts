import type { CycloneData } from '../types/cyclone';

export const mockCyclone: CycloneData = {
  name: 'Cyclone Varsha',
  category: 'Severe Cyclonic Storm',
  confidence: 94.2,
  pressure: 962,
  movementDir: 'NE',
  movementSpeed: 18,
  rainfall: 120,
  riskLevel: 'HIGH',
  current: {
    lat: 15.2,
    lon: 82.3,
    timestamp: '2026-08-26T21:00:00',
    wind: 118,
  },
  track: [
    { lat: 8.1, lon: 86.5, timestamp: '2026-08-23T09:00:00', wind: 45 },
    { lat: 9.3, lon: 86.0, timestamp: '2026-08-23T21:00:00', wind: 55 },
    { lat: 10.5, lon: 85.2, timestamp: '2026-08-24T09:00:00', wind: 65 },
    { lat: 11.4, lon: 84.3, timestamp: '2026-08-24T21:00:00', wind: 78 },
    { lat: 12.2, lon: 83.6, timestamp: '2026-08-25T09:00:00', wind: 90 },
    { lat: 13.0, lon: 83.1, timestamp: '2026-08-25T15:00:00', wind: 100 },
    { lat: 13.8, lon: 82.8, timestamp: '2026-08-25T21:00:00', wind: 108 },
    { lat: 14.5, lon: 82.5, timestamp: '2026-08-26T09:00:00', wind: 115 },
    { lat: 15.2, lon: 82.3, timestamp: '2026-08-26T21:00:00', wind: 118 },
  ],
  forecast: [
    { lat: 15.4, lon: 82.7, timestamp: '2026-08-26T23:00:00', hoursAhead: 2, wind: 120 },
    { lat: 15.7, lon: 83.1, timestamp: '2026-08-27T03:00:00', hoursAhead: 6, wind: 122 },
    { lat: 16.2, lon: 83.8, timestamp: '2026-08-27T15:00:00', hoursAhead: 18, wind: 125 },
    { lat: 16.8, lon: 84.5, timestamp: '2026-08-27T21:00:00', hoursAhead: 24, wind: 123 },
    { lat: 18.3, lon: 87.2, timestamp: '2026-08-29T21:00:00', hoursAhead: 72, wind: 110 },
  ],
};
