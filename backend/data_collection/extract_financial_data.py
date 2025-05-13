import os
import re
import logging
from datetime import datetime
import pandas as pd
import pdfplumber
import tabula
import camelot
from thefuzz import process

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PDF_ROOT = "backend/data_collection/downloaded_pdfs"
#OUTPUT_FILE = "quarterly_financials.csv"
# ensure the folder exists
BACKEND_DIR = os.path.join("backend", "data_collection")
os.makedirs(BACKEND_DIR, exist_ok=True)

# set the output file path inside backend/data_collection
OUTPUT_FILE = os.path.join(BACKEND_DIR, "quarterly_financials.csv")

# Define metrics and synonyms
METRICS = {
    "Revenue": ["revenue", "turnover", "revenue from contracts with customers"],
    "COGS": ["cost of goods sold", "cost of sales", "cost of revenue"],
    "Gross Profit": ["gross profit"],
    "Distribution Costs": ["distribution costs"],
    "Administrative Expenses": ["administrative expenses"],
    "Other Expenses": ["other expenses", "other operating expense"],
    "Other Income": ["other income", "other income and gains", "other operating income"],
    "Operating Income": ["operating income", "operating profit", "profit from operations", "profit/(loss) from operations"],
    "Net Income": ["net income", "net profit", "profit for the period", "profit/(loss) for the period"]
}
OUTPUT_METRICS = list(METRICS.keys()) + ["Operating Expenses"]

# Regex patterns
FNAME_DATE_RE = re.compile(r"^(\d{2}[A-Za-z]{3}\d{4})")
TABLE_DATE_RE = re.compile(r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})", re.IGNORECASE)
FUZZY_THRESHOLD = 65


def parse_report_date(name):
    m = FNAME_DATE_RE.match(name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%d%b%Y").date().isoformat()
        except ValueError:
            pass
    return ''


def find_table_date(pdf):
    text = ''
    for i in range(min(2, len(pdf.pages))):
        text += '\n' + (pdf.pages[i].extract_text() or '')
    for m in TABLE_DATE_RE.findall(text)[::-1]:
        clean = re.sub(r"(st|nd|rd|th)", "", m, flags=re.IGNORECASE)
        for fmt in ["%d %B %Y", "%d %b %Y"]:
            try:
                return datetime.strptime(clean.strip(), fmt).date().isoformat()
            except ValueError:
                continue
    return ''


def parse_value(val):
    if pd.isna(val) or not re.search(r"\d", str(val)):
        return None
    s = str(val).replace(',', '').replace(' ', '').replace('\n', '')
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else None


def match_metric(desc):
    if not isinstance(desc, str):
        return None
    desc_clean = re.sub(r"[^A-Za-z ]", '', desc).lower()
    best_metric, best_score = None, 0
    for metric, syns in METRICS.items():
        match, score = process.extractOne(desc_clean, syns)
        if score and score > best_score:
            best_metric, best_score = metric, score
    if best_score >= FUZZY_THRESHOLD:
        return best_metric
    # fallback substring
    for metric, syns in METRICS.items():
        for syn in syns:
            if syn in desc_clean:
                return metric
    return None


def extract_tables_tabula(path):
    dfs = []
    for flavor in ['lattice', 'stream']:
        try:
            dfs += tabula.read_pdf(path, pages='all', multiple_tables=True, pandas_options={'dtype': str}, lattice=(flavor=='lattice'), stream=(flavor=='stream'))
        except Exception as e:
            logging.warning(f"Tabula {flavor} failed on {path}: {e}")
    return dfs


def extract_tables_camelot(path):
    dfs = []
    for flavor in ['lattice', 'stream']:
        try:
            tables = camelot.read_pdf(path, pages='all', flavor=flavor)
            dfs += [t.df for t in tables]
        except Exception as e:
            logging.warning(f"Camelot {flavor} failed on {path}: {e}")
    return dfs


def extract_metrics_from_text(path):
    # Try to extract numbers from the text as a last resort
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    metrics = {}
    for metric, syns in METRICS.items():
        for syn in syns:
            pattern = re.compile(rf"{syn}.*?(-?\d[\d,.\(\)\s]*)", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                val = parse_value(match.group(1))
                if val is not None:
                    metrics[metric] = val
    return metrics


def extract_financials(path):
    with pdfplumber.open(path) as pdf:
        table_date = find_table_date(pdf)
    all_metrics = {}
    dfs = extract_tables_tabula(path) + extract_tables_camelot(path)
    for df in dfs:
        if isinstance(df, pd.DataFrame):
            data = df
        else:
            data = pd.DataFrame(df)
        if data.shape[0] < 2 or data.shape[1] < 2:
            continue
        data = data.replace({None: None, '\n': ' '})
        # header
        try:
            header = data.iloc[0].fillna('').astype(str).tolist()
        except IndexError:
            continue

        # Prefer columns with "group" or "consolidated" in header
        group_cols = [i for i, h in enumerate(header) if 'group' in h.lower() or 'consolidated' in h.lower()]
        candidate_cols = group_cols if group_cols else list(range(1, data.shape[1]))

        for col_idx in candidate_cols:
            col_metrics = {}
            for idx in range(1, len(data)):
                desc = data.iat[idx, 0]
                metric = match_metric(desc)
                if not metric:
                    continue
                try:
                    val = parse_value(data.iat[idx, col_idx])
                except IndexError:
                    continue
                # Sanity check: ignore values that are too small for revenue/cogs/gross profit
                if metric in ['Revenue', 'COGS', 'Gross Profit'] and (val is None or abs(val) < 1000):
                    continue
                if val is not None and (metric not in col_metrics or abs(val) > abs(col_metrics[metric])):
                    col_metrics[metric] = val
            # If this column has at least 2 core metrics, merge into all_metrics
            core_count = sum(1 for m in ['Revenue','COGS','Gross Profit'] if m in col_metrics)
            if core_count >= 2:
                for k, v in col_metrics.items():
                    if k not in all_metrics or abs(v) > abs(all_metrics[k]):
                        all_metrics[k] = v

        # Log problematic tables
        if not col_metrics and data.shape[0] > 1:
            logging.warning(f"Table in {path} (first 3 rows):\n{data.head(3)}")

    # compute derived
    if 'Revenue' in all_metrics and 'COGS' in all_metrics:
        all_metrics['Gross Profit'] = all_metrics.get('Gross Profit', all_metrics['Revenue'] - all_metrics['COGS'])
    ops = sum(all_metrics.get(x, 0.0) for x in ['Distribution Costs','Administrative Expenses','Other Expenses'])
    all_metrics['Operating Expenses'] = ops
    gp = all_metrics.get('Gross Profit', 0.0)
    oi = all_metrics.get('Other Income', 0.0)
    all_metrics['Operating Income'] = all_metrics.get('Operating Income', gp + oi - ops)

    # Only use text fallback if absolutely no metrics found
    if not any(all_metrics.values()):
        logging.warning(f"No metrics extracted from {path}, trying text fallback.")
        all_metrics = extract_metrics_from_text(path)
        # Sanity check for text fallback
        for k in list(all_metrics.keys()):
            if k in ['Revenue', 'COGS', 'Gross Profit'] and abs(all_metrics[k]) < 1000:
                del all_metrics[k]
        if not any(all_metrics.values()):
            logging.warning(f"Text fallback also failed for {path}.")

    return all_metrics, table_date


def main():
    records = []
    for comp in os.listdir(PDF_ROOT):
        comp_dir = os.path.join(PDF_ROOT, comp)
        if not os.path.isdir(comp_dir): continue
        for fname in os.listdir(comp_dir):
            if not fname.lower().endswith('.pdf'): continue
            path = os.path.join(comp_dir, fname)
            logging.info(f"Processing {path}")
            name = os.path.splitext(fname)[0]
            report_date = parse_report_date(name)
            metrics, table_date = extract_financials(path)
            rec = {'Company': comp, 'ReportDate': report_date, 'TableDate': table_date}
            for m in OUTPUT_METRICS:
                rec[m] = metrics.get(m, 0.0)
            records.append(rec)
    df = pd.DataFrame(records)
    df = df[['Company','ReportDate','TableDate'] + OUTPUT_METRICS]
    df.to_csv(OUTPUT_FILE, index=False)
    logging.info(f"Saved data to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()

