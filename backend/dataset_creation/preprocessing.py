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
import os
import logging

# Set up logging for the preprocessing pipeline
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INPUT_FILE = "backend/dataset_creation/extracted_tables/extracted_quarterly_financials.csv"
OUTPUT_FILE = "backend/dataset_creation/cleaned_data/cleaned_quarterly_financials.csv"

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
    # Ensure output directory exists
    out_dir = os.path.dirname(OUTPUT_FILE)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Cleaned/interpolated data saved to {OUTPUT_FILE}")

class Preprocessor:
    """
    Cleans and merges extracted financial tables into a single, standardized DataFrame.
    """
    def __init__(self, input_dir, output_path):
        """
        Initialize the preprocessor with input and output paths.
        Args:
            input_dir (str): Directory containing extracted CSV tables.
            output_path (str): Path to save the cleaned, merged CSV.
        """
        self.input_dir = input_dir
        self.output_path = output_path

    def clean_table(self, df):
        """
        Clean a single extracted table DataFrame.
        Args:
            df (pd.DataFrame): Raw extracted table.
        Returns:
            pd.DataFrame: Cleaned table.
        """
        # Example cleaning: drop empty columns, fill missing values, standardize column names
        df = df.dropna(axis=1, how='all')
        df = df.fillna(0)
        df.columns = [col.strip().replace('\n', ' ') for col in df.columns]
        return df

    def merge_tables(self):
        """
        Merge all cleaned tables into a single DataFrame.
        Returns:
            pd.DataFrame: Merged DataFrame.
        """
        all_tables = []
        for filename in os.listdir(self.input_dir):
            if filename.endswith('.csv'):
                path = os.path.join(self.input_dir, filename)
                try:
                    df = pd.read_csv(path)
                    df = self.clean_table(df)
                    all_tables.append(df)
                    logger.info(f"Processed {filename}")
                except Exception as e:
                    logger.error(f"Failed to process {filename}: {str(e)}")
        if all_tables:
            merged = pd.concat(all_tables, ignore_index=True)
            return merged
        else:
            logger.warning("No tables found to merge.")
            return pd.DataFrame()

    def run(self):
        """
        Run the preprocessing pipeline: clean, merge, and save the final CSV.
        """
        merged = self.merge_tables()
        if not merged.empty:
            merged.to_csv(self.output_path, index=False)
            logger.info(f"Saved cleaned data to {self.output_path}")
        else:
            logger.warning("No data to save.")

if __name__ == "__main__":
    main() 