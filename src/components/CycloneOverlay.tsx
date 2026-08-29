import { Polyline, CircleMarker, Polygon, Tooltip } from 'react-leaflet';
import type { CycloneData, ForecastPoint } from '../types/cyclone';

interface CycloneOverlayProps {
  data: CycloneData;
  selectedForecast: number | null;
  selectedHistorical: number | null;
  showTrack: boolean;
  onSelectForecast: (hoursAhead: number | null) => void;
  onSelectHistorical: (index: number | null) => void;
}

function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

function toDeg(rad: number): number {
  return (rad * 180) / Math.PI;
}

function bearing(from: [number, number], to: [number, number]): number {
  const dLon = toRad(to[1] - from[1]);
  const y = Math.sin(dLon) * Math.cos(toRad(to[0]));
  const x = Math.cos(toRad(from[0])) * Math.sin(toRad(to[0])) -
            Math.sin(toRad(from[0])) * Math.cos(toRad(to[0])) * Math.cos(dLon);
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

function offsetPoint(
  lat: number,
  lon: number,
  perpBearingDeg: number,
  distanceDeg: number
): [number, number] {
  const rlat = toRad(lat);
  const rlon = toRad(lon);
  const rb = toRad(perpBearingDeg);
  const d = toRad(distanceDeg);

  const newLat = toDeg(
    Math.asin(
      Math.sin(rlat) * Math.cos(d) +
      Math.cos(rlat) * Math.sin(d) * Math.cos(rb)
    )
  );
  const newLon = toDeg(
    rlon +
    Math.atan2(
      Math.sin(rb) * Math.sin(d) * Math.cos(rlat),
      Math.cos(d) - Math.sin(rlat) * Math.sin(toRad(newLat))
    )
  );

  return [newLat, newLon];
}

function generateCone(
  currentLat: number,
  currentLon: number,
  forecastPoints: ForecastPoint[]
): [number, number][] {
  if (forecastPoints.length === 0) return [];

  const left: [number, number][] = [];
  const right: [number, number][] = [];

  for (let i = 0; i < forecastPoints.length; i++) {
    const pt = forecastPoints[i];
    const halfWidth = pt.hoursAhead * 0.012;

    let b: number;
    if (i < forecastPoints.length - 1) {
      b = bearing(
        [pt.lat, pt.lon],
        [forecastPoints[i + 1].lat, forecastPoints[i + 1].lon]
      );
    } else {
      b = bearing(
        [forecastPoints[i - 1].lat, forecastPoints[i - 1].lon],
        [pt.lat, pt.lon]
      );
    }

    const perpLeft = (b + 90) % 360;
    const perpRight = (b + 270) % 360;

    left.push(offsetPoint(pt.lat, pt.lon, perpLeft, halfWidth));
    right.push(offsetPoint(pt.lat, pt.lon, perpRight, halfWidth));
  }

  const startLeft = offsetPoint(
    forecastPoints[0].lat,
    forecastPoints[0].lon,
    (bearing([currentLat, currentLon], [forecastPoints[0].lat, forecastPoints[0].lon]) + 90) % 360,
    forecastPoints[0].hoursAhead * 0.012
  );
  const startRight = offsetPoint(
    forecastPoints[0].lat,
    forecastPoints[0].lon,
    (bearing([currentLat, currentLon], [forecastPoints[0].lat, forecastPoints[0].lon]) + 270) % 360,
    forecastPoints[0].hoursAhead * 0.012
  );

  return [
    [currentLat, currentLon],
    startLeft,
    ...left,
    ...right.reverse(),
    startRight,
    [currentLat, currentLon],
  ];
}

export default function CycloneOverlay({
  data,
  selectedForecast,
  selectedHistorical,
  showTrack,
  onSelectForecast,
  onSelectHistorical,
}: CycloneOverlayProps) {
  const { track, current, forecast } = data;

  const trackPositions: [number, number][] = track.map((p) => [p.lat, p.lon]);
  const forecastPositions: [number, number][] = [
    [current.lat, current.lon],
    ...forecast.map((p): [number, number] => [p.lat, p.lon]),
  ];

  const conePositions = generateCone(current.lat, current.lon, forecast);

  return (
    <>
      {conePositions.length > 0 && (
        <Polygon
          positions={conePositions}
          pathOptions={{
            color: '#22c55e',
            weight: 1.5,
            opacity: 0.5,
            fillColor: '#22c55e',
            fillOpacity: 0.12,
            dashArray: '6, 4',
          }}
        />
      )}

      {showTrack && (
        <Polyline
          positions={trackPositions}
          pathOptions={{
            color: '#3b82f6',
            weight: 3,
            opacity: 0.85,
          }}
        />
      )}

      {showTrack && track.slice(0, -1).map((point, i) => {
        const isSelected = selectedHistorical === i;
        return (
          <CircleMarker
            key={i}
            center={[point.lat, point.lon]}
            radius={isSelected ? 5 : 3.5}
            pathOptions={{
              color: isSelected ? '#ffffff' : '#2563eb',
              fillColor: isSelected ? '#e2e8f0' : '#3b82f6',
              fillOpacity: isSelected ? 0.95 : 0.8,
              weight: isSelected ? 2 : 1.5,
            }}
            eventHandlers={{
              click: () => onSelectHistorical(isSelected ? null : i),
            }}
          >
            <Tooltip direction="top" offset={[0, -6]} opacity={0.9}>
              <span>
                {point.timestamp.replace('T', ' ')} IST
                {point.wind != null && <><br />Wind: {point.wind} km/h</>}
              </span>
            </Tooltip>
          </CircleMarker>
        );
      })}

      {showTrack && forecast.length > 0 && (
        <Polyline
          positions={forecastPositions}
          pathOptions={{
            color: '#22c55e',
            weight: 3,
            opacity: 0.9,
            dashArray: '10, 6',
          }}
        />
      )}

      {showTrack && forecast.map((point) => {
        const isSelected = selectedForecast === point.hoursAhead;
        return (
          <CircleMarker
            key={`fc-${point.hoursAhead}`}
            center={[point.lat, point.lon]}
            radius={isSelected ? 7 : 5}
            pathOptions={{
              color: isSelected ? '#ffffff' : '#22c55e',
              fillColor: '#22c55e',
              fillOpacity: isSelected ? 0.95 : 0.9,
              weight: isSelected ? 3 : 2,
            }}
            eventHandlers={{
              click: () => onSelectForecast(isSelected ? null : point.hoursAhead),
            }}
          >
            <Tooltip
              direction="top"
              offset={[0, -8]}
              opacity={0.95}
              permanent
            >
              <span style={{ fontSize: '11px', fontWeight: 600 }}>
                +{point.hoursAhead}h
              </span>
            </Tooltip>
            <Tooltip direction="right" offset={[8, 0]} opacity={0.9}>
              <span>
                <strong>{data.name}</strong><br />
                +{point.hoursAhead}h Forecast<br />
                {point.timestamp.replace('T', ' ')} IST<br />
                {point.lat.toFixed(1)}°N, {point.lon.toFixed(1)}°E<br />
                {point.wind != null && <>Wind: {point.wind} km/h</>}
              </span>
            </Tooltip>
          </CircleMarker>
        );
      })}

      <CircleMarker
        center={[current.lat, current.lon]}
        radius={10}
        pathOptions={{
          color: '#1d4ed8',
          fillColor: '#2563eb',
          fillOpacity: 0.95,
          weight: 3,
        }}
      />
      <CircleMarker
        center={[current.lat, current.lon]}
        radius={18}
        pathOptions={{
          color: '#3b82f6',
          fillColor: '#3b82f6',
          fillOpacity: 0.15,
          weight: 1,
        }}
      />
      <CircleMarker
        center={[current.lat, current.lon]}
        radius={28}
        pathOptions={{
          color: '#3b82f6',
          fillColor: '#3b82f6',
          fillOpacity: 0.06,
          weight: 1,
        }}
      >
        <Tooltip direction="top" offset={[0, -14]} opacity={0.95}>
          <span>
            <strong>{data.name}</strong><br />
            Current Position<br />
            {current.timestamp.replace('T', ' ')} IST<br />
            Wind: {current.wind} km/h
          </span>
        </Tooltip>
      </CircleMarker>
    </>
  );
}
