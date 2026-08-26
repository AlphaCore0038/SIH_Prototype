import './CycloneInfo.css';
import type { CycloneData } from '../types/cyclone';
import { formatDateTime, formatCoord } from '../utils/format';

interface CycloneInfoProps {
  data: CycloneData;
  onViewDetails: () => void;
}

export default function CycloneInfo({ data, onViewDetails }: CycloneInfoProps) {
  const { current } = data;

  return (
    <aside className="cyclone-info">
      <div className="section-heading">Cyclone Information</div>

      <div className="cyclone-info-header">
        <div className="cyclone-info-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" opacity="0.3"/>
            <path d="M12 2c-2 3-3 6-3 10s1 7 3 10"/>
            <path d="M12 2c2 3 3 6 3 10s-1 7-3 10"/>
            <path d="M2 12h20"/>
            <circle cx="12" cy="12" r="2" fill="currentColor" opacity="0.6"/>
          </svg>
        </div>
        <div>
          <div className="cyclone-info-name">{data.name}</div>
          <div className="cyclone-info-type">{data.category}</div>
        </div>
      </div>

      <div className="cyclone-info-details">
        <div className="cyclone-info-row">
          <span className="cyclone-info-row-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Date / Time
          </span>
          <span className="cyclone-info-row-value">{formatDateTime(current.timestamp)}</span>
        </div>
        <div className="cyclone-info-row">
          <span className="cyclone-info-row-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
            Location
          </span>
          <span className="cyclone-info-row-value">{formatCoord(current.lat, current.lon)}</span>
        </div>
        <div className="cyclone-info-row">
          <span className="cyclone-info-row-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/></svg>
            Max Wind
          </span>
          <span className="cyclone-info-row-value">{current.wind} km/h</span>
        </div>
        <div className="cyclone-info-row">
          <span className="cyclone-info-row-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Pressure
          </span>
          <span className="cyclone-info-row-value">{data.pressure} hPa</span>
        </div>
        <div className="cyclone-info-row">
          <span className="cyclone-info-row-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
            Movement
          </span>
          <span className="cyclone-info-row-value">{data.movementDir} @ {data.movementSpeed} km/h</span>
        </div>
        <div className="cyclone-info-row">
          <span className="cyclone-info-row-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            Confidence
          </span>
          <span className="cyclone-info-row-value cyclone-info-row-value--green">{data.confidence}%</span>
        </div>
      </div>

      <button className="cyclone-info-view-btn" onClick={onViewDetails}>
        View Details
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </button>
    </aside>
  );
}
