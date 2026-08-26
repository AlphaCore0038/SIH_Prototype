import './OverviewPanel.css';
import type { CycloneData } from '../types/cyclone';

interface OverviewPanelProps {
  data: CycloneData;
}

function getStatusLabel(category: string): { label: string; severity: string } {
  const lower = category.toLowerCase();
  if (lower.includes('extremely')) return { label: 'EXTREME', severity: 'extreme' };
  if (lower.includes('severe')) return { label: 'SEVERE', severity: 'severe' };
  if (lower.includes('very')) return { label: 'VERY STRONG', severity: 'strong' };
  if (lower.includes('cyclonic')) return { label: 'MODERATE', severity: 'moderate' };
  return { label: 'LOW', severity: 'low' };
}

export default function OverviewPanel({ data }: OverviewPanelProps) {
  const count = data.track.length > 0 ? '01' : '00';
  const { label: statusLabel } = getStatusLabel(data.category);

  return (
    <aside className="overview-panel">
      <div className="section-heading">Overview</div>

      <div className="overview-count-label">Cyclones</div>
      <div className="overview-count-value">{count}</div>

      <div className="overview-divider" />

      <div className="overview-status-label">Status</div>
      <div className="overview-status-value">{statusLabel}</div>
      <div className="overview-status-sub">{data.category}</div>

      <div className="overview-confidence-label">Confidence</div>
      <div className="overview-confidence-value">{data.confidence}%</div>
      <div className="overview-confidence-bar-track">
        <div className="overview-confidence-bar-fill" style={{ width: `${data.confidence}%` }} />
      </div>
    </aside>
  );
}
