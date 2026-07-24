"""
fetch_bhavcopy.py
─────────────────
Downloads NSE EOD data daily:
  Stock bhavcopy → data/YYYY-MM-DD.csv
  Index bhavcopy → data/index/YYYY-MM-DD.csv

NSE index CSV columns (verified):
  Index Name, Index Date, Open Index Value, High Index Value,
  Low Index Value, Closing Index Value, Points Change, Change(%), Volume
"""

import io, time, zipfile, re
from datetime import date, timedelta
from pathlib import Path

import requests
import pandas as pd

STOCK_DIR = Path("data")
INDEX_DIR = Path("data/index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)

DATE_PAT = re.compile(r"^\d{4}-\d{2}-\d{2}$")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.nseindia.com/",
    "Connection":      "keep-alive",
}


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    for attempt in range(3):
        try:
            r = s.get("https://www.nseindia.com", timeout=15)
            print(f"  NSE session: HTTP {r.status_code}")
            time.sleep(2)
            return s
        except Exception as e:
            print(f"  Session attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return s


def fetch_stock(session, dt: date):
    ds  = dt.strftime("%Y%m%d")
    ds2 = dt.strftime("%d%m%Y")

    # New format (2023+) - ZIP file
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
        print(f"    Stock new format error: {e}")

    # Old format - plain CSV
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
        print(f"    Stock old format error: {e}")
    return None


def fetch_index(session, dt: date):
    """
    NSE index bhavcopy.
    URL: https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv
    Columns: Index Name, Index Date, Open Index Value, High Index Value,
             Low Index Value, Closing Index Value, Points Change, Change(%), Volume
    """
    ds  = dt.strftime("%d%m%Y")
    url = (f"https://nsearchives.nseindia.com/content/indices/"
           f"ind_close_all_{ds}.csv")
    try:
        r = session.get(url, timeout=40)
        if r.status_code == 200 and len(r.content) > 200:
            df = pd.read_csv(io.StringIO(r.text), low_memory=False)
            df.columns = df.columns.str.strip()

            print(f"    Index columns: {df.columns.tolist()[:6]}")

            # Rename columns - handle both old and new NSE formats
            df = df.rename(columns={
                "Index Name":          "TckrSymb",
                "Closing Index Value": "ClsPric",
                "Closing":             "ClsPric",    # some versions use this
                "Open Index Value":    "Open",
                "High Index Value":    "High",
                "Low Index Value":     "Low",
                "Points Change":       "PtsChange",
                "Change(%)":           "ChgPct",
            })

            if "TckrSymb" not in df.columns or "ClsPric" not in df.columns:
                print(f"    Index: missing columns. Available: {df.columns.tolist()}")
                return None

            df["TradDt"]  = dt.isoformat()
            df["ClsPric"] = pd.to_numeric(df["ClsPric"], errors="coerce")
            df["TckrSymb"] = df["TckrSymb"].astype(str).str.strip()
            df = df.dropna(subset=["ClsPric"])
            df = df[df["ClsPric"] > 0]

            keep = ["TradDt","TckrSymb","ClsPric","Open","High","Low","PtsChange","ChgPct"]
            df = df[[c for c in keep if c in df.columns]]

            if len(df) > 5:
                return df
            else:
                print(f"    Index: only {len(df)} rows after filtering")
    except Exception as e:
        print(f"    Index error: {e}")
    return None


def get_missing(folder: Path, is_backfill: bool):
    existing  = {f.stem for f in folder.glob("*.csv") if DATE_PAT.match(f.stem)}
    today     = date.today()
    start     = today - timedelta(days=400) if is_backfill else today - timedelta(days=7)
    end       = today - timedelta(days=1)
    all_bdays = [d.date() for d in pd.bdate_range(start=start, end=end)]
    return [d for d in all_bdays if d.isoformat() not in existing]


def cleanup(folder: Path, keep: int = 280):
    files = sorted(f for f in folder.glob("*.csv") if DATE_PAT.match(f.stem))
    for old in files[:-keep]:
        old.unlink()
        print(f"  [DEL] {old.name}")


def main():
    stock_existing = [f for f in STOCK_DIR.glob("*.csv") if DATE_PAT.match(f.stem)]
    index_existing = [f for f in INDEX_DIR.glob("*.csv") if DATE_PAT.match(f.stem)]

    # Detect backfill independently for stocks and index
    # README.md does NOT count as a data file - only YYYY-MM-DD.csv files count
    stock_backfill = len(stock_existing) == 0
    index_backfill = len(index_existing) < 5   # fewer than 5 = needs full backfill

    is_backfill = stock_backfill or index_backfill

    print(f"=== {'BACKFILL' if is_backfill else 'DAILY UPDATE'} ===")
    print(f"Stock files: {len(stock_existing)} (backfill={stock_backfill})")
    print(f"Index files: {len(index_existing)} (backfill={index_backfill})")

    stock_dates = get_missing(STOCK_DIR, stock_backfill)
    index_dates = get_missing(INDEX_DIR, index_backfill)
    all_dates   = sorted(set(stock_dates) | set(index_dates))

    if not all_dates:
        print("All up to date. Nothing to do.")
        return

    print(f"Dates to process: {len(all_dates)}")
    session  = make_session()
    saved_s  = saved_i = skipped = 0

    for i, dt in enumerate(all_dates):
        if i > 0 and i % 20 == 0:
            print(f"  Refreshing session...")
            session = make_session()

        need_s = dt in stock_dates
        need_i = dt in index_dates
        s_ok = i_ok = False

        if need_s and not (STOCK_DIR / f"{dt.isoformat()}.csv").exists():
            df = fetch_stock(session, dt)
            if df is not None:
                df.to_csv(STOCK_DIR / f"{dt.isoformat()}.csv", index=False)
                saved_s += 1
                s_ok = True
            else:
                skipped += 1

        if need_i and not (INDEX_DIR / f"{dt.isoformat()}.csv").exists():
            df = fetch_index(session, dt)
            if df is not None:
                df.to_csv(INDEX_DIR / f"{dt.isoformat()}.csv", index=False)
                saved_i += 1
                i_ok = True

        status = (f"stock={'✓' if s_ok else ('–' if not need_s else '✗')}  "
                  f"index={'✓' if i_ok else ('–' if not need_i else '✗')}")
        print(f"  [{i+1:3}/{len(all_dates)}] {dt}  {status}")
        time.sleep(0.8)

    print(f"\nDone. Stocks={saved_s}, Index={saved_i}, Skipped={skipped}")
    cleanup(STOCK_DIR)
    cleanup(INDEX_DIR)


if __name__ == "__main__":
    main()
