# MOSDAC Phase 4 - Pilot Dataset Report (REMAL/DANA/FENGAL)

*Generated: 2026-08-28T19:30:15.195728+00:00*  
*Status: PILOT_WAITING_FOR_MOSDAC_DATA*

## 1. Data Sources
- IBTrACS v04r01 `ml/data/raw/ibtracs_NI.csv` (verified 11 BB 2024)
- INSAT-3DS 3SIMG L1C_ASIA_MER, L2B CTP/HEM/SST HDF5 half-hourly (via `hdf5_reader.py`)
- MOSDAC portal `mosdac.gov.in` (auth required)

## 2. Events Used

- 2024145N14087 REMAL n_obs=40 est_seq_track_only=25

- 2024295N15092 DANA n_obs=39 est_seq_track_only=24

- 2024329N04089 FENGAL n_obs=70 est_seq_track_only=55

## 3. Number of Satellite Observations

Local `data_download/` satellite timestamps: 50 (all 2026-08-27/28, none for 2024 pilot window)

Sample local: ['2026-08-27T10:00:00+00:00', '2026-08-27T10:30:00+00:00', '2026-08-27T11:00:00+00:00']

## 4. Number of Matched Observations

Matched total 0 (exact 0, nearest 0, skipped 149)

## 5. Exact vs Nearest

- 2024145N14087: exact 0, nearest 0, skipped 40

- 2024295N15092: exact 0, nearest 0, skipped 39

- 2024329N04089: exact 0, nearest 0, skipped 70

## 6. Alignment Offsets

Tolerance +/-90m; no fabrications; all 2024 pilot offsets missing due to no local 2024 HDF5.

## 7. Missing Observations

Required files for pilot (3 events x n_track x4): 596 (existing 0, missing 596)

Sample missing (first 5): ['data_download\\3SIMG_L1C_ASIA_MER\\2024\\23MAY\\3SIMG_23MAY2024_1200_L1C_ASIA_MER_V01R00.h5', 'data_download\\3SIMG_L2B_CTP\\2024\\23MAY\\3SIMG_23MAY2024_1200_L2B_CTP_V01R00.h5', 'data_download\\3SIMG_L2B_HEM\\2024\\23MAY\\3SIMG_23MAY2024_1200_L2B_HEM_V01R00.h5', 'data_download\\3SIMG_L2B_SST\\2024\\23MAY\\3SIMG_23MAY2024_1200_L2B_SST_V01R00.h5', 'data_download\\3SIMG_L1C_ASIA_MER\\2024\\23MAY\\3SIMG_23MAY2024_1500_L1C_ASIA_MER_V01R00.h5']

Reason: 2024 HDF5 not yet downloaded from MOSDAC (auth/manual). 2026 data exists but does not overlap pilot storm dates.

## 8. Satellite Feature Count

12 (list below) - actual P reported as 12:

- TIR1_btemp_mean

- TIR1_btemp_std

- WV_mean

- MIR_btemp_mean

- CTT_mean

- CTP_mean

- CTP_valid_frac

- HEM_mean

- HEM_high_rain_frac

- SST_ocean_valid_frac

- SST_ocean_mean

- SST_gradient_mean

SST not zero-filled; ocean valid fraction preserved; gradient via nan-masked.

## 9. Kinematic Feature Count

8: lat, lon, dlat, dlon, speed_kmh, direction_deg, hour_sin, hour_cos (verified from `preprocess.py` derive_features: dlat/dlon/speed/direction/hour_sin_cos)

## 10. Final Tensor Shapes

```
X_satellite (N,4,12)
X_kinematic (N,4,8)
X_fused (N,4,20)
Y (N,10) [+6/12/24/48/72 lat/lon]
```

Pilot actual N=0 (no matched 2024 satellite), schema N=0 placeholders created to document without fabricating.

## 11. Target Construction

For each t where satellite matched, seq [t-3,t] (12h history) -> future lat/lon at steps [1,2,4,8,12] x6h; requires n>=16 per storm (all 3 pilot storms satisfy track-only).

## 12. Train/Validation/Test Assignments

- REMAL (2024145N14087) May pre-monsoon - TRAIN n_obs=40 est_seq=25

- DANA (2024295N15092) Oct post-monsoon - VALIDATION n_obs=39 est_seq=24

- FENGAL (2024329N04089) Nov-Dec late season - TEST n_obs=70 est_seq=55

Note: PILOT split - 3 storms insufficient for statistical test; labeled as pilot only  
Full 9-event plan: 6 train (REMAL + 5 monsoon depressions + maybe), 1-2 val (DANA), 1-2 test (FENGAL + one monsoon) preserving diversity

## 13. Missing-Value Treatment

- Satellite NaN preserved; SST ocean mean NaN if valid_frac<=0.01, valid_frac kept as feature
- HEM 0% pixel NaN -> mean valid; CTP 16% valid_frac feature; no zero-fill
- Rows with no satellite within 90m skipped (not imputed)

## 14. Leakage Checks

- **temporal_future_leak**: Checked: satellite timestamp used is at track time T, not future; alignment offset verifies sat <= track+90 and satellite never from future beyond T; dataset would use only history [T-9h,T] satellite frames, no future.

- **target_leakage**: Checked: input features derived only from [t-3,t] history; targets are future lat/lon at +6..72h not in input.

- **storm_leakage**: Would be storm-level split: REMAL train, DANA val, FENGAL test (example) - no SID overlap. Verified via SID grouping.

- **normalization_leakage**: Not applied in pilot (no training); recommendation: fit Z-score on train storms only, as in Normalizer.fit.

- **file_leakage**: Verified: target files not used as input; input uses sat at T, targets use later IBTrACS lat/lon, not satellite files.

Assertions: all would_pass true if dataset built with storm-level split and train-only norm.

## 15. Geographic Sanity

- Lat 3.6-28.2, Lon 79-93 (Bay), no impossible coords, no wrapping, chronological, no future sat.

## 16. Dataset Limitations

- Pilot has 0 matched samples due to missing 2024 HDF5 locally -> cannot train/evaluate
- 3 storms insufficient for statistical test; full 9 needed for 6/1-2/1-2 split
- 20.5h single regime in Phase1 also limited; 2024 9-event would give 258 seq but still correlated windows
- Feature count 12 vs 8 baseline keeps p/n 0.046 for 258 (good) vs 2.59 before

## 17. Whether Pilot Passed

**PILOT_WAITING_FOR_MOSDAC_DATA** (was PILOT_BLOCKED — now reclassified as waiting for auth)

**What was actually downloaded (Step 1):**
- `data_download/` inspected: 50 L1C + 50 CTP + 40 HEM + 37 SST = 177 files, all `2026-08-27/28` only. No 2024 files for REMAL/DANA/FENGAL. Existing 2026 files remain untouched and validated.

**Tiny validation (Step 5):**
- REMAL expected `.../2024/23MAY/3SIMG_23MAY2024_1200_L1C_ASIA_MER_V01R00.h5` → **not found** (auth required, no bypass, no corrupt file).
- Control 2026 `3SIMG_27AUG2026_1630_*` → **PASS**: L1C 6 bands (1,1616,1737), CTP 3, HEM 1, SST 3; calibration/LUT, mercator bounds -10→45.5, ROI mask 290970 valid, no shape/projection issue. Reader needs no change.

**Matched timestamps (Step 7):** exact 0, nearest 0, skipped 149/149 (100%), per-storm 40/39/70. Tolerance strictly +/-90m, not increased.

**Generated sequences:** `max_seq track-only` REMAL 25 + DANA 24 + FENGAL 55 = 104 track-only, but joint **N=0** due to 0 satellite matches → placeholders `X_sat(0,4,12)` etc. documented without fabricating.

**Leakage (Step 8):** PASS vacuously (storm-split REMAL/DANA/FENGAL disjoint, no future sat, train-only norm, file leakage checked).

**Why waiting:** MOSDAC historical 2024 requires registration + Order Data (`mosdac.gov.in/internal/uops`, latency 3 days, API `/downloadapi-manual`). Web-verified Data Access Policy. No compatibility block.

**Exact next action (STOP before auto-download):**
1. SignUp/Login at https://www.mosdac.gov.in/internal/registration → https://www.mosdac.gov.in/internal/uops
2. Order Data → Satellite INSAT-3DS → Products `3SIMG_L1C_ASIA_MER, 3SIMG_L2B_CTP, 3SIMG_L2B_HEM, 3SIMG_L2B_SST` → Date ranges `REMAL 2024-05-22→05-29, DANA 2024-10-20→10-27, FENGAL 2024-11-22→12-03` (±1 day) half-hourly → Download HDF5
3. Preserve filenames: `data_download/{PRODUCT}/YYYY/DDMMM/3SIMG_DDMMMYYYY_HHMM_*_V01R00.h5` (full list in `pilot_required_manifest.json` — 596 files for 3 events, ~15 GB; ~1260 for full 9)
4. Re-run `python -m ml.mosdac.dataset_builder` and `python C:\Users\chait\AppData\Local\Temp\opencode\validate_tiny.py` → should then report `PILOT_READY_FOR_FULL_9_EVENT_BUILD` with N~104

Do NOT download remaining 6 events until pilot passes.

## 18. Prerequisites for Full 9-Event Dataset

1. Manually download from MOSDAC for 9 overlapping 2024 BB events (REMAL + 8 others) 4-product half-hourly covering each storm period +/-1 day (~1260 HDF5 ~15 GB) to `data_download/{PRODUCT}/YYYY/DDMMM/` (resumable, avoid duplicates).

2. Re-run `python -m ml.mosdac.dataset_builder --pilot` (or full) - will then populate train/validation/test.npz with N~258.

3. Verify alignment exact/nearest counts, leakage asserts, geographic checks (automated in builder).

4. Normalize satellite+kinematic with train-only stats (extend Normalizer).

5. Then proceed to Phase5 controlled experiment A/B/C/D vs 81.2 km baseline (separate approval).


---
*No model retraining done; baseline 81.2 km preserved.*
