import './CurrentConditions.css';
import type { CycloneData } from '../types/cyclone';

interface CurrentConditionsProps {
  data: CycloneData;
}

function getWindLabel(wind: number): string {
  if (wind >= 120) return 'Hurricane Force';
  if (wind >= 90) return 'Very Strong';
  if (wind >= 60) return 'Strong';
  if (wind >= 40) return 'Moderate';
  return 'Weak';
}

function getPressureLabel(pressure: number): string {
  if (pressure < 950) return 'Very Low';
  if (pressure < 980) return 'Low';
  return 'Normal';
}

function getRainfallLabel(rainfall: number): string {
  if (rainfall >= 100) return 'Heavy';
  if (rainfall >= 50) return 'Moderate';
  return 'Light';
}

function getRiskStyle(level: CycloneData['riskLevel']): string {
  switch (level) {
    case 'EXTREME': return 'var(--accent-red)';
    case 'HIGH': return 'var(--accent-red)';
    case 'MODERATE': return 'var(--accent-yellow)';
    case 'LOW': return 'var(--accent-green)';
  }
}

function getRiskSubLabel(level: CycloneData['riskLevel']): string {
  switch (level) {
    case 'EXTREME': return 'Extreme Danger';
    case 'HIGH': return 'Take Action';
    case 'MODERATE': return 'Be Prepared';
    case 'LOW': return 'Monitor';
  }
}

export default function CurrentConditions({ data }: CurrentConditionsProps) {
  const { current, pressure, movementDir, movementSpeed, rainfall, riskLevel } = data;

  return (
    <section className="current-conditions">
      <div className="section-heading">Current Conditions</div>
      <div className="current-conditions-cards">
        <div className="condition-card">
          <div className="condition-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
            </svg>
            Wind
          </div>
          <div className="condition-card-value">
            {current.wind}<span className="condition-card-unit">km/h</span>
          </div>
          <div className="condition-card-sub condition-card-sub--strong">{getWindLabel(current.wind ?? 0)}</div>
        </div>

        <div className="condition-card">
          <div className="condition-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            Pressure
          </div>
          <div className="condition-card-value">
            {pressure}<span className="condition-card-unit">hPa</span>
          </div>
          <div className="condition-card-sub condition-card-sub--low">{getPressureLabel(pressure)}</div>
        </div>

        <div className="condition-card">
          <div className="condition-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12"/>
              <polyline points="12 5 19 12 12 19"/>
            </svg>
            Movement
          </div>
          <div className="condition-card-value">
            {movementDir}
          </div>
          <div className="condition-card-sub condition-card-sub--low">{movementSpeed} km/h</div>
        </div>

        <div className="condition-card">
          <div className="condition-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 13V4a4 4 0 0 0-8 0v9"/>
              <path d="M12 13a4 4 0 1 0 0 8H8"/>
              <line x1="8" y1="21" x2="8" y2="23"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="16" y1="21" x2="16" y2="23"/>
            </svg>
            Rainfall (24h)
          </div>
          <div className="condition-card-value">
            {rainfall}<span className="condition-card-unit">mm</span>
          </div>
          <div className="condition-card-sub condition-card-sub--heavy">{getRainfallLabel(rainfall)}</div>
        </div>

        <div className="condition-card">
          <div className="condition-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            Risk Level
          </div>
          <div className="condition-card-value" style={{ color: getRiskStyle(riskLevel) }}>
            {riskLevel}
          </div>
          <div className="condition-card-sub condition-card-sub--high">{getRiskSubLabel(riskLevel)}</div>
        </div>
      </div>
    </section>
  );
}
