import './Footer.css';
import type { ModelStatus } from '../App';

const STATUS_CONFIG: Record<ModelStatus, { label: string; color: string }> = {
  loading: { label: 'CONNECTING...', color: '#eab308' },
  ml: { label: 'ML FORECAST', color: '#22c55e' },
  unavailable: { label: 'DEMO \u2014 API OFFLINE', color: '#eab308' },
};

interface FooterProps {
  modelStatus?: ModelStatus;
}

export default function Footer({ modelStatus }: FooterProps) {
  const status = modelStatus ? STATUS_CONFIG[modelStatus] : null;

  return (
    <footer className="footer">
      <div className="footer-sources">
        <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Data Sources:</span>
        <span className="footer-source">
          <span className="footer-source-icon">
            <svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/></svg>
          </span>
          INSAT-3D (MOSDAC)
        </span>
        <span className="footer-source">
          <span className="footer-source-icon">
            <svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/></svg>
          </span>
          GOES-16 (NOAA)
        </span>
        <span className="footer-source">
          <span className="footer-source-icon">
            <svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/></svg>
          </span>
          EUMETSAT (Meteosat)
        </span>
      </div>
      {status && (
        <div className="footer-model-status">
          <span className="footer-status-dot" style={{ background: status.color }} />
          <span className="footer-status-label">{status.label}</span>
        </div>
      )}
      <div className="footer-ministry">
        <span className="footer-ministry-emblem">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 21h18"/>
            <path d="M5 21V7l7-4 7 4v14"/>
            <path d="M9 21v-6h6v6"/>
          </svg>
        </span>
        Ministry of Earth Sciences, India
      </div>
    </footer>
  );
}
