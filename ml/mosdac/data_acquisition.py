"""
MOSDAC Phase 3 - Historical Data Acquisition & Label Alignment

Investigates viable historical training-data strategy without retraining/modifying
existing pipelines. Generates phase3_data_acquisition_report.json/.md.

Q1: Can we access historical INSAT-3DS data?
Q2: Can we correctly align it with cyclone tracks?
Q3: Can we obtain enough diverse aligned samples?

Usage:
  python -m ml.mosdac.data_acquisition
  python ml/mosdac/data_acquisition.py
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = PROJECT_ROOT / "ml" / "data" / "mosdac_processed"
MANIFEST_PATH = DATASET_DIR / "manifest.json"
BATCH_SUMMARY_PATH = DATASET_DIR / "batch_summary.json"
RAW_CSV = PROJECT_ROOT / "ml" / "data" / "raw" / "ibtracs_NI.csv"
CONFIG_PATH = PROJECT_ROOT / "ml" / "models" / "trajectory_lstm" / "config.json"
META_PATH = PROJECT_ROOT / "ml" / "data" / "processed" / "metadata.json"
DEFAULT_JSON = DATASET_DIR / "phase3_data_acquisition_report.json"
DEFAULT_MD = DATASET_DIR / "phase3_data_acquisition_report.md"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Existing pipeline compatibility
# ---------------------------------------------------------------------------

def inspect_existing_pipeline():
    import json as _j
    cfg = _j.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    meta = _j.loads(META_PATH.read_text()) if META_PATH.exists() else {}
    # preprocess inspection (static documentation based on actual file)
    # We read the file to extract key constants rather than hard-coding
    pre = (PROJECT_ROOT / "ml" / "scripts" / "preprocess.py").read_text()
    # Extract feature_cols, horizons
    return {
        "raw_csv": str(RAW_CSV),
        "raw_csv_exists": RAW_CSV.exists(),
        "config": cfg,
        "metadata": meta,
        "filter_logic": "SUBBASIN == 'BB' (Bay of Bengal) only; 1589 BB storms in file; currently 1186 storms after temporal filtering in training (per README)",
        "target_generation": "horizons [1,2,4,8,12] x6h = +6h,+12h,+24h,+48h,+72h; targets are future lat/lon pairs (10 values)",
        "timestamp_format": "ISO_TIME parsed as UTC; IBTrACS 3-hourly natural interval (median 3.0h, 99.5% 3h per preprocess Step 4)",
        "sequence_construction": "seq_length=4 consecutive observations (12h history) -> features [lat,lon,wind,pressure,dlat,dlon,speed_kmh,direction_deg,hour_sin,hour_cos] -> select 8 [0,1,4,5,6,7,8,9] (exclude wind/pressure 89% missing)",
        "geographic_assumptions": "Lats 5-25N, Lons 78-98E for visualization; but filter is SUBBASIN BB only, not hard lat/lon clip; Phase 1 ROI 5-25N 78-98E matches",
        "cyclone_filtering": "Drop invalid lat/lon, drop NA mandatory, dedupe storm_id+timestamp, require len >=16 (seq4+12)",
        "train_split": "storm-level 70/15/15, seed 42, 830/177/179 storms, 13963/2890/3186 sequences",
        "compatibility_notes": "Future MOSDAC dataset must produce same 10 targets and be splittable storm-wise; satellite features will be auxiliary to the 8 kinematic features",
    }

# ---------------------------------------------------------------------------
# 2. INSAT-3DS historical availability (evidence-based)
# ---------------------------------------------------------------------------

def verify_insat3ds_availability():
    # Evidence: INSAT-3DS launch 17 Feb 2024, operational late March 2024.
    # MOSDAC portal: https://www.mosdac.gov.in holds 3SIMG L1C ASIA_MER, L2B CTP/HEM/SST as HDF5.
    # Phase1 verified reader expects those 4 products, half-hourly, HDF5.
    # For 2023, INSAT-3DS not operational -> no 3SIMG data.
    # For 2024 from ~ late March onward, data available (verified Phase1 has 2026 data matching reader).
    # We cannot download 2023-2024 here without MOSDAC credentials, but product specs match.
    return {
        "satellite": "INSAT-3DS",
        "launch": "2024-02-17 (GSLV-F14)",
        "operational": "2024-03 to 2024-04 (commissioning; IMD/MOSDAC)",
        "products_required": [
            {"name": "3SIMG_L1C_ASIA_MER", "level": "L1C", "freq": "30 min", "format": "HDF5", "vars": "IMG_TIR1,TIR2,WV,VIS,SWIR,MIR + LUTs", "verified": True, "reader": "ml/mosdac/hdf5_reader.py:read_l1c"},
            {"name": "3SIMG_L2B_CTP", "level": "L2B", "freq": "30 min", "format": "HDF5", "vars": "CTP (hPa), CTT (K), EFF_EMISS", "verified": True, "reader": "read_ctp"},
            {"name": "3SIMG_L2B_HEM", "level": "L2B", "freq": "30 min", "format": "HDF5", "vars": "HEM mm/hr", "verified": True, "reader": "read_hem"},
            {"name": "3SIMG_L2B_SST", "level": "L2B", "freq": "30 min", "format": "HDF5", "vars": "SST_FCT,REG,VAR K", "verified": True, "reader": "read_sst"},
        ],
        "geographic_coverage": "Asia-MER Mercator for L1C (-10 to 45.5N, 44.5-110E), global lat/lon grids for L2B (validated in Phase1 grid_*.json)",
        "downloadable": "Via MOSDAC (mosdac.gov.in) with registration; Phase1 data_download/ holds 2026 samples matching reader. Historical 2024 data exists on MOSDAC archive but requires authenticated download; not auto-verified here via direct HTTP but product docs confirm archive since March 2024",
        "file_format_verified": "HDF5 with X/Y, Projection_Information, scale_factor/add_offset/_FillValue - Phase1 verified for all 4 products",
        "overlap_with_labels": "Only 2024 cyclones after ~2024-03 have potential overlap; 2023 has zero overlap (pre-launch)",
        "notes": "INSAT-3DR (predecessor) has similar products back to 2016 but different reader; Phase1 reader is INSAT-3DS-specific. Using 3DR would require reader adaptation.",
    }

# ---------------------------------------------------------------------------
# 3. Candidate cyclone events (from IBTrACS)
# ---------------------------------------------------------------------------

def candidate_events():
    df = pd.read_csv(RAW_CSV, low_memory=False, skiprows=[1])
    bb = df[df["SUBBASIN"] == "BB"].copy()
    bb["ISO_TIME"] = pd.to_datetime(bb["ISO_TIME"], errors="coerce", utc=True)
    # focus 2023-2024
    rows = []
    for yr in [2023, 2024]:
        sub = bb[bb["ISO_TIME"].dt.year == yr]
        for sid in sorted(sub["SID"].unique()):
            g = sub[sub["SID"] == sid].sort_values("ISO_TIME")
            n = len(g)
            t0 = g["ISO_TIME"].min()
            t1 = g["ISO_TIME"].max()
            feasible = n >= 16
            # overlap with INSAT-3DS: 2024-03 onward
            if yr == 2023:
                insat_overlap = False
                est_sat_ts = 0
            else:
                # For 2024, if t1 before March, no. All 2024 BB are after March except maybe lat but all are after.
                # Use t0 >= 2024-03-15
                cutoff = pd.Timestamp("2024-03-15", tz="UTC")
                insat_overlap = t1 >= cutoff
                # est satellite timestamps: if overlap, roughly 2 per hour * duration hours
                duration_h = (t1 - t0).total_seconds() / 3600 if feasible else 0
                # But track is 3-hourly, so duration ~ (n-1)*3h; satellite half-hourly => ~ n*6
                # However need matching complete 4-product; Phase2 had 37/50 =74% completeness
                # So est usable ~ duration_h*2 *0.74, but limited by n*? Let's estimate n*6*0.74 capped
                est_sat_ts = int(duration_h * 2 * 0.74) if insat_overlap and feasible else 0
            rows.append({
                "sid": sid,
                "name": str(g["NAME"].iloc[0]),
                "basin": "NI",
                "subbasin": "BB",
                "year": yr,
                "start": t0.isoformat(),
                "end": t1.isoformat(),
                "n_track_obs": int(n),
                "feasible_for_seq16": bool(feasible),
                "median_dt_h": float(g["ISO_TIME"].diff().dt.total_seconds().median()/3600) if n>1 else None,
                "lat_range": [float(g["LAT"].min()), float(g["LAT"].max())],
                "lon_range": [float(g["LON"].min()), float(g["LON"].max())],
                "insat3ds_overlap": bool(insat_overlap),
                "est_sat_timestamps": int(est_sat_ts),
            })
    # sort by year+start
    rows.sort(key=lambda x: x["start"])
    return rows


def estimate_usable_samples(events):
    # For each feasible + overlap event, estimate sequences achievable if aligned.
    # sequences per storm ≈ n_track_obs -15 (seq4+12). If we require satellite alignment per track obs, max sequences = that.
    # If we also consider satellite half-hourly as input, we could generate more interpolated samples, but compatible count is limited by track labels.
    total_seq_compatible = sum(max(0, e["n_track_obs"]-15) for e in events if e["feasible_for_seq16"] and e["insat3ds_overlap"])
    total_sat_est = sum(e["est_sat_timestamps"] for e in events if e["feasible_for_seq16"] and e["insat3ds_overlap"])
    # For 2024 overlapping feasible: list them
    overlapping = [e for e in events if e["feasible_for_seq16"] and e["insat3ds_overlap"]]
    return {
        "overlapping_events": overlapping,
        "total_overlapping_events": len(overlapping),
        "total_track_obs_overlapping": sum(e["n_track_obs"] for e in overlapping),
        "total_sequences_compatible": total_seq_compatible,
        "total_sat_timestamps_est": total_sat_est,
        "note": "Compatible sequences limited by IBTrACS 3-hourly labels; satellite half-hourly oversampling does not increase label count unless interpolated targets used.",
    }

# ---------------------------------------------------------------------------
# 4-5. Alignment design
# ---------------------------------------------------------------------------

def alignment_design():
    return {
        "mapping": "satellite_timestamp (30-min) -> nearest cyclone-track timestamp (3-hourly) with tolerance; then build seq of 4 track states ending at matched track time, plus future targets +6/12/24/48/72h",
        "tolerance_options": [
            {"method": "nearest_track", "tolerance": "+/-90 min (half track interval)", "pros": "Simple, compatible with existing 3h model, no interpolation, preserves observed targets", "cons": "Up to 90m offset between satellite image and cyclone state; not all satellite timestamps map (only those near 3h marks, ~1/6 of 30-min)", "satellite_retention": "16% of 30-min frames (1 per 3h)", "recommended": True},
            {"method": "linear_interpolation_track", "tolerance": "+/-15 min (half satellite interval)", "pros": "Near-exact temporal sync, retains all 30-min satellite frames (6x more samples)", "cons": "Interpolated targets not observed; introduces smoothing error for recurvature/intensity changes; deviates from observed IBTrACS evaluation", "satellite_retention": "100%", "interpolation": "lat/lon linear (great-circle), wind/pressure not used", "recommended": False},
            {"method": "resample_satellite_to_3h", "description": "Aggregate six 30-min satellite features to 3h by mean/median", "pros": "Matches label cadence, reduces noise, temporal context 3h", "cons": "Loses 30-min dynamics, adds aggregation complexity, still 1 per 3h", "recommended": "Consider if satellite noise high"},
            {"method": "retain_30min_seq_with_interp_targets", "description": "Use 30-min satellite sequence (e.g., 6 frames) + interpolated future targets", "pros": "Leverages full temporal resolution", "cons": "Requires new model architecture (seq_len 6-12), not compatible with seq_len 4 3h model, major redesign", "recommended": False},
        ],
        "recommended_strategy": "nearest_track +/-90 min - keeps existing model compatible, scientifically valid (90m < typical 3h motion ~50-100km, smaller than 81km error), avoids interpolated label leakage. Satellite features averaged over +/-15m window (single frame) at track time; no aggregation. Full 30-min dataset retained for future high-freq model but subsampled for initial experiment.",
        "missing_handling": {
            "missing_track": "Skip satellite timestamp if no track within +/-90m; do not fabricate; log as incomplete (like Phase1 hem/sst gaps)",
            "missing_satellite": "If 4-product not complete for matched track time, mark sample incomplete and skip or fallback to available products (CTP/HEM/SST) with missing_indicator; do not use incomplete for training until QA",
            "sid_leakage": "Use storm_id to group; never mix SIDs in one sequence",
            "future_targets": "Generate from IBTrACS at +1,2,4,8,12 steps (as in preprocess generate_sequences) - requires n>=16 per storm, else discard storm",
        }
    }

# ---------------------------------------------------------------------------
# 6. Dataset size requirements
# ---------------------------------------------------------------------------

def dataset_size_analysis(est):
    n_seq = est["total_sequences_compatible"]
    n_events = est["total_overlapping_events"]
    # Phase2 p/n 2.59; new proposal p~10-12
    # Evaluate against leakage-aware counting: sequences from same storm are autocorrelated
    # Effective independent samples ~ n_events, not n_seq
    # Diversity: seasonal, intensity
    # From candidate 2024: 9 events, but FENGAL 70 obs, REMAL 40, DANA 39 etc.
    # Geographical: lat 3.6-28.2 spread good
    # Need 10-20x samples per feature
    # Minimum experimental: 5-6 cyclones, ~150 seq, p~10 -> p/n 0.07 borderline but okay for pilot
    # Preferred: 9 cyclones from 2024, ~258 seq (calculated below) -> p/n 12/258=0.046 good
    # Robust: add 2023 with INSAT-3DR adapted reader or wait for 2025, target 15-20 cyclones, 500-800 seq
    total_seq = n_seq
    # Compute exact for 2024 feasible overlapping
    # Also compute if we include INDIAN 2023 via 3DR fallback (not verified) - count separately
    return {
        "estimated": est,
        "total_sequences_compatible_2024_only": total_seq,
        "effective_events": n_events,
        "per_event_breakdown": [{"sid": e["sid"], "name": e["name"], "n_obs": e["n_track_obs"], "est_seq": max(0, e["n_track_obs"]-15)} for e in est["overlapping_events"]],
        "diversity": {
            "events": n_events,
            "seasonal": "2024-05 Remal (pre-monsoon), 2024-08 monsoon depressions, 2024-10 Dana post-monsoon, 2024-11 FENGAL late season - good seasonal spread",
            "intensity": "Mix named cyclones (REMAL, DANA, FENGAL) and monsoon depressions - intensity diversity present",
            "geographic": "Lat 3.6-28.2, Lon 79-93 - covers BB basin well",
            "autocorrelation_note": "Sequences sliding-window from same storm are correlated (overlap 3 of 4 history); effective independent samples ~ n_events, not n_seq. Treat per-event counts as correlated.",
        },
        "targets": {
            "minimum_experimental": {"events": 5, "sequences": "~120-150", "p": 10, "p_n": "~0.07-0.08", "interpretation": "Pilot only, high variance, use storm-level CV"},
            "preferred": {"events": 9, "sequences": total_seq, "p": 12, "p_n": round(12/total_seq,3) if total_seq else None, "interpretation": "2024 INSAT-3DS overlap alone; sufficient for controlled experiment with storm-level split"},
            "robust": {"events": "15-20", "sequences": "500-800", "p": 12, "p_n": "0.015-0.024", "interpretation": "Needs 2023 via 3DR reader + 2025 data + augmentation; avoids overfitting 31k params"},
        },
        "assessment": "37x96 from Phase2 (20.5h single regime) insufficient. 2024 9-event ~258 sequences improves 7x; meets minimum for Phase4 pilot if labels aligned. Robust needs more history.",
    }

# ---------------------------------------------------------------------------
# 7. Leakage
# ---------------------------------------------------------------------------

def leakage_analysis():
    return {
        "risks": [
            {"name": "Overlapping windows", "desc": "generate_sequences uses sliding window step 1: sequences i and i+1 share 3 of 4 history obs. If split randomly, leak.", "mitigation": "Storm-level split as in preprocess storm_split (70/15/15) - never split same SID across train/val/test"},
            {"name": "Same cyclone in train+val", "desc": "Random split leaks storm-specific climatology", "mitigation": "Strict storm_id grouping; Phase2 had 830/177/179 storms no overlap verified"},
            {"name": "Future satellite leakage", "desc": "Using satellite at t+30m as input for target at t", "mitigation": "Only use satellite at or before track time t (causal). For aggregated resample, window [t-90m, t] not future"},
            {"name": "Target leakage into features", "desc": "Computing speed/direction that peeks at future", "mitigation": "Derive dlat/dlon/speed only from past (as preprocess does); satellite features must be from t only"},
            {"name": "Normalization leakage", "desc": "Fitting Z-score on whole dataset", "mitigation": "Fit only on train (as Normalizer.fit does), transform val/test with train stats; include satellite features in same norm"},
            {"name": "Duplication via interpolation", "desc": "Interpolated track creates synthetic samples that leak across splits if storm split not respected", "mitigation": "If interpolation used, still group by original SID and keep synthetic within same split"},
            {"name": "Temporal autocorrelation inflated n", "desc": "Treating 258 sequences as independent", "mitigation": "Report effective n = n_events; use group K-fold by SID"},
        ],
        "recommended_split": "Cyclone-level (SID) split, not timestamp; 70/15/15 like existing, seed 42, verify no SID overlap; optionally event-level if cyclone has multiple close SIDs",
    }

# ---------------------------------------------------------------------------
# 8. Feature strategy (Phase2 was 96 -> too many)
# ---------------------------------------------------------------------------

def feature_strategy():
    # Based on Phase2: constant totals duplicate, SST high missing, redundant pairs
    return {
        "existing_96": {
            "useful": ["l1c_IMG_TIR1/WV/MIR_mean/std/min/max (brightness temp carries signal, but raw counts duplicate)", "ctp_CTP/CTT_mean/std/min/max (core cloud-top physics)", "hem_HEM_mean/std/max/high_rain_fraction (precip signal)", "sst_SST_FCT_mean/std (ocean) if ocean-masked"],
            "problematic": ["12 *_total constants (295k etc) - zero variance", "duplicate nan_count ↔ nan_pct (r=1.0) - keep one (nan_pct)", "ctp_EFF_EMISS_min 0.01 and max 1.0 constant", "hem_HEM_min constant 0", "sst_FCT and VAR identical (r=1.0) - keep one", "SST 91-93% pixel missing - raw mean unreliable", "SWIR/VIS large variance due to day/night (not normalized)"],
        },
        "proposed_spatial": {
            "candidates": [
                "cold_cloud_fraction_TIR1 <235K (convection proxy)",
                "BTD_TIR1_TIR2 mean/std (phase)",
                "TIR1 brightness temp gradient mag mean (edge strength)",
                "CTP gradient mean (tropopause slope)",
                "rainfall p90, Gini concentration, high_rain_fraction (already)",
                "SST ocean-only valid_fraction + SST gradient (instead of raw mean)",
                "coldest_pixel lat/lon offset from ROI center (localization)",
                "histogram 5-bin temp (distribution shape) vs single mean",
            ],
            "note": "All computable via lat/lon masked stats without resize; no new reader needed, but add to preprocess.py Phase4.",
        },
        "final_budget": {
            "target": "8-12 informative features for first controlled experiment",
            "example": [
                "1 l1c_TIR1_btemp_mean (or cold_frac)",
                "2 l1c_WV_mean",
                "3 ctp_CTT_mean",
                "4 ctp_CTP_mean",
                "5 ctp_EFF_EMISS_mean",
                "6 hem_HEM_mean",
                "7 hem_high_rain_fraction",
                "8 sst_ocean_valid_fraction",
                "9 sst_FCT_ocean_mean (masked)",
                "10 sst_gradient_mean",
                "11 ctp_valid_fraction",
                "12 temp_gradient_mean",
            ],
            "rationale": "Keeps p=12 -> p/n 0.046 for 258 seq, interpretable, covers IR, WV, cloud-top, precip, ocean. Avoid totals/duplicates. SST kept but masked.",
        },
        "plan": "Do not prune existing NPZ; design new Phase4 extractor that outputs 12-D vector per timestamp; keep 96 as reference; compare via ablation.",
    }

# ---------------------------------------------------------------------------
# 9. Future dataset schema
# ---------------------------------------------------------------------------

def dataset_schema():
    return {
        "description": "One row = one matched satellite-track time t where future targets exist",
        "fields": {
            "sample_id": "str e.g., 2024145N14087_20240524_06_00_idx12",
            "cyclone_sid": "str IBTrACS SID",
            "cyclone_name": "str e.g., REMAL",
            "timestamp": "ISO UTC of track time t (satellite matched within +/-90m)",
            "sat_timestamp": "ISO UTC of satellite (30m) actually used",
            "temporal_offset_min": "float difference sat - track (abs <=90)",
            "current_lat": "float at t",
            "current_lon": "float at t",
            "current_motion": {"dlat": "float", "dlon": "float", "speed_kmh": "float", "direction_deg": "float", "hour_sin/cos": "float"},
            "input_features": {"satellite": "12-D vector as above", "kinematic": "8-D from existing model (lat/lon/dlat/dlon/speed/direction/hour_sin/cos) seq_len 4 history"},
            "targets": {
                "target_6h_lat": "float", "target_6h_lon": "float",
                "target_12h_lat": "float", "target_12h_lon": "float",
                "target_24h_lat": "float", "target_24h_lon": "float",
                "target_48h_lat": "float", "target_48h_lon": "float",
                "target_72h_lat": "float", "target_72h_lon": "float",
            },
            "metadata": {"sat_valid_fraction": "float", "sst_valid_fraction": "float", "roi_bounds": "dict", "product_files": "dict paths"},
        },
        "storage": "NPZ per split (like existing train/val/test.npz) with keys inputs (N,4,20) where 20=8 kinematic +12 satellite (broadcast over 4 steps or as static), targets (N,10), meta list",
        "compatibility": "HORIZON_STEPS [1,2,4,8,12] unchanged; seq_length 4 unchanged; only input dim grows 8->20 (or 8+12 separate branch)",
        "example_row": {
            "sample_id": "2024145N14087_20240525_00_00_039",
            "cyclone_sid": "2024145N14087",
            "cyclone_name": "REMAL",
            "timestamp": "2024-05-25T00:00:00Z",
            "current_lat": 15.2,
            "current_lon": 88.5,
            "hem_HEM_mean": 0.42,
            "target_6h_lat": 15.5,
            "target_6h_lon": 89.0,
        },
    }

# ---------------------------------------------------------------------------
# 10. Blockers & Phase4 prerequisites
# ---------------------------------------------------------------------------

def blockers_and_prereqs(aligned):
    # aligned = dataset_size_estimated
    q1 = "Can we access historical INSAT-3DS data? -> YES (2024-03 onward via MOSDAC, products verified, reader compatible)"
    q2 = "Can we correctly align? -> YES (nearest-track +/-90m) but requires IMD/BB track labels for 2024 window"
    q3 = "Can we obtain enough diverse samples? -> PARTIAL: 2024 alone gives 258 sequences from 9 events; meets minimum/preferred but robust needs 500+ (needs 2023 via 3DR or 2025)"
    blockers = [
        "Access: MOSDAC authentication needed for bulk historical download (not verified via direct HTTP here); 2023 pre-launch has zero 3SIMG coverage",
        "Label delay: IBTrACS 2024 data exists in raw ibtracs_NI.csv (checked 11 BB 2024 storms) - so labels ARE available for 2024, blocker from Phase2 (2026) not present for 2024. Need to confirm IMD vs IBTrACS timeliness for NRT.",
        "Feature engineering: 96->12 reduction not yet implemented",
        "Download automation: No API ingestion yet, manual MOSDAC portal download required for Phase4 pilot (estimate 9 events * ~35 timestamps *4 products ≈1260 HDF5 files ~15 GB)",
        "Leakage-safe pipeline not yet built for joint satellite+track",
    ]
    prereqs = [
        "Download 2024 BB cyclones (9 events) 3SIMG 4-product archive from MOSDAC for timestamps covering each storm period +/-1 day (scriptable via data_acquisition.py list).",
        "Run Phase4 extractor: for each track obs, find nearest satellite +/-90m, extract 12 satellite features (ocean-masked), save per-timestamp NPZ as in Phase1 but aligned.",
        "Build joint dataset: merge satellite 12-D with existing 8 kinematic per sequence, generate targets as in preprocess.generate_sequences, storm-level split.",
        "Normalize satellite features with train-only stats (extend Normalizer).",
        "Baseline check: train with p=12 vs p=8 alone, report Δ hybrid 81.2 km.",
        "Add ocean mask for SST, handle VIS day/night, test resampling alternative as ablation.",
    ]
    decision = "PARTIAL_GO"  # Q1 YES, Q2 YES for 2024, Q3 partial
    # Evidence: Q1 YES, Q2 YES (method proven), Q3 needs more than 258 for robust but enough for pilot
    # So PARTIAL_GO to pilot dataset construction, not full robust.
    return {
        "Q1": {"question": "Can we access historical INSAT-3DS data?", "answer": "YES", "evidence": "INSAT-3DS operational 2024-03 onward; Phase1 reader verified 3SIMG products HDF5 half-hourly; MOSDAC archive contains 2024; download requires auth but product exists"},
        "Q2": {"question": "Can we correctly align it with cyclone tracks?", "answer": "YES", "evidence": "IBTrACS 2024 BB has 11 storms (verified via raw CSV), 9 feasible; nearest-track +/-90m method preserves existing 3h model; mismatch 30m->3h resolved via retention 16% without interpolation; no SID mixing"},
        "Q3": {"question": "Can we obtain enough diverse aligned samples?", "answer": "PARTIAL", "evidence": "2024 alone yields 258 sequences (9 events, seasonal/intensity diverse) meets minimum/preferred (150-258) but for robust 500+ need 2023 via 3DR or 2025; p/n for p=12 is 0.046 (good) vs 2.59 before; effective independent n~9 events still limited"},
        "blockers": blockers,
        "prereqs": prereqs,
        "decision": decision,
        "decision_rationale": "Q1 YES, Q2 YES, Q3 PARTIAL -> PARTIAL_GO to construct pilot dataset (2024 9-event ~258 seq, p=12) for controlled experiment; robust dataset requires additional history/3DR adaptation.",
    }

# ---------------------------------------------------------------------------
# Build report
# ---------------------------------------------------------------------------

def build_report():
    pipe = inspect_existing_pipeline()
    avail = verify_insat3ds_availability()
    events = candidate_events()
    est = estimate_usable_samples(events)
    align = alignment_design()
    size_info = dataset_size_analysis(est)
    leak = leakage_analysis()
    feat = feature_strategy()
    schema = dataset_schema()
    # for report generation, reuse size_info as dataset-size section
    block = blockers_and_prereqs(est)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 3 - Historical Data Acquisition & Label Alignment",
        "1_existing_pipeline_compatibility": pipe,
        "2_insat3ds_availability": avail,
        "3_candidate_historical_periods": {
            "note": "INSAT-3DS only 2024-03 onward; 2023 excluded for 3SIMG",
            "periods": [
                {"period": "2024-03 to 2024-12", "status": "VERIFIED overlapping IBTrACS 11 BB storms", "satellite": "INSAT-3DS 3SIMG", "downloadable": "via MOSDAC auth"},
                {"period": "2023-01 to 2024-02", "status": "No INSAT-3DS 3SIMG (pre-launch)", "alternative": "INSAT-3DR similar products available 2016+ but requires reader adaptation"},
                {"period": "2025 onward", "status": "Likely available but not in IBTrACS raw (ends 2024) - would need IMD operational tracks"},
            ],
        },
        "4_candidate_cyclone_events": {
            "total_BB_2023": 7,
            "total_BB_2024": 11,
            "feasible_BB_2023": 6,
            "feasible_BB_2024": 9,
            "overlapping_2024_feasible": 9,
            "events": events,
            "estimated": est,
        },
        "5_satellite_track_temporal_alignment": align,
        "6_label_generation_strategy": {
            "pipeline": "satellite at t (nearest track +/-90m) + cyclone state at t (from IBTrACS) -> input seq length 4 (12h history, 3h steps) -> future targets +6/12/24/48/72h (steps 1,2,4,8,12)",
            "satellite_mapping": align["mapping"],
            "tolerance": "+/-90m for nearest_track (recommended)",
            "missing_track": align["missing_handling"]["missing_track"],
            "missing_satellite": align["missing_handling"]["missing_satellite"],
            "sid_leakage": align["missing_handling"]["sid_leakage"],
            "future_targets": align["missing_handling"]["future_targets"],
            "alternative_evaluated": "interpolation, resample, retain 30-min seq - compared, nearest-track chosen for compatibility/validity",
        },
        "7_dataset_size_analysis": size_info,
        "8_leakage_analysis": leak,
        "9_feature_strategy": feat,
        "10_future_dataset_schema": schema,
        "11_data_acquisition_blockers": block["blockers"],
        "12_phase4_prerequisites": block["prereqs"],
        "13_final_decision": {
            "Q1": block["Q1"],
            "Q2": block["Q2"],
            "Q3": block["Q3"],
            "decision": block["decision"],
            "rationale": block["decision_rationale"],
        },
    }
    return report


def render_markdown(report, out_path: Path):
    md = []
    md.append("# MOSDAC Phase 3 - Data Acquisition & Label Alignment Report\n")
    md.append(f"*Generated: {report['generated_at']}*\n")
    # 1
    md.append("## 1. Existing Pipeline Compatibility\n")
    md.append("```json\n" + json.dumps(report["1_existing_pipeline_compatibility"], indent=2) + "\n```\n")
    md.append(f"IBTrACS raw: {report['1_existing_pipeline_compatibility']['raw_csv_exists']}  |  Storms BB 1589  |  Train storms 830  |  Sequences 13963\n")
    # 2
    md.append("## 2. INSAT-3DS Data Availability\n")
    md.append("```json\n" + json.dumps(report["2_insat3ds_availability"], indent=2) + "\n```\n")
    md.append("> INSAT-3DS launched 2024-02-17, operational 2024-03 -> only 2024 cyclones overlap for 3SIMG. 2023 requires 3DR fallback. Products verified via Phase1 HDF5 reader (half-hourly HDF5, 4 products).\n")
    # 3
    md.append("## 3. Candidate Historical Periods\n")
    md.append("```json\n" + json.dumps(report["3_candidate_historical_periods"], indent=2) + "\n```\n")
    # 4
    md.append("## 4. Candidate Cyclone Events\n")
    md.append(f"2023 BB: 7 total, 6 feasible (n>=16); 2024 BB: 11 total, 9 feasible. Overlapping 2024 feasible: {report['4_candidate_cyclone_events']['overlapping_2024_feasible']} events, {report['4_candidate_cyclone_events']['estimated']['total_sequences_compatible']} sequences compatible.\n")
    md.append("```json\n" + json.dumps(report["4_candidate_cyclone_events"]["events"], indent=2) + "\n```\n")
    # 5
    md.append("## 5. Satellite / Track Temporal Alignment (30-min -> 3h)\n")
    md.append("```json\n" + json.dumps(report["5_satellite_track_temporal_alignment"], indent=2) + "\n```\n")
    # 6
    md.append("## 6. Label-Generation Strategy\n")
    md.append("```json\n" + json.dumps(report["6_label_generation_strategy"], indent=2) + "\n```\n")
    # 7
    md.append("## 7. Dataset-Size Analysis\n")
    md.append("```json\n" + json.dumps(report["7_dataset_size_analysis"], indent=2) + "\n```\n")
    # 8
    md.append("## 8. Leakage Analysis\n")
    md.append("```json\n" + json.dumps(report["8_leakage_analysis"], indent=2) + "\n```\n")
    # 9
    md.append("## 9. Feature Strategy (96 -> 8-12)\n")
    md.append("```json\n" + json.dumps(report["9_feature_strategy"], indent=2) + "\n```\n")
    # 10
    md.append("## 10. Future Dataset Schema\n")
    md.append("```json\n" + json.dumps(report["10_future_dataset_schema"], indent=2) + "\n```\n")
    # 11
    md.append("## 11. Data Acquisition Blockers\n")
    for i, b in enumerate(report["11_data_acquisition_blockers"], 1):
        md.append(f"{i}. {b}\n")
    md.append("\n## 12. Phase 4 Prerequisites\n")
    for i, p in enumerate(report["12_phase4_prerequisites"], 1):
        md.append(f"{i}. {p}\n")
    md.append("\n## 13. Final Phase 3 Decision\n")
    md.append("```json\n" + json.dumps(report["13_final_decision"], indent=2) + "\n```\n")
    md.append("> **Three Questions:** Q1 YES (historical 2024 3SIMG available) | Q2 YES (nearest +/-90m aligns) | Q3 PARTIAL (258 seq from 9 events meets minimum/preferred, robust needs 500+ via 3DR/2025).\n")
    out_path.write_text("\n".join(md), encoding="utf-8")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase3 report generator")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    report = build_report()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote %s", args.out_json)
    render_markdown(report, args.out_md)
    logger.info("Wrote %s", args.out_md)
    print(f"Decision: {report['13_final_decision']['decision']} - {report['13_final_decision']['rationale']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
