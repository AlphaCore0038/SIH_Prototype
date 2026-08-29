export interface HistoricalTrack {
  name: string;
  year: number;
  category: string;
  points: [number, number][];
}

export const historicalCyclones: HistoricalTrack[] = [
  {
    name: 'Amphan',
    year: 2020,
    category: 'Super Cyclonic Storm',
    points: [
      [11.2, 87.5], [12.0, 87.2], [13.1, 87.0], [14.2, 86.8],
      [15.3, 86.5], [16.5, 86.3], [17.8, 86.0], [19.0, 85.6],
      [20.1, 85.0], [21.0, 84.2], [21.7, 83.0], [22.1, 81.5],
      [22.5, 80.0], [22.8, 78.5], [23.0, 77.0],
    ],
  },
  {
    name: 'Yaas',
    year: 2021,
    category: 'Very Severe Cyclonic Storm',
    points: [
      [14.5, 89.5], [15.2, 89.0], [16.0, 88.5], [17.0, 88.0],
      [18.0, 87.5], [19.0, 87.0], [20.0, 86.5], [21.0, 86.0],
      [21.5, 85.5], [22.0, 85.0], [22.5, 84.5],
    ],
  },
  {
    name: 'Sitrang',
    year: 2022,
    category: 'Severe Cyclonic Storm',
    points: [
      [13.0, 89.0], [14.0, 88.5], [15.0, 88.0], [16.0, 87.5],
      [17.0, 87.0], [18.0, 86.5], [19.0, 86.0], [20.0, 85.5],
      [21.0, 85.0], [22.0, 84.5], [23.0, 84.0],
    ],
  },
  {
    name: 'Mandous',
    year: 2022,
    category: 'Severe Cyclonic Storm',
    points: [
      [9.5, 85.0], [10.5, 84.5], [11.5, 84.0], [12.5, 83.5],
      [13.5, 82.8], [14.0, 82.0], [14.5, 81.0],
    ],
  },
  {
    name: 'Hamoon',
    year: 2023,
    category: 'Severe Cyclonic Storm',
    points: [
      [14.0, 88.5], [15.0, 88.0], [16.5, 87.5], [18.0, 87.0],
      [19.5, 86.5], [21.0, 86.0], [22.0, 85.5], [23.0, 85.0],
    ],
  },
  {
    name: 'Michaung',
    year: 2023,
    category: 'Severe Cyclonic Storm',
    points: [
      [10.0, 82.5], [11.0, 82.0], [12.0, 81.5], [13.0, 81.0],
      [14.0, 80.8], [15.0, 80.5], [16.0, 80.3], [17.0, 80.0],
    ],
  },
  {
    name: 'Dana',
    year: 2024,
    category: 'Severe Cyclonic Storm',
    points: [
      [15.5, 89.5], [16.5, 89.0], [17.5, 88.5], [18.5, 87.5],
      [19.5, 86.5], [20.5, 85.5], [21.0, 84.5],
    ],
  },
  {
    name: 'Fengal',
    year: 2024,
    category: 'Deep Depression',
    points: [
      [6.0, 82.0], [7.0, 83.0], [8.0, 84.0], [9.0, 85.0],
      [10.0, 86.0], [11.0, 87.0],
    ],
  },
  {
    name: 'Remal',
    year: 2024,
    category: 'Very Severe Cyclonic Storm',
    points: [
      [14.5, 88.0], [15.5, 87.5], [16.5, 87.0], [18.0, 86.5],
      [19.5, 86.0], [21.0, 85.5], [22.5, 85.0], [23.5, 84.5],
    ],
  },
];
