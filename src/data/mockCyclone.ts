import type { CycloneData } from '../types/cyclone';

export const mockCyclone: CycloneData = {
  name: 'Cyclone Fani',
  category: 'Extremely Severe Cyclonic Storm',
  confidence: 84.6,
  pressure: 932,
  movementDir: 'NE',
  movementSpeed: 18,
  rainfall: 120,
  riskLevel: 'HIGH',
  current: {
    lat: 15.2,
    lon: 82.3,
    timestamp: '2019-05-02T21:00:00',
    wind: 175,
  },
  track: [
    { lat: 8.1, lon: 86.5, timestamp: '2019-04-26T09:00:00', wind: 45 },
    { lat: 9.3, lon: 86.0, timestamp: '2019-04-26T21:00:00', wind: 55 },
    { lat: 10.5, lon: 85.2, timestamp: '2019-04-27T09:00:00', wind: 65 },
    { lat: 11.4, lon: 84.3, timestamp: '2019-04-27T21:00:00', wind: 78 },
    { lat: 12.2, lon: 83.6, timestamp: '2019-04-28T09:00:00', wind: 90 },
    { lat: 13.0, lon: 83.1, timestamp: '2019-04-28T15:00:00', wind: 100 },
    { lat: 13.8, lon: 82.8, timestamp: '2019-04-28T21:00:00', wind: 108 },
    { lat: 14.5, lon: 82.5, timestamp: '2019-04-29T09:00:00', wind: 115 },
    { lat: 15.2, lon: 82.3, timestamp: '2019-05-02T21:00:00', wind: 175 },
  ],
  forecast: [
    { lat: 15.4, lon: 82.7, timestamp: '2019-05-02T23:00:00', hoursAhead: 2, wind: 178 },
    { lat: 15.7, lon: 83.1, timestamp: '2019-05-03T03:00:00', hoursAhead: 6, wind: 180 },
    { lat: 16.2, lon: 83.8, timestamp: '2019-05-03T15:00:00', hoursAhead: 18, wind: 170 },
    { lat: 16.8, lon: 84.5, timestamp: '2019-05-03T21:00:00', hoursAhead: 24, wind: 155 },
    { lat: 18.3, lon: 87.2, timestamp: '2019-05-05T21:00:00', hoursAhead: 72, wind: 80 },
  ],
};
