import { Circle, Tooltip } from 'react-leaflet';
import type { CycloneData } from '../types/cyclone';
import './RiskOverlay.css';

interface RiskOverlayProps {
  data: CycloneData;
}

const ZONES = [
  { label: 'EXTREME', radius: 50000, color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.12 },
  { label: 'VERY HIGH', radius: 120000, color: '#f97316', fillColor: '#f97316', fillOpacity: 0.08 },
  { label: 'HIGH', radius: 200000, color: '#eab308', fillColor: '#eab308', fillOpacity: 0.05 },
  { label: 'MODERATE', radius: 320000, color: '#94a3b8', fillColor: '#94a3b8', fillOpacity: 0.03 },
] as const;

export default function RiskOverlay({ data }: RiskOverlayProps) {
  const { current } = data;
  const center: [number, number] = [current.lat, current.lon];

  return (
    <>
      {ZONES.map((zone) => (
        <Circle
          key={zone.label}
          center={center}
          radius={zone.radius}
          pathOptions={{
            color: zone.color,
            weight: 1,
            opacity: 0.4,
            fillColor: zone.fillColor,
            fillOpacity: zone.fillOpacity,
          }}
        >
          <Tooltip direction="center" permanent opacity={0.85}>
            <span className="risk-zone-label">{zone.label}</span>
          </Tooltip>
        </Circle>
      ))}

      <div className="risk-legend">
        <div className="risk-legend-title">Prototype Risk Assessment</div>
        {ZONES.map((zone) => (
          <div key={zone.label} className="risk-legend-item">
            <span className="risk-legend-swatch" style={{ background: zone.color }} />
            <span className="risk-legend-label">{zone.label}</span>
          </div>
        ))}
        <div className="risk-legend-disclaimer">
          Demonstration visualization — not an operational hazard forecast.
        </div>
      </div>
    </>
  );
}
