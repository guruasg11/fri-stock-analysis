"""
fetch_bhavcopy.py
─────────────────
Downloads two NSE EOD files daily:
  1. Stock bhavcopy  → data/YYYY-MM-DD.csv
  2. Index bhavcopy  → data/index/YYYY-MM-DD.csv

First run: downloads full 1-year backfill (~260 days).
Daily run: downloads only missing recent dates.
"""

import io, time, zipfile
from datetime import date, timedelta
from pathlib import Path

import requests
import pandas as pd

STOCK_DIR = Path("data")
INDEX_DIR = Path("data/index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.nseindia.com/",
    "Connection":      "keep-alive",
}


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    for _ in range(3):
        try:
            r = s.get("https://www.nseindia.com", timeout=15)
            print(f"  NSE homepage: {r.status_code}")
            time.sleep(2)
            break
        except Exception as e:
            print(f"  Session init failed: {e}")
            time.sleep(3)
    return s


def fetch_stock(session, dt: date):
    """Download stock bhavcopy. Returns DataFrame or None."""
    ds  = dt.strftime("%Y%m%d")
    ds2 = dt.strftime("%d%m%Y")

    # New format (2023+)
    url = (f"https://nsearchives.nseindia.com/content/cm/"
           f"BhavCopy_NSE_CM_0_0_0_{ds}_F_0000.csv.zip")
    try:
        r = session.get(url, timeout=40)
        if r.status_code == 200 and len(r.content) > 1000:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_csv(f, low_memory=False)
            df.columns = df.columns.str.strip()
            if "SctySrs" in df.columns:
                df = df[df["SctySrs"].astype(str).str.strip() == "EQ"]
            keep = ["TckrSymb","SctySrs","HghPric","LwPric",
                    "ClsPric","PrvsClsgPric","TtlTradgVol"]
            df = df[[c for c in keep if c in df.columns]].copy()
            df["TradDt"] = dt.isoformat()
            if len(df) > 100:
                return df
    except Exception as e:
        print(f"    New format error: {e}")

    # Old format fallback
    url2 = (f"https://nsearchives.nseindia.com/products/content/"
             f"sec_bhavdata_full_{ds2}.csv")
    try:
        r = session.get(url2, timeout=40)
        if r.status_code == 200 and len(r.content) > 1000:
            df = pd.read_csv(io.StringIO(r.text), low_memory=False)
            df.columns = df.columns.str.strip()
            df = df.rename(columns={
                "SYMBOL":"TckrSymb","SERIES":"SctySrs",
                "HIGH":"HghPric","LOW":"LwPric",
                "CLOSE":"ClsPric","PREVCLOSE":"PrvsClsgPric",
                "TOTTRDQTY":"TtlTradgVol",
            })
            if "SctySrs" in df.columns:
                df = df[df["SctySrs"].astype(str).str.strip() == "EQ"]
            keep = ["TckrSymb","SctySrs","HghPric","LwPric",
                    "ClsPric","PrvsClsgPric","TtlTradgVol"]
            df = df[[c for c in keep if c in df.columns]].copy()
            df["TradDt"] = dt.isoformat()
            if len(df) > 100:
                return df
    except Exception as e:
        print(f"    Old format error: {e}")

    return None


def fetch_index(session, dt: date):
    """Download index bhavcopy. Returns DataFrame or None."""
    ds = dt.strftime("%d%m%Y")
    url = (f"https://nsearchives.nseindia.com/content/indices/"
           f"ind_close_all_{ds}.csv")
    try:
        r = session.get(url, timeout=40)
        if r.status_code == 200 and len(r.content) > 500:
            df = pd.read_csv(io.StringIO(r.text), low_memory=False)
            df.columns = df.columns.str.strip()
            if "Index Name" not in df.columns:
                return None
            # Keep only needed columns
            keep_cols = ["Index Name","Open","High","Low","Closing",
                         "Points Change","Change(%)"]
            df = df[[c for c in keep_cols if c in df.columns]].copy()
            df = df.rename(columns={
                "Index Name": "TckrSymb",
                "Closing":    "ClsPric",
            })
            df["TradDt"]  = dt.isoformat()
            df["ClsPric"] = pd.to_numeric(df["ClsPric"], errors="coerce")
            df = df.dropna(subset=["ClsPric"])
            if len(df) > 5:
                return df
    except Exception as e:
        print(f"    Index error: {e}")
    return None


def get_missing_dates(folder: Path, is_backfill: bool) -> list:
    import re
    date_pat  = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    existing  = {f.stem for f in folder.glob("*.csv") if date_pat.match(f.stem)}
    today     = date.today()
    start     = today - timedelta(days=400) if is_backfill else today - timedelta(days=7)
    end       = today - timedelta(days=1)
    all_bdays = [d.date() for d in pd.bdate_range(start=start, end=end)]
    return [d for d in all_bdays if d.isoformat() not in existing]


def cleanup(folder: Path, keep: int = 280):
    import re
    date_pat = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    files = sorted(f for f in folder.glob("*.csv") if date_pat.match(f.stem))
    for old in files[:-keep]:
        old.unlink()
        print(f"  [DEL] {old.name}")


def main():
    import re
    date_pat = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    stock_existing = [f for f in STOCK_DIR.glob("*.csv") if date_pat.match(f.stem)]
    is_backfill    = len(stock_existing) == 0

    if is_backfill:
        print("=== FIRST RUN: Full backfill (1 year) ===")
    else:
        print("=== DAILY UPDATE ===")
        print(f"Existing stock files: {len(stock_existing)}")

    stock_dates  = get_missing_dates(STOCK_DIR, is_backfill)
    index_dates  = get_missing_dates(INDEX_DIR, is_backfill)
    all_dates    = sorted(set(stock_dates) | set(index_dates))

    if not all_dates:
        print("All data up to date. Nothing to do.")
        return

    print(f"Dates to process: {len(all_dates)}")
    session = make_session()
    saved_s = saved_i = skipped = 0

    for i, dt in enumerate(all_dates):
        # Refresh session every 25 requests
        if i > 0 and i % 25 == 0:
            print(f"  Refreshing session at {i}/{len(all_dates)}...")
            session = make_session()

        need_stock = dt in stock_dates
        need_index = dt in index_dates
        s_ok = i_ok = False

        if need_stock:
            out = STOCK_DIR / f"{dt.isoformat()}.csv"
            if not out.exists():
                df = fetch_stock(session, dt)
                if df is not None:
                    df.to_csv(out, index=False)
                    saved_s += 1
                    s_ok = True
                else:
                    skipped += 1

        if need_index:
            out = INDEX_DIR / f"{dt.isoformat()}.csv"
            if not out.exists():
                df = fetch_index(session, dt)
                if df is not None:
                    df.to_csv(out, index=False)
                    saved_i += 1
                    i_ok = True

        status = f"stock={'✓' if s_ok else ('–' if not need_stock else '✗')}  index={'✓' if i_ok else ('–' if not need_index else '✗')}"
        print(f"  [{i+1:3}/{len(all_dates)}] {dt}  {status}")
        time.sleep(0.8)

    print(f"\nDone. Stocks saved={saved_s}, Index saved={saved_i}, Skipped={skipped}")
    cleanup(STOCK_DIR)
    cleanup(INDEX_DIR)


if __name__ == "__main__":
    main()
