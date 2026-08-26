import './Header.css';
import type { CycloneData } from '../types/cyclone';
import { formatHeaderDate, formatHeaderTime } from '../utils/format';

interface HeaderProps {
  data: CycloneData;
}

export default function Header({ data }: HeaderProps) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" opacity="0.3"/>
            <path d="M12 2c-2 3-3 6-3 10s1 7 3 10"/>
            <path d="M12 2c2 3 3 6 3 10s-1 7-3 10"/>
            <path d="M2 12h20"/>
            <circle cx="12" cy="12" r="2" fill="currentColor" opacity="0.6"/>
          </svg>
        </div>
        <div className="header-brand">
          <span className="header-brand-cyclone">CYCLONE</span>
          <span className="header-brand-intel">INTELLIGENCE</span>
        </div>
      </div>
      <div className="header-right">
        <div className="header-live">
          <span className="header-live-dot" />
          ACTIVE
        </div>
        <span className="header-datetime">
          {formatHeaderDate(data.current.timestamp)}<span className="header-datetime-sep">|</span>{formatHeaderTime(data.current.timestamp)}
        </span>
        <div className="header-bell">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
        </div>
      </div>
    </header>
  );
}
