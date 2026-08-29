import { useEffect, useState } from 'react';
import './App.css';
import Header from './components/Header';
import OverviewPanel from './components/OverviewPanel';
import MapView from './components/MapView';
import LayerBar from './components/LayerBar';
import CurrentConditions from './components/CurrentConditions';
import ForecastPanel from './components/ForecastPanel';
import CycloneInfo from './components/CycloneInfo';
import DetailsPanel from './components/DetailsPanel';
import Footer from './components/Footer';
import { mockCyclone } from './data/mockCyclone';
import { fetchMlForecast } from './services/mlApi';
import type { CycloneData } from './types/cyclone';

export type ModelStatus = 'loading' | 'ml' | 'unavailable';

function addHoursToTimestamp(iso: string, hours: number): string {
  const d = new Date(iso);
  d.setHours(d.getHours() + hours);
  return d.toISOString().replace('.000Z', '');
}

export default function App() {
  const [selectedForecast, setSelectedForecast] = useState<number | null>(null);
  const [selectedHistorical, setSelectedHistorical] = useState<number | null>(null);
  const [showTrack, setShowTrack] = useState(true);
  const [showRisk, setShowRisk] = useState(false);
  const [showSatellite, setShowSatellite] = useState(true);
  const [showDetails, setShowDetails] = useState(false);
  const [cyclone, setCyclone] = useState<CycloneData>(mockCyclone);
  const [modelStatus, setModelStatus] = useState<ModelStatus>('loading');

  useEffect(() => {
    async function loadMlForecast() {
      try {
        const input = mockCyclone.track.slice(-4).map((p) => ({
          lat: p.lat,
          lon: p.lon,
          wind: p.wind,
          timestamp: p.timestamp,
        }));
        const mlPoints = await fetchMlForecast(input);
        const forecast = mlPoints.map((p) => ({
          ...p,
          timestamp: addHoursToTimestamp(mockCyclone.current.timestamp, p.hoursAhead),
        }));
        setCyclone({ ...mockCyclone, forecast });
        setModelStatus('ml');
      } catch {
        setModelStatus('unavailable');
      }
    }
    loadMlForecast();
  }, []);

  return (
    <div className="dashboard">
      <Header data={cyclone} />
      <OverviewPanel data={cyclone} />
      <div className="map-area-wrapper">
        <MapView
          trackData={cyclone}
          selectedForecast={selectedForecast}
          selectedHistorical={selectedHistorical}
          showTrack={showTrack}
          showRisk={showRisk}
          showSatellite={showSatellite}
          onSelectForecast={setSelectedForecast}
          onSelectHistorical={setSelectedHistorical}
        />
        <LayerBar
          showTrack={showTrack}
          showRisk={showRisk}
          showSatellite={showSatellite}
          onToggleTrack={() => setShowTrack(prev => !prev)}
          onToggleRisk={() => setShowRisk(prev => !prev)}
          onToggleSatellite={() => setShowSatellite(prev => !prev)}
        />
      </div>
      <CycloneInfo data={cyclone} onViewDetails={() => setShowDetails(true)} />
      <div className="bottom-area">
        <CurrentConditions data={cyclone} />
        <ForecastPanel
          data={cyclone}
          selectedForecast={selectedForecast}
          onSelectForecast={setSelectedForecast}
        />
      </div>
      <Footer modelStatus={modelStatus} />
      {showDetails && <DetailsPanel data={cyclone} onClose={() => setShowDetails(false)} />}
    </div>
  );
}
