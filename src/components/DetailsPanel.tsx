import type { CycloneData, TrackPoint } from '../types/cyclone';
import { formatDateTime, formatTime } from '../utils/format';
import './DetailsPanel.css';

interface DetailsPanelProps {
  data: CycloneData;
  onClose: () => void;
}

function computeIntensityTrend(track: TrackPoint[]): { label: string; delta: number } {
  if (track.length < 2) return { label: 'Stable', delta: 0 };
  const first = track[0].wind ?? 0;
  const last = track[track.length - 1].wind ?? 0;
  const delta = last - first;
  if (delta > 30) return { label: 'Rapidly Intensifying', delta };
  if (delta > 10) return { label: 'Intensifying', delta };
  if (delta > 0) return { label: 'Gradually Strengthening', delta };
  if (delta === 0) return { label: 'Stable', delta };
  return { label: 'Weakening', delta };
}

function computeTrackDirection(track: TrackPoint[]): string {
  if (track.length < 2) return 'N/A';
  const first = track[0];
  const last = track[track.length - 1];
  const dLat = last.lat - first.lat;
  const dLon = last.lon - first.lon;
  const angle = (Math.atan2(dLon, dLat) * 180) / Math.PI;
  const normalized = (angle + 360) % 360;
  if (normalized < 22.5 || normalized >= 337.5) return 'North';
  if (normalized < 67.5) return 'Northeast';
  if (normalized < 112.5) return 'East';
  if (normalized < 157.5) return 'Southeast';
  if (normalized < 202.5) return 'South';
  if (normalized < 247.5) return 'Southwest';
  if (normalized < 292.5) return 'West';
  return 'Northwest';
}

function computeForecastDisplacement(
  current: TrackPoint,
  forecastPoints: TrackPoint[]
): { maxLat: number; maxLon: number } {
  const maxLat = Math.max(...forecastPoints.map((p) => p.lat)) - current.lat;
  const maxLon = Math.max(...forecastPoints.map((p) => p.lon)) - current.lon;
  return { maxLat, maxLon };
}

function getConfidenceLabel(confidence: number): string {
  if (confidence >= 90) return 'High confidence';
  if (confidence >= 70) return 'Moderate confidence';
  if (confidence >= 50) return 'Low confidence';
  return 'Very low confidence';
}

function Sparkline({ track }: { track: TrackPoint[] }) {
  const winds = track.map((p) => p.wind ?? 0);
  const max = Math.max(...winds);
  const min = Math.min(...winds);
  const range = max - min || 1;
  const width = 200;
  const height = 48;
  const padding = 4;

  const points = winds.map((w, i) => {
    const x = padding + (i / (winds.length - 1)) * (width - padding * 2);
    const y = height - padding - ((w - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="sparkline">
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke="#ff6b00"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {winds.map((w, i) => {
        const x = padding + (i / (winds.length - 1)) * (width - padding * 2);
        const y = height - padding - ((w - min) / range) * (height - padding * 2);
        const isLast = i === winds.length - 1;
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r={isLast ? 3.5 : 2}
            fill={isLast ? '#ff6b00' : '#94a3b8'}
            stroke={isLast ? '#ffffff' : 'none'}
            strokeWidth={isLast ? 1.5 : 0}
          />
        );
      })}
    </svg>
  );
}

export default function DetailsPanel({ data, onClose }: DetailsPanelProps) {
  const { current, track, forecast, name, category, confidence, pressure, movementDir, movementSpeed, rainfall, riskLevel } = data;

  const intensityTrend = computeIntensityTrend(track);
  const trackDirection = computeTrackDirection(track);
  const displacement = computeForecastDisplacement(current, forecast);
  const forecastMaxWind = Math.max(...forecast.map((p) => p.wind ?? -Infinity));
  const windFirst = track[0].wind ?? 0;
  const windLast = track[track.length - 1].wind ?? 0;

  return (
    <div className="details-backdrop" onClick={onClose}>
      <div className="details-panel" onClick={(e) => e.stopPropagation()}>
        <div className="details-header">
          <div className="details-header-text">
            <div className="details-title">Cyclone Intelligence</div>
            <div className="details-subtitle">{name} — {category}</div>
          </div>
          <button className="details-close" onClick={onClose}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="details-body">
          <section className="details-section">
            <div className="details-section-heading">Current Conditions</div>
            <div className="details-grid">
              <div className="details-kv"><span className="details-kv-label">Wind</span><span className="details-kv-value">{current.wind} km/h</span></div>
              <div className="details-kv"><span className="details-kv-label">Pressure</span><span className="details-kv-value">{pressure} hPa</span></div>
              <div className="details-kv"><span className="details-kv-label">Movement</span><span className="details-kv-value">{movementDir} @ {movementSpeed} km/h</span></div>
              <div className="details-kv"><span className="details-kv-label">Rainfall (24h)</span><span className="details-kv-value">{rainfall} mm</span></div>
              <div className="details-kv"><span className="details-kv-label">Risk Level</span><span className={`details-kv-value details-risk--${riskLevel.toLowerCase()}`}>{riskLevel}</span></div>
            </div>
          </section>

          <section className="details-section">
            <div className="details-section-heading">Position</div>
            <div className="details-grid">
              <div className="details-kv"><span className="details-kv-label">Latitude</span><span className="details-kv-value">{current.lat.toFixed(1)}°N</span></div>
              <div className="details-kv"><span className="details-kv-label">Longitude</span><span className="details-kv-value">{current.lon.toFixed(1)}°E</span></div>
              <div className="details-kv"><span className="details-kv-label">Timestamp</span><span className="details-kv-value">{formatDateTime(current.timestamp)}</span></div>
            </div>
          </section>

          <section className="details-section">
            <div className="details-section-heading">Intensity Trend</div>
            <div className="details-sparkline-row">
              <Sparkline track={track} />
            </div>
            <div className="details-grid">
              <div className="details-kv"><span className="details-kv-label">Status</span><span className="details-kv-value details-kv-value--accent">{intensityTrend.label}</span></div>
              <div className="details-kv"><span className="details-kv-label">Initial Wind</span><span className="details-kv-value">{windFirst} km/h</span></div>
              <div className="details-kv"><span className="details-kv-label">Current Wind</span><span className="details-kv-value">{windLast} km/h</span></div>
              <div className="details-kv"><span className="details-kv-label">Change</span><span className="details-kv-value">+{intensityTrend.delta} km/h</span></div>
            </div>
          </section>

          <section className="details-section">
            <div className="details-section-heading">Movement</div>
            <div className="details-grid">
              <div className="details-kv"><span className="details-kv-label">Overall Direction</span><span className="details-kv-value details-kv-value--accent">{trackDirection}</span></div>
              <div className="details-kv"><span className="details-kv-label">Current Movement</span><span className="details-kv-value">{movementDir} @ {movementSpeed} km/h</span></div>
            </div>
          </section>

          <section className="details-section">
            <div className="details-section-heading">Forecast Summary</div>
            <div className="details-forecast-list">
              {forecast.map((point) => (
                <div key={point.hoursAhead} className="details-forecast-item">
                  <span className="details-forecast-hours">+{point.hoursAhead}h</span>
                  <span className="details-forecast-time">{formatTime(point.timestamp)}</span>
                  <span className="details-forecast-coord">{point.lat.toFixed(1)}°N, {point.lon.toFixed(1)}°E</span>
                  <span className="details-forecast-wind">{point.wind != null ? `${point.wind} km/h` : 'N/A'}</span>
                </div>
              ))}
            </div>
            <div className="details-grid" style={{ marginTop: '8px' }}>
              <div className="details-kv"><span className="details-kv-label">Max Forecast Wind</span><span className="details-kv-value details-kv-value--accent">{Number.isFinite(forecastMaxWind) ? `${forecastMaxWind} km/h` : 'N/A'}</span></div>
              <div className="details-kv"><span className="details-kv-label">Lat Displacement</span><span className="details-kv-value">+{displacement.maxLat.toFixed(1)}°</span></div>
              <div className="details-kv"><span className="details-kv-label">Lon Displacement</span><span className="details-kv-value">+{displacement.maxLon.toFixed(1)}°</span></div>
            </div>
          </section>

          <section className="details-section">
            <div className="details-section-heading">Model Confidence</div>
            <div className="details-confidence-bar">
              <div className="details-confidence-fill" style={{ width: `${confidence}%` }} />
            </div>
            <div className="details-grid">
              <div className="details-kv"><span className="details-kv-label">Confidence</span><span className="details-kv-value details-kv-value--green">{confidence}%</span></div>
              <div className="details-kv"><span className="details-kv-label">Assessment</span><span className="details-kv-value">{getConfidenceLabel(confidence)}</span></div>
            </div>
          </section>

          <div className="details-disclaimer">
            Prototype analysis derived from demonstration cyclone data. Not operational meteorological intelligence.
          </div>
        </div>
      </div>
    </div>
  );
}
