"""
extract_tables.py

Extracts financial tables from downloaded PDFs for CSE-listed companies and saves them as a single CSV file for downstream analysis.

Key Features:
- Identifies and extracts income statement tables from PDFs using pdfplumber, Camelot, and Tabula.
- Uses fuzzy matching to map various table row names to standardized financial metrics.
- Handles company-specific table structures and naming conventions.
- Outputs a unified CSV with all relevant metrics for each company and quarter.

Usage:
    python extract_tables.py

Requirements:
    - pdfplumber, camelot, tabula-py, thefuzz, pandas, numpy
    - Java (for tabula)
"""

import os
import re
import logging
from datetime import datetime
import pandas as pd
import camelot
import tabula
import pdfplumber
from thefuzz import process


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PDF_ROOT = "backend/data_scraping/pdfs"
OUTPUT_FILE = "backend/dataset_creation/extracted_tables/extracted_quarterly_financials.csv"

INCOME_STATEMENT_NAMES = [
    "income statement", "consolidated income statement", "earnings statement", "revenue statement",
    "operating statement", "statement of operations", "statement of financial performance",
    "statement of profit and loss", "profit and loss statement", "p&l statement", "income statements",
    "consolidated income statements", "statement of profit or loss"
]

METRICS = {
    "DIPD": {
        "Revenue": ["turnover", "revenue", "revenue from contracts with customers", "total income"],
        "COGS": ["cost of sales", "cost of goods sold", "cost of revenue", "direct expenses"],
        "Gross Profit": ["gross profit", "gross profit/(loss)", "gross income"],
        "Distribution Costs": ["distribution costs", "distribution expenses", "selling expenses"],
        "Administrative Expenses": ["administrative expenses", "admin expenses", "administration costs"],
        "Other Expenses": ["other expenses", "other operating expense", "other costs", "miscellaneous expense", "other losses", "other outflows"],
        "Other Income": ["other income", "other income and gains", "other operating income", "miscellaneous income", "other gains", "other inflows"],
        "Operating Expenses": ["operating expenses", "cash outflows from operating activities", "operating expenditure", "operating outflows", "total operating expenses"],
        "Operating Income": ["operating income", "operating profit", "profit from operations", "profit/(loss) from operations", "results from operating activities", "cash inflows from operating activities", "operating inflows", "total operating income"],
        "Net Income": ["net income", "net profit", "profit for the period", "profit/(loss) for the period", "total comprehensive income"],
    },
    "REXP": {
        "Revenue": ["revenue", "revenue from contracts with customers", "total income"],
        "COGS": ["cost of sales", "cost of goods sold", "cost of revenue", "direct expenses"],
        "Gross Profit": ["gross profit", "gross profit/(loss)", "gross income"],
        "Distribution Costs": ["distribution costs", "distribution expenses", "selling expenses"],
        "Administrative Expenses": ["administrative expenses", "admin expenses", "administration costs"],
        "Other Operating Expense": ["other operating expense", "other expenses", "other costs", "miscellaneous expense", "other losses", "other outflows"],
        "Other Income": ["other income", "other income and gains", "other operating income", "miscellaneous income", "other gains", "other inflows"],
        "Operating Expenses": ["operating expenses", "cash outflows from operating activities", "operating expenditure", "operating outflows", "total operating expenses"],
        "Operating Income": ["operating income", "operating profit", "profit from operations", "profit/(loss) from operations", "results from operating activities", "cash inflows from operating activities", "operating inflows", "total operating income"],
        "Net Income": ["net income", "net profit", "profit / (loss) for the period", "profit for the period", "total comprehensive income"],
    }
}

OUTPUT_METRICS = [
    "Company", "ReportDate", "TableDate", "YLabel",
    "Revenue", "COGS", "Gross Profit",
    "Distribution Costs", "Administrative Expenses", "Other Expenses", "Other Income", "Other Operating Expense",
    "Operating Expenses", "Operating Income", "Net Income"
]

FUZZY_THRESHOLD = 60

num_re = re.compile(r"\(?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?")

# Helper functions

def ensure_output_dir():
    """
    Ensure the output directory for the extracted CSV exists.
    """
    out_dir = os.path.dirname(OUTPUT_FILE)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)


def parse_date_from_filename(filename):
    """
    Attempt to extract a date from the PDF filename using several common patterns.
    Args:
        filename (str): The filename to parse.
    Returns:
        date or None: The extracted date, or None if not found.
    """
    m = re.match(r"(\d{2})_([A-Za-z]{3})_(\d{4})", filename)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y").date()
        except:
            pass
    date_patterns = [r"(\d{2}[-_]\d{2}[-_]\d{4})", r"(\d{2}[-_]\w{3}[-_]\d{4})", r"(\d{4}[-_]\d{2}[-_]\d{2})"]
    for pattern in date_patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                return pd.to_datetime(match.group(1), errors='coerce').date()
            except:
                continue
    return None


def parse_value(val):
    """
    Parse a string value from a table cell into a float, handling negatives and parentheses.
    Args:
        val (str or float): The value to parse.
    Returns:
        float: The parsed value, or 0.0 if not parseable.
    """
    if pd.isna(val): return 0.0
    s = str(val).replace(',', '').replace(' ', '').replace('\n', '')
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else 0.0


def match_metric(desc, company):
    """
    Fuzzy match a table row description to a standardized metric for the given company.
    Args:
        desc (str): The row description from the table.
        company (str): The company code (e.g., 'DIPD').
    Returns:
        str or None: The matched metric name, or None if not matched.
    """
    if not isinstance(desc, str): return None
    desc_clean = re.sub(r"[^A-Za-z ]", '', desc).lower()
    best_metric, best_score = None, 0
    for metric, syns in METRICS[company].items():
        match, score = process.extractOne(desc_clean, syns)
        if score > best_score:
            best_metric, best_score = metric, score
    if best_score >= FUZZY_THRESHOLD:
        return best_metric
    for metric, syns in METRICS[company].items():
        for syn in syns:
            if syn in desc_clean:
                return metric
    return None


def find_income_statement_table(pdf_path):
    """
    Search all pages of a PDF for a page containing an income statement header.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        tuple: (page_index, line_index) of the header, or (None, None) if not found.
    """
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = [l.strip().lower() for l in text.splitlines()]
            for line in lines:
                for name in INCOME_STATEMENT_NAMES:
                    if name in line:
                        return i, lines.index(line)
    return None, None


def extract_y_label(header_lines):
    """
    Extract the Y-axis label (e.g., currency/units) from header lines near the table.
    Args:
        header_lines (list): List of lines near the table header.
    Returns:
        str: The extracted Y-label, or empty string if not found.
    """
    for line in header_lines:
        m = re.search(r"rs\.?[' ]?0{3,}", line, re.IGNORECASE)
        if m:
            return m.group(0)
    return ""


def find_table_date(pdf_path):
    """
    Attempt to extract the quarter/period end date from the PDF text.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        date or None: The detected table date, or None if not found.
    """
    # Patterns for quarter/period end dates
    QUARTER_ENDS = [(3, 31), (6, 30), (9, 30), (12, 31)]
    TABLE_DATE_RE = re.compile(
        r"(\d{1,2})(?:st|nd|rd|th)?[\s/-]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)[\s/-]+(\d{4})",
        re.IGNORECASE
    )
    MONTHS = {m: i+1 for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}
    MONTHS.update({m: i+1 for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])})
    candidates = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for m in TABLE_DATE_RE.findall(text):
                day, month, year = m
                month_num = MONTHS.get(month[:3].capitalize(), None)
                if month_num:
                    try:
                        d = datetime(int(year), int(month_num), int(day))
                        # Only accept quarter ends
                        if (d.month, d.day) in QUARTER_ENDS:
                            candidates.append(d.date())
                    except:
                        pass
    if candidates:
        return max(candidates)
    # Fallback: use report date and pick closest previous quarter end
    report_date = parse_date_from_filename(os.path.basename(pdf_path))
    if report_date:
        year = report_date.year
        q_ends = [datetime(year, m, d).date() for m, d in QUARTER_ENDS]
        q_ends = [d for d in q_ends if d <= report_date]
        if q_ends:
            return max(q_ends)
    return None


def parse_page3_metrics(text, company="DIPD"):
    """
    Parse metrics from a block of text (usually from DIPD PDFs) using fuzzy matching.
    Args:
        text (str): The text block to parse.
        company (str): The company code.
    Returns:
        dict: Dictionary of matched metrics and their values.
    """
    metrics = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        # Combine with next line for multi-line metrics
        combined = line
        if i + 1 < len(lines):
            combined += " " + lines[i + 1]
        metric = match_metric(combined, company)
        if metric:
            nums = num_re.findall(line)
            # For DIPD, the 3rd number is usually the "Group Unaudited" value
            if len(nums) >= 3:
                val = nums[2]
                val = val.replace(',', '').replace('(', '-').replace(')', '')
                try:
                    metrics[metric] = float(val)
                except:
                    metrics[metric] = 0.0
    return metrics


def extract_all_metrics(pdf_path, company, table_date):
    """
    Extract all relevant financial metrics from a PDF for a given company and date.
    Handles both DIPD and REXP table formats.
    Args:
        pdf_path (str): Path to the PDF file.
        company (str): Company code.
        table_date (date): The detected table date.
    Returns:
        tuple: (metrics_dict, y_label)
    """
    if company == "DIPD":
        # Search all pages for income statement tables
        with pdfplumber.open(pdf_path) as pdf:
            found_metrics = {}
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines = text.splitlines()
                for idx, line in enumerate(lines):
                    lwr = line.strip().lower()
                    # Check if this line is a valid income statement header
                    if any(name in lwr for name in INCOME_STATEMENT_NAMES):
                        # Avoid tables under unwanted headers
                        if any(x in lwr for x in ["other comprehensive income", "statement of financial position", "statements of changes in equity"]):
                            continue
                        # Extract the table below this header (next ~20 lines)
                        table_lines = lines[idx+1:idx+21]
                        table_text = "\n".join(table_lines)
                        page_metrics = parse_page3_metrics(table_text, company)
                        # Merge found metrics, prefer first nonzero value
                        for k, v in page_metrics.items():
                            if k not in found_metrics or found_metrics[k] == 0.0:
                                found_metrics[k] = v
            metrics = {m: found_metrics.get(m, 0.0) for m in OUTPUT_METRICS}
            return metrics, "Rs.'000"

    # REXP and others: robust table extraction
    page_idx, heading_idx = find_income_statement_table(pdf_path)
    if page_idx is None:
        logging.warning(f"No income statement for {pdf_path}")
        return {k: 0.0 for k in OUTPUT_METRICS}, ""
    # Try Camelot first
    try:
        tables = camelot.read_pdf(pdf_path, pages=str(page_idx+1), flavor='stream')
    except:
        tables = []
    if not tables or not hasattr(tables, 'n') or tables.n == 0:
        try:
            dfs = tabula.read_pdf(pdf_path, pages=page_idx+1, multiple_tables=True, pandas_options={'dtype':str})
            tables = [df for df in dfs if isinstance(df, pd.DataFrame)]
        except:
            tables = []
    # Extract y_label
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_idx]
        lines = page.extract_text().splitlines()
    y_label = extract_y_label(lines[max(0, heading_idx-5):heading_idx+5])

    metrics = {m:0.0 for m in OUTPUT_METRICS}
    if tables:
        df = tables[0].df if hasattr(tables[0],'df') else tables[0]
        # Find all header rows (sometimes there are multiple header rows)
        header_rows = []
        for i in range(min(3, len(df))):
            if any(re.search(r"\d{4}", str(cell)) for cell in df.iloc[i]):
                header_rows.append(i)
        if not header_rows:
            header_rows = [0]
        header_row = header_rows[-1]  # Use the last header row with years
        header = df.iloc[header_row].astype(str).tolist()
        # Find the column for '3 months ended' and the latest year
        col_idx = None
        best_year = -1
        for idx, h in enumerate(header):
            m = re.search(r"3 months ended.*?(\d{4})", h, re.IGNORECASE)
            if m:
                year = int(m.group(1))
                if year > best_year:
                    best_year = year
                    col_idx = idx
        if col_idx is None:
            # fallback: any column with a year
            for idx, h in enumerate(header):
                m = re.search(r"(\d{4})", h)
                if m:
                    year = int(m.group(1))
                    if year > best_year:
                        best_year = year
                        col_idx = idx
        if col_idx is None:
            col_idx = 1
        # For each metric, scan all rows and match the metric name
        for metric in METRICS[company]:
            found = False
            for i in range(header_row+1, len(df)):
                desc = str(df.iat[i, 0])
                # Try combining with next row if not matched
                mname = match_metric(desc, company)
                if not mname and i+1 < len(df):
                    desc2 = desc + ' ' + str(df.iat[i+1, 0])
                    mname = match_metric(desc2, company)
                if mname == metric:
                    # Now, for this row, scan all columns to find the correct value
                    value = None
                    # Prefer the column with '3 months ended' and correct year
                    if col_idx is not None:
                        value = parse_value(df.iat[i, col_idx])
                    else:
                        # fallback: first numeric value in the row
                        for j in range(1, len(header)):
                            v = parse_value(df.iat[i, j])
                            if v != 0.0:
                                value = v
                                break
                    if value is not None:
                        metrics[metric] = value
                        found = True
                        break
        # Also handle multi-line metric names that may be split across two rows
    return metrics, y_label


def calculate_derived_metrics(metrics, company):
    """
    Calculate derived metrics (e.g., Operating Expenses, Operating Income) for a company.
    Args:
        metrics (dict): Dictionary of base metrics.
        company (str): Company code.
    Returns:
        dict: Updated metrics dictionary with derived values.
    """
    # Always store absolute values for expenses/costs/COGS
    for key in ["COGS", "Distribution Costs", "Administrative Expenses", "Other Expenses", "Other Operating Expense"]:
        if key in metrics:
            metrics[key] = abs(metrics[key]) if metrics[key] is not None else 0
    if company == "DIPD":
        dist = metrics.get("Distribution Costs", 0) or 0
        admin = metrics.get("Administrative Expenses", 0) or 0
        other = metrics.get("Other Expenses", 0) or 0
        op_exp = dist + admin + other
        metrics["Operating Expenses"] = op_exp
        gross = metrics.get("Gross Profit", 0) or 0
        other_income = metrics.get("Other Income", 0) or 0
        metrics["Operating Income"] = gross + other_income - op_exp
    elif company == "REXP":
        dist = metrics.get("Distribution Costs", 0) or 0
        admin = metrics.get("Administrative Expenses", 0) or 0
        other_op = metrics.get("Other Operating Expense", 0) or 0
        op_exp = dist + admin + other_op
        metrics["Operating Expenses"] = op_exp
        gross = metrics.get("Gross Profit", 0) or 0
        other_income = metrics.get("Other Income", 0) or 0
        metrics["Operating Income"] = gross + other_income - op_exp
    # Ensure Operating Income is always positive in the output
    if "Operating Income" in metrics:
        metrics["Operating Income"] = abs(metrics["Operating Income"]) if metrics["Operating Income"] is not None else 0
    return metrics


def main():
    """
    Main workflow: iterate over all company PDF folders, extract and aggregate metrics, and save to CSV.
    """
    ensure_output_dir()
    records=[]
    for company in os.listdir(PDF_ROOT):
        comp_dir=os.path.join(PDF_ROOT,company)
        if not os.path.isdir(comp_dir): continue
        for fname in os.listdir(comp_dir):
            if not fname.lower().endswith('.pdf'): continue
            path=os.path.join(comp_dir,fname)
            rd=parse_date_from_filename(fname)
            td=find_table_date(path)
            mets,yl=extract_all_metrics(path,company,td)
            mets=calculate_derived_metrics(mets,company)
            rec={"Company":company,"ReportDate":str(rd) if rd else "","TableDate":str(td) if td else "","YLabel":yl}
            for m in OUTPUT_METRICS[4:]: rec[m]=mets.get(m,0)
            records.append(rec)
    if records:
        df=pd.DataFrame(records)[OUTPUT_METRICS]
        df.to_csv(OUTPUT_FILE,index=False)
        logging.info(f"Saved to {OUTPUT_FILE}")
    else:
        logging.warning("No records extracted.")

if __name__=="__main__": main()
