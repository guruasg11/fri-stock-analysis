"""
NSE EOD Tracker – Streamlit app
================================
Zero live API / network calls.
All data comes from NSE bhavcopy CSV files in the data/ folder,
populated automatically by GitHub Actions after every market close.

First deploy:
  GitHub Actions triggers on push, downloads 1 year of backfill,
  commits to repo, Streamlit Cloud redeploys with the data.
  This takes ~5-10 minutes. The app shows a friendly waiting screen
  and auto-refreshes until data arrives.
"""

import time
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE EOD Tracker",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .block-container { padding-top:.5rem; padding-bottom:.5rem }
  .metric-card {
    background:#0f172a; border:1px solid #1e293b;
    border-radius:10px; padding:14px 8px;
    text-align:center; margin-bottom:6px;
  }
  .metric-card .num { font-size:1.8rem; font-weight:700; line-height:1.1 }
  .metric-card .lbl { font-size:.7rem; color:#94a3b8; margin-top:3px }
  .g { color:#22c55e } .r { color:#ef4444 } .w { color:#f1f5f9 }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")

SECTORS = {
    "My Watchlist":    ["ASTRAL","TATAMOTORS","BANKBARODA","PFC","RECLTD",
                        "HUDCO","RVNL","GODREJIND"],
    "Nifty 50":        ["RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","BHARTIARTL",
                        "ITC","LT","HINDUNILVR","SBIN","BAJFINANCE","KOTAKBANK",
                        "AXISBANK","ASIANPAINT","MARUTI","HCLTECH","SUNPHARMA",
                        "TITAN","WIPRO","ONGC","NTPC","POWERGRID","ULTRACEMCO",
                        "NESTLEIND","TECHM","INDUSINDBK","ADANIENT","ADANIPORTS",
                        "BAJAJFINSV","DRREDDY","DIVISLAB","CIPLA","BPCL",
                        "COALINDIA","HEROMOTOCO","M&M","TATASTEEL","JSWSTEEL",
                        "EICHERMOT","GRASIM"],
    "Nifty Bank":      ["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK","PNB",
                        "INDUSINDBK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB",
                        "AUBANK","BANKBARODA"],
    "Nifty IT":        ["TCS","INFY","HCLTECH","WIPRO","TECHM","LTIM",
                        "PERSISTENT","MPHASIS","COFORGE","OFSS"],
    "Nifty Auto":      ["MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO",
                        "EICHERMOT","BOSCHLTD","MRF","BALKRISIND","MOTHERSON",
                        "BHARATFORG","APOLLOTYRE"],
    "Nifty FMCG":      ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO",
                        "COLPAL","GODREJCP","EMAMILTD","TATACONSUM","UBL","MCDOWELL-N"],
    "Nifty Pharma":    ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP",
                        "TORNTPHARM","ALKEM","AUROPHARMA","LUPIN","BIOCON",
                        "IPCALAB","GLENMARK"],
    "Nifty Metal":     ["TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","VEDL","SAIL",
                        "NMDC","APLAPOLLO","NATIONALUM","HINDCOPPER","MOIL","WELCORP"],
    "Nifty Realty":    ["DLF","GODREJPROP","OBEROIRLTY","PHOENIXLTD","PRESTIGE",
                        "BRIGADE","SOBHA","SUNTECK","KOLTEPATIL","MAHLIFE"],
    "Nifty Energy":    ["RELIANCE","ONGC","NTPC","POWERGRID","BPCL","IOC","GAIL",
                        "TATAPOWER","ADANIGREEN","ADANIPOWER","CESC"],
    "Nifty Infra":     ["LT","ADANIPORTS","POWERGRID","NTPC","BHARTIARTL","RVNL",
                        "IRFC","PFC","RECLTD","HUDCO","NBCC","IRB"],
    "Nifty PSU Bank":  ["SBIN","PNB","BANKBARODA","CANARABANK","UNIONBANK","BANKINDIA",
                        "CENTRALBK","UCOBANK","MAHABANK","INDIANB"],
    "Nifty Midcap":    ["PERSISTENT","POLYCAB","FEDERALBNK","LTTS","MPHASIS","COFORGE",
                        "ABCAPITAL","SUNDARMFIN","VOLTAS","ASTRAL","PIIND","ZYDUSLIFE",
                        "MAXHEALTH","CAMS","ANGELONE","BSE","MCX","DIXON","AMBER","TRENT"],
    "Nifty Fin Svcs":  ["HDFCBANK","ICICIBANK","BAJFINANCE","KOTAKBANK","AXISBANK",
                        "SBIN","BAJAJFINSV","HDFCAMC","MUTHOOTFIN","CHOLAFIN",
                        "M&MFIN","LICHSGFIN"],
    "Nifty Oil & Gas": ["RELIANCE","ONGC","BPCL","IOC","GAIL","HINDPETRO",
                        "MGL","IGL","PETRONET","GSPL","CASTROLIND"],
    "Custom Basket":   [],
}

AD_UNIVERSE = list(dict.fromkeys([
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","BHARTIARTL","ITC","LT",
    "HINDUNILVR","SBIN","BAJFINANCE","KOTAKBANK","AXISBANK","ASIANPAINT",
    "MARUTI","HCLTECH","SUNPHARMA","TITAN","WIPRO","ONGC","NTPC","POWERGRID",
    "ULTRACEMCO","NESTLEIND","TECHM","INDUSINDBK","ADANIENT","ADANIPORTS",
    "BAJAJFINSV","DRREDDY","DIVISLAB","CIPLA","BPCL","COALINDIA","HEROMOTOCO",
    "M&M","TATASTEEL","JSWSTEEL","EICHERMOT","GRASIM","DMART","SIEMENS",
    "HAVELLS","PIDILITIND","DABUR","MARICO","COLPAL","GODREJCP","TATACONSUM",
    "BRITANNIA","MUTHOOTFIN","CHOLAFIN","SHREECEM","BERGEPAINT","TORNTPHARM",
    "LUPIN","BIOCON","ALKEM","AUROPHARMA","AMBUJACEM","HINDPETRO","IOC",
    "PETRONET","MGL","IGL","DLF","GODREJPROP","OBEROIRLTY","PHOENIXLTD",
    "PRESTIGE","APOLLOHOSP","MAXHEALTH","FORTIS","LALPATHLAB","PERSISTENT",
    "POLYCAB","LTTS","MPHASIS","COFORGE","ZYDUSLIFE","CAMS","ANGELONE","BSE",
    "MCX","VOLTAS","ASTRAL","PIIND","ABCAPITAL","SUNDARMFIN","FEDERALBNK",
    "IDFCFIRSTB","AUBANK","BANDHANBNK","PNB","BANKBARODA","CANARABANK",
    "UNIONBANK","BANKINDIA","CENTRALBK","INDIANB","TATAMOTORS","PFC","RECLTD",
    "HUDCO","RVNL","IRFC","RAILTEL","IRCON","RITES","NBCC","HFCL","SUZLON",
    "NHPC","SJVN","TATAPOWER","ADANIGREEN","ADANIPOWER","CESC","JSWENERGY",
    "TORNTPOWER","BAJAJ-AUTO","BOSCHLTD","MRF","BALKRISIND","MOTHERSON",
    "BHARATFORG","APOLLOTYRE","VEDL","NMDC","APLAPOLLO","NATIONALUM",
    "HINDCOPPER","MOIL","SAIL","HINDALCO","HDFCAMC","HDFCLIFE","SBILIFE",
    "M&MFIN","LICHSGFIN","DIXON","AMBER","WHIRLPOOL","BLUESTAR","CROMPTON",
    "VGUARD","ZOMATO","NYKAA","DELHIVERY","TRENT","UPL","COROMANDEL",
    "CHAMBLFERT","DEEPAKNTR","OFSS","KPITTECH","TATAELXSI","HAPPYMNDS",
    "MASTEK","LTIM","VARUNBEV","RADICO","UBL","MCDOWELL-N","JUBLFOOD",
    "KAJARIACER","GODREJIND","EMAMILTD","IPCALAB","GLENMARK","BRIGADE",
    "SOBHA","IRB","GSPL","WELCORP","MAHLIFE","SUNTECK","KOLTEPATIL",
]))

PCT_COLS = ["1D %","1W %","2W %","1M %","3M %","6M %","1Y %",
            "vs 52WH%","vs 52WL%"]


# ── DATA LOADING (cached 1 hour) ──────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def load_history():
    """
    Reads all YYYY-MM-DD.csv files from data/ folder.
    Returns clean DataFrame with columns:
        TradDt, TckrSymb, ClsPric, HghPric, LwPric, PrvsClsgPric
    """
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        return pd.DataFrame()

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, low_memory=False)
            df.columns = df.columns.str.strip()
            # Handle both old and new bhavcopy column names
            df = df.rename(columns={
                "SYMBOL":"TckrSymb", "SERIES":"SctySrs",
                "HIGH":"HghPric",   "LOW":"LwPric",
                "CLOSE":"ClsPric",  "PREVCLOSE":"PrvsClsgPric",
            })
            if "TradDt" not in df.columns:
                df["TradDt"] = f.stem
            dfs.append(df)
        except Exception:
            continue

    if not dfs:
        return pd.DataFrame()

    hist = pd.concat(dfs, ignore_index=True)

    # EQ series only
    if "SctySrs" in hist.columns:
        hist = hist[hist["SctySrs"].astype(str).str.strip() == "EQ"]

    hist["TradDt"]   = pd.to_datetime(hist["TradDt"], errors="coerce")
    hist["TckrSymb"] = hist["TckrSymb"].astype(str).str.strip().str.upper()

    for col in ["ClsPric","HghPric","LwPric","PrvsClsgPric"]:
        if col in hist.columns:
            hist[col] = pd.to_numeric(hist[col], errors="coerce")

    hist = (hist
            .dropna(subset=["TradDt","TckrSymb","ClsPric"])
            .sort_values("TradDt")
            .reset_index(drop=True))
    return hist


# ── METRIC CALCULATION ────────────────────────────────────────────────────────
def calc(hist: pd.DataFrame, sym: str) -> dict:
    df = hist[hist["TckrSymb"] == sym].sort_values("TradDt")
    if len(df) < 5:
        return {"Symbol": sym, "Error": "< 5 days data"}

    close = df["ClsPric"].astype(float).values
    high  = df["HghPric"].astype(float).values  if "HghPric"      in df.columns else close.copy()
    low   = df["LwPric"].astype(float).values   if "LwPric"       in df.columns else close.copy()
    ltp   = float(close[-1])
    prev  = (float(df["PrvsClsgPric"].iloc[-1])
             if "PrvsClsgPric" in df.columns and not pd.isna(df["PrvsClsgPric"].iloc[-1])
             else float(close[-2]))

    cs = pd.Series(close)

    def ret(n):
        if len(close) <= n: return np.nan
        p = float(close[-(n + 1)])
        return round(((ltp - p) / p) * 100, 2) if p else np.nan

    def ema(span):
        return round(float(cs.ewm(span=span, adjust=False).mean().iloc[-1]), 2)

    h52 = round(float(high.max()), 2)
    l52 = round(float(low.min()),  2)

    return {
        "Symbol":   sym,
        "LTP":      round(ltp, 2),
        "1D %":     round(((ltp - prev) / prev) * 100, 2) if prev else np.nan,
        "1W %":     ret(5),
        "2W %":     ret(10),
        "1M %":     ret(21),
        "3M %":     ret(63),
        "6M %":     ret(126),
        "1Y %":     ret(251),
        "4 EMA":    ema(4),
        "10 EMA":   ema(10),
        "20 EMA":   ema(20),
        "50 EMA":   ema(50),
        "100 EMA":  ema(100),
        "52W High": h52,
        "vs 52WH%": round(((ltp - h52) / h52) * 100, 2),
        "52W Low":  l52,
        "vs 52WL%": round(((ltp - l52) / l52) * 100, 2),
        "Error":    None,
    }


# ── STYLING ───────────────────────────────────────────────────────────────────
def cell_color(val, cap=20):
    try:
        val = float(val)
    except Exception:
        return ""
    if pd.isna(val):
        return ""
    i = min(abs(val) / cap, 1.0)
    if val >= 0:
        r, g, b = int(255 - i*195), int(255 - i*55),  int(255 - i*195)
    else:
        r, g, b = int(255 - i*35),  int(255 - i*205), int(255 - i*205)
    return f"background-color:rgb({r},{g},{b});color:#000;font-weight:600;"

def style_df(df, cap=20):
    cols = [c for c in PCT_COLS if c in df.columns]
    fmt  = {c: "{:.2f}" for c in df.columns if c != "Symbol"}
    s    = df.style.format(fmt, na_rep="—")
    fn   = s.map if hasattr(s, "map") else s.applymap
    return fn(lambda v: cell_color(v, cap), subset=cols)

def mcard(num, lbl, clr="w"):
    return (f'<div class="metric-card">'
            f'<div class="num {clr}">{num}</div>'
            f'<div class="lbl">{lbl}</div>'
            f'</div>')


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
if "custom_stocks" not in st.session_state:
    st.session_state.custom_stocks = []

st.sidebar.title("📈 NSE EOD Tracker")
page = st.sidebar.radio(
    "View",
    ["📊 Sector Tracker", "📉 Advance / Decline"],
    label_visibility="collapsed",
)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
hist = load_history()

# ── WAITING SCREEN (first deploy, data not yet populated) ─────────────────────
if hist.empty:
    st.title("📈 NSE EOD Tracker")
    st.info(
        "⏳ **Setting up for the first time…**\n\n"
        "GitHub Actions is downloading 1 year of NSE bhavcopy data right now. "
        "This runs automatically — you don't need to do anything.\n\n"
        "**It takes about 5–10 minutes.** This page will refresh automatically."
    )
    st.markdown("#### What's happening:")
    st.markdown("""
- ✅ Your app is deployed on Streamlit Cloud  
- 🔄 GitHub Actions triggered on your push — downloading ~260 days of NSE data  
- ⏳ Once it finishes and commits the files, this page loads automatically  

Check your GitHub repo → **Actions** tab to see live progress.
    """)
    # Auto-refresh every 30 seconds until data arrives
    st.markdown(
        '<meta http-equiv="refresh" content="30">',
        unsafe_allow_html=True,
    )
    st.stop()

# Data is available — show stats in sidebar
last_date = hist["TradDt"].max().date()
all_sym   = sorted(hist["TckrSymb"].unique())
num_days  = hist["TradDt"].nunique()

st.sidebar.markdown(
    f"---\n"
    f"📅 **Last EOD:** `{last_date}`  \n"
    f"📂 **Days loaded:** {num_days}  \n"
    f"🏷️ **Stocks:** {len(all_sym)}"
)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 – SECTOR TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Sector Tracker":
    st.header("📊 Sector Tracker")

    sector_names = [s for s in SECTORS if s != "Custom Basket"] + ["Custom Basket"]
    sel_sector   = st.sidebar.selectbox("Sector / Basket", sector_names)
    def_stocks   = SECTORS.get(sel_sector, [])

    available = [s for s in def_stocks if s in all_sym]
    missing   = [s for s in def_stocks if s not in all_sym]
    opts      = sorted(set(available + st.session_state.custom_stocks))
    ms_def    = (st.session_state.custom_stocks
                 if sel_sector == "Custom Basket"
                 else available)

    sel = st.sidebar.multiselect("Stocks", options=opts, default=ms_def)

    inp = st.sidebar.text_input("Add stock (e.g. ZOMATO)").upper().strip()
    ca, cb = st.sidebar.columns(2)
    with ca:
        if st.button("➕ Add") and inp:
            if inp not in st.session_state.custom_stocks:
                st.session_state.custom_stocks.append(inp)
                st.rerun()
    with cb:
        if st.button("🗑 Clear"):
            st.session_state.custom_stocks = []
            st.rerun()

    final = list(dict.fromkeys(sel + st.session_state.custom_stocks))

    if missing:
        st.info(
            f"ℹ️ {len(missing)} stocks not yet in data: "
            + ", ".join(missing[:10])
            + (" …" if len(missing) > 10 else "")
        )

    if not final:
        st.info("Select stocks from the sidebar.")
        st.stop()

    results, errors = [], []
    for sym in final:
        d = calc(hist, sym)
        if d.get("Error"):
            errors.append(f"**{sym}**: {d['Error']}")
        else:
            d.pop("Error", None)
            results.append(d)

    if errors:
        with st.expander(f"⚠️ {len(errors)} stock(s) skipped"):
            for e in errors:
                st.write(e)

    if not results:
        st.warning("No metrics calculated — check your stock symbols.")
        st.stop()

    df = pd.DataFrame(results)
    num_cols = [c for c in df.columns if c != "Symbol"]

    avg = {"Symbol": f"📊 {sel_sector} AVG"}
    avg.update(df[num_cols].mean(numeric_only=True).round(2).to_dict())

    df_all = pd.concat([pd.DataFrame([avg]), df], ignore_index=True)

    st.caption(
        f"{sel_sector} · {len(results)} stocks · EOD {last_date} · "
        "🟢 positive  🔴 negative"
    )
    st.dataframe(style_df(df_all), use_container_width=True, height=600)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 – ADVANCE / DECLINE
# ═══════════════════════════════════════════════════════════════════════════════
else:
    st.header("📉 Market Advance / Decline")
    st.caption(
        f"Universe: {len(AD_UNIVERSE)} NSE stocks (≥ ₹1000 Cr market cap) · "
        f"EOD {last_date}"
    )

    @st.cache_data(show_spinner=False, ttl=3600)
    def build_ad(last_dt_str: str, n_days: int):
        """Cache key = last EOD date + number of days loaded."""
        rows = []
        for sym in AD_UNIVERSE:
            df = hist[hist["TckrSymb"] == sym].sort_values("TradDt")
            if len(df) < 10:
                continue
            close = df["ClsPric"].astype(float).values
            high  = df["HghPric"].astype(float).values if "HghPric" in df.columns else close.copy()
            low   = df["LwPric"].astype(float).values  if "LwPric"  in df.columns else close.copy()
            ltp   = float(close[-1])
            prev  = (float(df["PrvsClsgPric"].iloc[-1])
                     if "PrvsClsgPric" in df.columns and not pd.isna(df["PrvsClsgPric"].iloc[-1])
                     else float(close[-2]))
            cs = pd.Series(close)

            def ema(sp):
                return float(cs.ewm(span=sp, adjust=False).mean().iloc[-1])

            e4, e10, e20, e50, e100 = ema(4), ema(10), ema(20), ema(50), ema(100)
            h52 = float(high.max())
            l52 = float(low.min())
            chg = round(((ltp - prev) / prev) * 100, 2) if prev else 0.0

            rows.append({
                "Symbol":   sym,
                "LTP":      round(ltp, 2),
                "Day Chg%": chg,
                ">4EMA":    "✅" if ltp > e4   else "❌",
                "4 EMA":    round(e4,   2),
                ">10EMA":   "✅" if ltp > e10  else "❌",
                "10 EMA":   round(e10,  2),
                ">20EMA":   "✅" if ltp > e20  else "❌",
                "20 EMA":   round(e20,  2),
                ">50EMA":   "✅" if ltp > e50  else "❌",
                "50 EMA":   round(e50,  2),
                ">100EMA":  "✅" if ltp > e100 else "❌",
                "100 EMA":  round(e100, 2),
                "vs 52WH%": round(((ltp - h52) / h52) * 100, 2),
                "vs 52WL%": round(((ltp - l52) / l52) * 100, 2),
                "52W High": round(h52, 2),
                "52W Low":  round(l52, 2),
            })
        return pd.DataFrame(rows)

    df_ad = build_ad(str(last_date), num_days)

    if df_ad.empty:
        st.warning("Not enough history yet — check back after more data loads.")
        st.stop()

    total = len(df_ad)
    adv   = int((df_ad["Day Chg%"] > 0).sum())
    dec   = int((df_ad["Day Chg%"] < 0).sum())
    unch  = total - adv - dec
    a4    = int((df_ad[">4EMA"]   == "✅").sum())
    a10   = int((df_ad[">10EMA"]  == "✅").sum())
    a20   = int((df_ad[">20EMA"]  == "✅").sum())
    a50   = int((df_ad[">50EMA"]  == "✅").sum())
    a100  = int((df_ad[">100EMA"] == "✅").sum())
    at52h   = int((df_ad["vs 52WH%"] >= 0).sum())
    near52h = int((df_ad["vs 52WH%"] >= -5).sum())
    at52l   = int((df_ad["vs 52WL%"] <= 5).sum())
    near52l = int((df_ad["vs 52WL%"] <= 10).sum())

    st.markdown("#### Today's Breadth")
    c = st.columns(4)
    c[0].markdown(mcard(adv,   "Advancing",     "g"), unsafe_allow_html=True)
    c[1].markdown(mcard(dec,   "Declining",     "r"), unsafe_allow_html=True)
    c[2].markdown(mcard(unch,  "Unchanged",     "w"), unsafe_allow_html=True)
    c[3].markdown(mcard(total, "Total Tracked", "w"), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Stocks Above EMA")
    c = st.columns(5)
    for col, ab, lbl in zip(
        c,
        [a4,    a10,    a20,    a50,    a100],
        ["4 EMA","10 EMA","20 EMA","50 EMA","100 EMA"],
    ):
        pct = round(ab / total * 100, 1) if total else 0
        clr = "g" if ab >= total / 2 else "r"
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="num {clr}">{ab}'
            f'<span style="font-size:.85rem;color:#475569"> /{total}</span></div>'
            f'<div class="lbl">{lbl} · {pct}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("#### 52-Week Extremes")
    c = st.columns(4)
    c[0].markdown(mcard(at52h,   "At / Above 52W High",  "g"), unsafe_allow_html=True)
    c[1].markdown(mcard(near52h, "Within 5% of 52W High","g"), unsafe_allow_html=True)
    c[2].markdown(mcard(at52l,   "Within 5% of 52W Low", "r"), unsafe_allow_html=True)
    c[3].markdown(mcard(near52l, "Within 10% of 52W Low","r"), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Stock Detail")

    skip = ["Symbol",">4EMA",">10EMA",">20EMA",">50EMA",">100EMA"]
    fmt  = {c: "{:.2f}" for c in df_ad.columns if c not in skip}
    pcts = ["Day Chg%","vs 52WH%","vs 52WL%"]
    s    = df_ad.style.format(fmt, na_rep="—")
    fn   = s.map if hasattr(s, "map") else s.applymap
    s    = fn(lambda v: cell_color(v, 10),
               subset=[c for c in pcts if c in df_ad.columns])
    st.dataframe(s, use_container_width=True, height=580)
    st.caption("✅ above EMA  ·  ❌ below EMA  ·  NSE official EOD data, no live feed")
