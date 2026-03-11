# Figure Captions (Publication Package)

1. **Predicted vs Observed Fuel (Test Set)**  
   Scatter comparison for speed-power baseline, pure ML, physics-only, and hybrid. The hybrid model should show the tightest concentration around the identity line.

2. **Residual Diagnostics by Model**  
   Residual histograms and residual-vs-prediction plots, highlighting bias reduction and variance contraction in the hybrid model.

3. **Uncertainty Calibration Plot**  
   Empirical coverage of split-conformal prediction intervals versus nominal confidence levels.

4. **Feature Sensitivity Ranking**  
   Permutation sensitivity (delta MAE) for operational and environmental covariates used in residual learning.

5. **Error by Sea-State Bin**  
   MAE stratified by significant wave-height bins to demonstrate robustness under harsh sea states.

6. **Error by Speed Bin**  
   MAE stratified by speed-through-water bins, with emphasis on slow steaming and high-load operating regimes.

7. **Ablation Study**  
   Performance degradation when removing wind, wave, current, loading, and fouling feature blocks.
