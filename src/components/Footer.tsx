import './Footer.css';

export default function Footer() {
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
