"""
fetch_bhavcopy.py
─────────────────
Run by GitHub Actions on every push AND daily at 4:30 PM IST.

First run (data/ is empty):
    Downloads ~290 business days (~1 full year) of bhavcopy files.
    NSE holidays are silently skipped (their files simply don't exist).

Subsequent runs:
    Downloads only the current/most-recent trading day file.
    Already-downloaded files are never re-fetched.

Keeps at most 280 files (just over 1 year) to limit repo size.
"""

import io, os, sys, time, zipfile
from datetime import date, timedelta
from pathlib import Path

import requests
import pandas as pd

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ── NSE session with required headers and cookie ─────────────────────────────
def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":          "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.nseindia.com/",
    })
    # Prime the session to get NSE cookie (needed to avoid 403)
    for attempt in range(3):
        try:
            s.get("https://www.nseindia.com", timeout=15)
            time.sleep(1)
            break
        except Exception as e:
            print(f"  Cookie fetch attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return s


# ── Download one day's bhavcopy, return DataFrame or None ────────────────────
def fetch_one_day(session, dt: date):
    ds = dt.strftime("%Y%m%d")

    # Try new format first (2023+)
    url_new = (
        f"https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{ds}_F_0000.csv.zip"
    )
    try:
        r = session.get(url_new, timeout=30)
        if r.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_csv(f, low_memory=False)
            df = df.rename(columns=lambda c: c.strip())
            # Keep only EQ series and needed columns
            if "SctySrs" in df.columns:
                df = df[df["SctySrs"].astype(str).str.strip() == "EQ"]
            needed = ["TckrSymb","SctySrs","HghPric","LwPric","ClsPric","PrvsClsgPric","TtlTradgVol"]
            df = df[[c for c in needed if c in df.columns]].copy()
            df["TradDt"] = dt.isoformat()
            return df
    except Exception as e:
        pass  # fall through to old format

    # Try old format (fallback)
    ds_old = dt.strftime("%d%m%Y")
    url_old = (
        f"https://nsearchives.nseindia.com/products/content/"
        f"sec_bhavdata_full_{ds_old}.csv"
    )
    try:
        r = session.get(url_old, timeout=30)
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text), low_memory=False)
            df.columns = df.columns.str.strip()
            df = df.rename(columns={
                "SYMBOL":   "TckrSymb", "SERIES":   "SctySrs",
                "HIGH":     "HghPric",  "LOW":      "LwPric",
                "CLOSE":    "ClsPric",  "PREVCLOSE":"PrvsClsgPric",
                "TOTTRDQTY":"TtlTradgVol",
            })
            if "SctySrs" in df.columns:
                df = df[df["SctySrs"].astype(str).str.strip() == "EQ"]
            needed = ["TckrSymb","SctySrs","HghPric","LwPric","ClsPric","PrvsClsgPric","TtlTradgVol"]
            df = df[[c for c in needed if c in df.columns]].copy()
            df["TradDt"] = dt.isoformat()
            return df
    except Exception as e:
        pass

    return None  # This date is a holiday or weekend


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    existing = {f.stem for f in DATA_DIR.glob("*.csv")}
    is_backfill = len(existing) == 0

    if is_backfill:
        print("=== FIRST RUN: Backfilling 1 year of NSE data ===")
        today  = date.today()
        start  = today - timedelta(days=400)   # ~14 months back (covers holidays)
        end    = today - timedelta(days=1)      # up to yesterday
        dates  = [
            d.date()
            for d in pd.bdate_range(start=start, end=end)
        ]
        print(f"Will attempt {len(dates)} business days ({start} → {end})")
    else:
        print("=== DAILY UPDATE ===")
        # Try today and last 5 business days to catch up if a day was missed
        today = date.today()
        dates = [
            d.date()
            for d in pd.bdate_range(
                start=today - timedelta(days=7),
                end=today
            )
        ]
        dates = [d for d in dates if d.isoformat() not in existing]
        if not dates:
            print("All recent trading days already downloaded. Nothing to do.")
            return
        print(f"Missing {len(dates)} recent trading days: {dates}")

    session    = make_session()
    saved      = 0
    skipped    = 0    # holidays / weekends with no bhavcopy

    for i, dt in enumerate(dates):
        out = DATA_DIR / f"{dt.isoformat()}.csv"
        if out.exists():
            continue

        if is_backfill and i % 20 == 0:
            # Refresh cookie every 20 requests during long backfill
            session = make_session()

        df = fetch_one_day(session, dt)
        if df is not None and not df.empty:
            df.to_csv(out, index=False)
            saved += 1
            if is_backfill:
                print(f"  [{i+1}/{len(dates)}] {dt} ✓  ({len(df)} rows)")
            else:
                print(f"  {dt} ✓  ({len(df)} rows)")
        else:
            skipped += 1
            if is_backfill and i % 10 == 0:
                print(f"  [{i+1}/{len(dates)}] {dt} – holiday/weekend, skipped")

        # Polite delay to avoid rate limiting
        time.sleep(0.5)

    print(f"\nDone. Saved={saved}, Skipped(holidays)={skipped}")

    # Keep only latest 280 files
    all_files = sorted(DATA_DIR.glob("*.csv"))
    if len(all_files) > 280:
        for old_f in all_files[:-280]:
            old_f.unlink()
            print(f"Deleted old file: {old_f.name}")


if __name__ == "__main__":
    main()
