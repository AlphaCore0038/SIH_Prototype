import { useState } from 'react';
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

export default function App() {
  const [selectedForecast, setSelectedForecast] = useState<number | null>(null);
  const [selectedHistorical, setSelectedHistorical] = useState<number | null>(null);
  const [showTrack, setShowTrack] = useState(true);
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="dashboard">
      <Header data={mockCyclone} />
      <OverviewPanel data={mockCyclone} />
      <div className="map-area-wrapper">
        <MapView
          trackData={mockCyclone}
          selectedForecast={selectedForecast}
          selectedHistorical={selectedHistorical}
          showTrack={showTrack}
          onSelectForecast={setSelectedForecast}
          onSelectHistorical={setSelectedHistorical}
        />
        <LayerBar showTrack={showTrack} onToggleTrack={() => setShowTrack(prev => !prev)} />
      </div>
      <CycloneInfo data={mockCyclone} onViewDetails={() => setShowDetails(true)} />
      <div className="bottom-area">
        <CurrentConditions data={mockCyclone} />
        <ForecastPanel
          data={mockCyclone}
          selectedForecast={selectedForecast}
          onSelectForecast={setSelectedForecast}
        />
      </div>
      <Footer />
      {showDetails && <DetailsPanel data={mockCyclone} onClose={() => setShowDetails(false)} />}
    </div>
  );
}
