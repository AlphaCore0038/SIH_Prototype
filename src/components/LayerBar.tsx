import './LayerBar.css';

const layers = [
  { id: 'satellite', label: 'Satellite', active: true, disabled: false },
  { id: 'track', label: 'Track', active: false, disabled: false },
  { id: 'rain', label: 'Rain', active: false, disabled: true },
  { id: 'wind', label: 'Wind', active: false, disabled: true },
  { id: 'risk', label: 'Risk', active: false, disabled: false },
];

interface LayerBarProps {
  showTrack: boolean;
  showRisk: boolean;
  showSatellite: boolean;
  onToggleTrack: () => void;
  onToggleRisk: () => void;
  onToggleSatellite: () => void;
}

function LayerIcon({ id }: { id: string }) {
  switch (id) {
    case 'satellite':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="2" y1="12" x2="22" y2="12"/>
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
        </svg>
      );
    case 'track':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="4 12 8 8 12 14 16 6 20 12"/>
          <circle cx="4" cy="12" r="1.5" fill="currentColor"/>
          <circle cx="20" cy="12" r="1.5" fill="currentColor"/>
        </svg>
      );
    case 'rain':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 13V4a4 4 0 0 0-8 0v9"/>
          <path d="M12 13a4 4 0 1 0 0 8H8"/>
          <line x1="8" y1="21" x2="8" y2="23"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="16" y1="21" x2="16" y2="23"/>
        </svg>
      );
    case 'wind':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
        </svg>
      );
    case 'risk':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      );
    default:
      return null;
  }
}

export default function LayerBar({ showTrack, showRisk, showSatellite, onToggleTrack, onToggleRisk, onToggleSatellite }: LayerBarProps) {
  return (
    <div className="layer-bar">
      {layers.map((layer) => {
        if (layer.id === 'satellite') {
          return (
            <button
              key={layer.id}
              className={`layer-btn ${showSatellite ? 'layer-btn--active' : ''}`}
              onClick={onToggleSatellite}
            >
              <span className="layer-btn-icon">
                <LayerIcon id={layer.id} />
              </span>
              {layer.label}
            </button>
          );
        }

        if (layer.id === 'track') {
          return (
            <button
              key={layer.id}
              className={`layer-btn ${showTrack ? 'layer-btn--active' : ''}`}
              onClick={onToggleTrack}
            >
              <span className="layer-btn-icon">
                <LayerIcon id={layer.id} />
              </span>
              {layer.label}
            </button>
          );
        }

        if (layer.id === 'risk') {
          return (
            <button
              key={layer.id}
              className={`layer-btn ${showRisk ? 'layer-btn--active' : ''}`}
              onClick={onToggleRisk}
            >
              <span className="layer-btn-icon">
                <LayerIcon id={layer.id} />
              </span>
              {layer.label}
            </button>
          );
        }

        return (
          <button
            key={layer.id}
            className={`layer-btn ${layer.active ? 'layer-btn--active' : ''}`}
            disabled={layer.disabled}
          >
            <span className="layer-btn-icon">
              <LayerIcon id={layer.id} />
            </span>
            {layer.label}
          </button>
        );
      })}
    </div>
  );
}
