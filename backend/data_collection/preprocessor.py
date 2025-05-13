"""
Preprocessor for quarterly_financials.csv

- Sorts by TableDate ascendingly
- Keeps only main metrics: Revenue, COGS, Gross Profit, Operating Expenses, Operating Income, Net Income
- Interpolates unacceptable values (0, negative, or >1000x less than average) using linear interpolation between closest valid previous/next values
- Saves to quarterly_financials_cleaned.csv

Other possible data handling techniques:
- Use rolling mean or median for imputation
- Use forward/backward fill for short gaps
- Flag interpolated values for downstream analysis
"""
import pandas as pd
import numpy as np
from datetime import datetime

INPUT_FILE = "backend/data_collection/quarterly_financials.csv"
OUTPUT_FILE = "backend/data_collection/quarterly_financials_cleaned.csv"

MAIN_METRICS = [
    "Revenue", "COGS", "Gross Profit", "Operating Expenses", "Operating Income", "Net Income"
]
KEEP_COLS = ["Company", "ReportDate", "TableDate"] + MAIN_METRICS

def is_unacceptable(val, avg):
    if pd.isna(val): return True
    if val <= 0: return True
    if avg > 0 and val < avg / 1000: return True
    return False

def interpolate_series(s, mask):
    s_interp = s.copy()
    idxs = np.arange(len(s))
    bad_idxs = np.where(mask)[0]
    good_idxs = np.where(~mask)[0]
    # Interpolate each contiguous block of bad values
    i = 0
    while i < len(bad_idxs):
        start = bad_idxs[i]
        # Find the end of this contiguous block
        end = start
        while end + 1 in bad_idxs:
            end += 1
            i += 1
        # Find left and right good indices
        left = good_idxs[good_idxs < start]
        right = good_idxs[good_idxs > end]
        if len(left) == 0 or len(right) == 0:
            i += 1
            continue  # Can't interpolate at edges
        l_idx = left[-1]
        r_idx = right[0]
        l_val = s.iloc[l_idx]
        r_val = s.iloc[r_idx]
        n = r_idx - l_idx
        for j in range(1, n):
            interp_val = l_val + (r_val - l_val) * j / n
            s_interp.iloc[l_idx + j] = interp_val
        i += 1
    return s_interp

def main():
    df = pd.read_csv(INPUT_FILE)
    # Parse TableDate as datetime
    df["TableDate"] = pd.to_datetime(df["TableDate"], errors='coerce')
    # Sort by Company, then TableDate
    df = df.sort_values(["Company", "TableDate"]).reset_index(drop=True)
    df = df[KEEP_COLS]
    for metric in MAIN_METRICS:
        vals = df[metric].astype(float)
        avg = vals[vals > 0].mean()
        mask = vals.apply(lambda v: is_unacceptable(v, avg))
        if mask.any():
            vals_interp = interpolate_series(vals, mask)
            # Edge case: forward fill for first value if still unacceptable
            if is_unacceptable(vals_interp.iloc[0], avg):
                first_good = vals_interp[~mask].iloc[0] if (~mask).any() else np.nan
                vals_interp.iloc[0] = first_good
            # Edge case: backward fill for last value if still unacceptable
            if is_unacceptable(vals_interp.iloc[-1], avg):
                last_good = vals_interp[~mask].iloc[-1] if (~mask).any() else np.nan
                vals_interp.iloc[-1] = last_good
            df[metric] = vals_interp
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Cleaned/interpolated data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main() 