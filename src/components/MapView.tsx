import { useRef, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Polyline, Tooltip, useMap } from 'react-leaflet';
import type { Map } from 'leaflet';
import type { CycloneData } from '../types/cyclone';
import { historicalCyclones } from '../data/historicalCyclones';
import CycloneOverlay from './CycloneOverlay';
import RiskOverlay from './RiskOverlay';
import 'leaflet/dist/leaflet.css';
import './MapView.css';

const DEFAULT_CENTER: [number, number] = [14.5, 84.0];
const DEFAULT_ZOOM = 6;

const SATELLITE_ATTR = '&copy; <a href="https://www.esri.com/">Esri</a> | Source: Esri, Maxar, Earthstar Geographics';
const DARK_ATTR = '&copy; <a href="https://carto.com/">CARTO</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

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
  showRisk: boolean;
  showSatellite: boolean;
  onSelectForecast: (hoursAhead: number | null) => void;
  onSelectHistorical: (index: number | null) => void;
}

export default function MapView({
  trackData,
  selectedForecast,
  selectedHistorical,
  showTrack,
  showRisk,
  showSatellite,
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
        {showSatellite ? (
          <>
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution={SATELLITE_ATTR}
              maxZoom={19}
            />
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png"
              subdomains="abcd"
              attribution=""
              opacity={0.35}
            />
          </>
        ) : (
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            subdomains="abcd"
            attribution={DARK_ATTR}
          />
        )}
        <MapController mapRef={mapRef} />
        {historicalCyclones.map((c) => (
          <Polyline
            key={`${c.name}-${c.year}`}
            positions={c.points}
            pathOptions={{
              color: '#94a3b8',
              weight: 1.5,
              opacity: 0.4,
              dashArray: '4, 4',
            }}
          >
            <Tooltip direction="top" offset={[0, -4]} opacity={0.8}>
              <span>{c.name} ({c.year}) — {c.category}</span>
            </Tooltip>
          </Polyline>
        ))}
        {showRisk && trackData && <RiskOverlay data={trackData} />}
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
      <div className="map-vignette" />
      <div className="map-scanline" />
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
