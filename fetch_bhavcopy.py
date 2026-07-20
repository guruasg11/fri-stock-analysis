"""
fetch_bhavcopy.py
─────────────────
Downloads two types of NSE EOD data daily:
  1. Stock bhavcopy  → data/stocks/YYYY-MM-DD.csv
  2. Index bhavcopy  → data/index/YYYY-MM-DD.csv

On first run (empty data/): downloads full 1-year backfill (~260 days each).
On daily runs: downloads only missing recent dates.
Keeps max 280 files in each folder.
"""

import io, time, zipfile
from datetime import date, timedelta
from pathlib import Path

import requests
import pandas as pd

STOCK_DIR = Path("data/stocks")
INDEX_DIR = Path("data/index")
STOCK_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.nseindia.com/",
}


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    for _ in range(3):
        try:
            s.get("https://www.nseindia.com", timeout=15)
            time.sleep(1)
            break
        except Exception:
            time.sleep(3)
    return s


def fetch_stock_bhavcopy(session, dt: date):
    """Returns clean stock DataFrame or None."""
    ds = dt.strftime("%Y%m%d")
    # New format (2023+)
    url = (f"https://nsearchives.nseindia.com/content/cm/"
           f"BhavCopy_NSE_CM_0_0_0_{ds}_F_0000.csv.zip")
    try:
        r = session.get(url, timeout=30)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_csv(f, low_memory=False)
            df.columns = df.columns.str.strip()
            if "SctySrs" in df.columns:
                df = df[df["SctySrs"].astype(str).str.strip() == "EQ"]
            keep = ["TckrSymb","SctySrs","HghPric","LwPric","ClsPric","PrvsClsgPric","TtlTradgVol"]
            df = df[[c for c in keep if c in df.columns]].copy()
            df["TradDt"] = dt.isoformat()
            return df
    except Exception:
        pass

    # Old format fallback
    ds2 = dt.strftime("%d%m%Y")
    url2 = (f"https://nsearchives.nseindia.com/products/content/"
            f"sec_bhavdata_full_{ds2}.csv")
    try:
        r = session.get(url2, timeout=30)
        if r.status_code == 200:
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
            keep = ["TckrSymb","SctySrs","HghPric","LwPric","ClsPric","PrvsClsgPric","TtlTradgVol"]
            df = df[[c for c in keep if c in df.columns]].copy()
            df["TradDt"] = dt.isoformat()
            return df
    except Exception:
        pass
    return None


def fetch_index_bhavcopy(session, dt: date):
    """Returns index closing DataFrame or None."""
    ds = dt.strftime("%d%m%Y")
    url = f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{ds}.csv"
    try:
        r = session.get(url, timeout=30)
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text), low_memory=False)
            df.columns = df.columns.str.strip()
            if "Index Name" not in df.columns:
                return None
            df = df.rename(columns={"Index Name": "TckrSymb", "Closing": "ClsPric"})
            df["TradDt"] = dt.isoformat()
            df["ClsPric"] = pd.to_numeric(df["ClsPric"], errors="coerce")
            return df[["TradDt","TckrSymb","ClsPric"]].dropna(subset=["ClsPric"])
    except Exception:
        pass
    return None


def get_dates_to_fetch(folder: Path, is_backfill: bool) -> list:
    existing = {f.stem for f in folder.glob("*.csv")}
    today    = date.today()
    if is_backfill:
        start = today - timedelta(days=400)
        end   = today - timedelta(days=1)
    else:
        start = today - timedelta(days=7)
        end   = today
    dates = [d.date() for d in pd.bdate_range(start=start, end=end)]
    return [d for d in dates if d.isoformat() not in existing]


def cleanup(folder: Path, keep: int = 280):
    files = sorted(folder.glob("*.csv"))
    for old in files[:-keep]:
        old.unlink()
        print(f"  [DEL] {old.name}")


def main():
    stock_existing = list(STOCK_DIR.glob("*.csv"))
    index_existing = list(INDEX_DIR.glob("*.csv"))
    is_backfill    = len(stock_existing) == 0

    if is_backfill:
        print("=== FIRST RUN: Backfilling 1 year ===")
    else:
        print("=== DAILY UPDATE ===")

    session = make_session()

    stock_dates = get_dates_to_fetch(STOCK_DIR, is_backfill)
    index_dates = get_dates_to_fetch(INDEX_DIR, is_backfill)
    all_dates   = sorted(set(stock_dates) | set(index_dates))

    if not all_dates:
        print("All data is up to date.")
        return

    print(f"Dates to process: {len(all_dates)}")
    saved_s = saved_i = skipped = 0

    for i, dt in enumerate(all_dates):
        # Refresh session every 30 requests
        if i > 0 and i % 30 == 0:
            session = make_session()

        need_stock = dt in stock_dates
        need_index = dt in index_dates

        # Stock bhavcopy
        if need_stock:
            df_s = fetch_stock_bhavcopy(session, dt)
            if df_s is not None and not df_s.empty:
                df_s.to_csv(STOCK_DIR / f"{dt.isoformat()}.csv", index=False)
                saved_s += 1
                if is_backfill:
                    print(f"  [{i+1}/{len(all_dates)}] {dt} stock ✓ ({len(df_s)} rows)")
            else:
                skipped += 1

        # Index bhavcopy
        if need_index:
            df_i = fetch_index_bhavcopy(session, dt)
            if df_i is not None and not df_i.empty:
                df_i.to_csv(INDEX_DIR / f"{dt.isoformat()}.csv", index=False)
                saved_i += 1
                if is_backfill:
                    print(f"  [{i+1}/{len(all_dates)}] {dt} index ✓ ({len(df_i)} indices)")

        if not is_backfill:
            print(f"  {dt} → stock={'✓' if need_stock else '-'}, index={'✓' if need_index else '-'}")

        time.sleep(0.6)

    print(f"\nDone. Stocks saved={saved_s}, Indices saved={saved_i}, Skipped(holidays)={skipped}")

    cleanup(STOCK_DIR)
    cleanup(INDEX_DIR)


if __name__ == "__main__":
    main()
