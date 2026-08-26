import './ForecastPanel.css';
import type { CycloneData } from '../types/cyclone';
import { formatTime } from '../utils/format';

interface ForecastPanelProps {
  data: CycloneData;
  selectedForecast: number | null;
  onSelectForecast: (hoursAhead: number | null) => void;
}

export default function ForecastPanel({ data, selectedForecast, onSelectForecast }: ForecastPanelProps) {
  return (
    <section className="forecast-panel">
      <div className="section-heading">
        Forecast <span style={{ fontWeight: 400, letterSpacing: 0, textTransform: 'none', fontSize: 11 }}>(Cyclone Center Position)</span>
      </div>
      <div className="forecast-grid">
        {data.forecast.map((point) => {
          const isSelected = selectedForecast === point.hoursAhead;
          return (
            <div
              key={point.hoursAhead}
              className={`forecast-col ${isSelected ? 'forecast-col--selected' : ''}`}
              onClick={() => onSelectForecast(isSelected ? null : point.hoursAhead)}
            >
              <div className="forecast-col-header">
                <span className="forecast-col-hours">+{point.hoursAhead}h</span>
                <span className="forecast-col-clock">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                </span>
              </div>
              <div className="forecast-col-time">
                {formatTime(point.timestamp)}
                {point.hoursAhead >= 24 && (
                  <span className="forecast-col-time-note"> ({point.timestamp.substring(8, 10)} Aug)</span>
                )}
              </div>
              <div className="forecast-col-lat">{point.lat.toFixed(1)}°N</div>
              <div className="forecast-col-lon">{point.lon.toFixed(1)}°E</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
