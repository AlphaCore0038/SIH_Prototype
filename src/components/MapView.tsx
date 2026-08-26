import { useRef, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import type { Map } from 'leaflet';
import type { CycloneData } from '../types/cyclone';
import CycloneOverlay from './CycloneOverlay';
import 'leaflet/dist/leaflet.css';
import './MapView.css';

const DEFAULT_CENTER: [number, number] = [14.5, 84.0];
const DEFAULT_ZOOM = 6;

function MapController({ mapRef }: { mapRef: React.MutableRefObject<Map | null> }) {
  const map = useMap();

  useEffect(() => {
    mapRef.current = map;
    map.invalidateSize();
  }, [map, mapRef]);

  return null;
}

interface MapViewProps {
  trackData?: CycloneData;
  selectedForecast: number | null;
  selectedHistorical: number | null;
  showTrack: boolean;
  onSelectForecast: (hoursAhead: number | null) => void;
  onSelectHistorical: (index: number | null) => void;
}

export default function MapView({
  trackData,
  selectedForecast,
  selectedHistorical,
  showTrack,
  onSelectForecast,
  onSelectHistorical,
}: MapViewProps) {
  const mapRef = useRef<Map | null>(null);

  const handleZoomIn = useCallback(() => {
    mapRef.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    mapRef.current?.zoomOut();
  }, []);

  const handleReset = useCallback(() => {
    mapRef.current?.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
  }, []);

  return (
    <div className="map-container">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        zoomControl={false}
        attributionControl={false}
        style={{ width: '100%', height: '100%' }}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
          attribution='&copy; <a href="https://carto.com/">CARTO</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        <MapController mapRef={mapRef} />
        {trackData && (
          <CycloneOverlay
            data={trackData}
            selectedForecast={selectedForecast}
            selectedHistorical={selectedHistorical}
            showTrack={showTrack}
            onSelectForecast={onSelectForecast}
            onSelectHistorical={onSelectHistorical}
          />
        )}
      </MapContainer>
      <div className="map-controls">
        <button className="map-control-btn" title="Layers">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 2 7 12 12 22 7 12 2"/>
            <polyline points="2 17 12 22 22 17"/>
            <polyline points="2 12 12 17 22 12"/>
          </svg>
        </button>
        <button className="map-control-btn" title="Reset view" onClick={handleReset}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <line x1="12" y1="2" x2="12" y2="6"/>
            <line x1="12" y1="18" x2="12" y2="22"/>
            <line x1="2" y1="12" x2="6" y2="12"/>
            <line x1="18" y1="12" x2="22" y2="12"/>
          </svg>
        </button>
        <div className="map-control-divider" />
        <button className="map-control-btn" title="Zoom in" onClick={handleZoomIn}>+</button>
        <button className="map-control-btn" title="Zoom out" onClick={handleZoomOut}>−</button>
      </div>
    </div>
  );
}
