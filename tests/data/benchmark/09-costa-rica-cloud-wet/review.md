# 09 — Costa Rica Cloud-Contaminated

## Location
Talamanca range, Costa Rica. ~9.82N, -83.97W. Tropical montane rainforest.

## Change description
Cloud-contaminated imagery during peak wet season (Oct-Nov 2024).
Persistent cloud cover in the AOI during both windows.

## Source of truth
- Sentinel-2 cloud metadata
- Costa Rica weather records (wet season Oct-Nov)

## Expected behavior
Pipeline should ABSTAIN due to cloud/insufficient valid pixels.
This is a known failure mode — tropical wet season imagery is unreliable.
If pipeline reports findings, they are likely artifacts of cloud masking.
max_cloud_fraction=0.15 should reject most scenes.

## Reviewer
Farzin Shifat
## Date
2026-06-22
