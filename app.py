"""
NSE EOD Tracker – v3
=====================
Three tabs:
  1. Index Dashboard  – broad + sectoral index returns and EMAs
  2. Sectoral         – click a sector → see all constituent stocks
  3. Compare          – add any mix of indices and stocks, compare side-by-side

Data (zero live API calls):
  data/stocks/YYYY-MM-DD.csv  – stock EQ bhavcopy
  data/index/YYYY-MM-DD.csv   – NSE index closing values
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="NSE EOD Tracker v4", layout="wide", page_icon="📈")
st.markdown("""
<style>
  .block-container{padding-top:.5rem;padding-bottom:.5rem}
  .stTabs [data-baseweb="tab"]{font-size:15px;font-weight:500;padding:8px 20px}
  .sector-btn{
    display:inline-block;padding:8px 14px;margin:4px;border-radius:8px;
    background:var(--surface-1);border:1px solid var(--border);
    cursor:pointer;font-size:13px;font-weight:500;color:var(--text-primary);
    text-align:center;
  }
  .sector-btn:hover{background:var(--text-accent);color:#fff}
  h2{font-size:1.2rem!important} h3{font-size:1rem!important}
</style>
""", unsafe_allow_html=True)

STOCK_DIR = Path("data")      # existing CSVs are directly in data/
INDEX_DIR = Path("data/index") # new index CSVs go here

# ── BROAD INDICES (Tab 1) in user-requested order ─────────────────────────────
BROAD_INDICES = [
    "Nifty 50", "Nifty Next 50", "Nifty 100", "Nifty 200",
    "Nifty 500", "Nifty Total Market",
    "Nifty Midcap 50", "Nifty Midcap 100",
    "Nifty Smallcap 50", "Nifty Smallcap 100",
]

# ── SECTORAL INDICES with constituents ────────────────────────────────────────
SECTORS = {
    "Nifty Bank": {
        "idx": "Nifty Bank",
        "stocks": ["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK","PNB",
                   "INDUSINDBK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","AUBANK","BANKBARODA"],
    },
    "Nifty PSU Bank": {
        "idx": "Nifty PSU Bank",
        "stocks": ["SBIN","PNB","BANKBARODA","CANARABANK","UNIONBANK","BANKINDIA",
                   "CENTRALBK","UCOBANK","MAHABANK","INDIANB","IOB"],
    },
    "Nifty Private Bank": {
        "idx": "Nifty Private Bank",
        "stocks": ["HDFCBANK","ICICIBANK","KOTAKBANK","AXISBANK","INDUSINDBK",
                   "BANDHANBNK","FEDERALBNK","IDFCFIRSTB","AUBANK","RBLBANK"],
    },
    "Nifty Financial Services": {
        "idx": "Nifty Financial Services",
        "stocks": ["HDFCBANK","ICICIBANK","BAJFINANCE","KOTAKBANK","AXISBANK","SBIN",
                   "BAJAJFINSV","HDFCAMC","MUTHOOTFIN","CHOLAFIN","M&MFIN",
                   "SHRIRAMFIN","JIOFINSERV","HDFCLIFE","SBILIFE"],
    },
    "Nifty Housing Finance": {
        "idx": "Nifty Housing Finance",
        "stocks": ["LICHSGFIN","PNBHOUSING","AAVAS","CANFINHOME","HOMEFIRST",
                   "APTUS","REPCO","INDIABULL"],
    },
    "Nifty NBFC": {
        "idx": "Nifty NBFC",
        "stocks": ["BAJFINANCE","BAJAJFINSV","MUTHOOTFIN","CHOLAFIN","M&MFIN",
                   "SHRIRAMFIN","JIOFINSERV","MANAPPURAM","SUNDARMFIN","L&TFH"],
    },
    "Nifty Insurance": {
        "idx": "Nifty Insurance",
        "stocks": ["HDFCLIFE","SBILIFE","ICICIGI","LICI","MAXLIFE",
                   "STARHEALTH","GICRE","NIACL"],
    },
    "Nifty Energy": {
        "idx": "Nifty Energy",
        "stocks": ["RELIANCE","ONGC","NTPC","POWERGRID","BPCL","IOC","GAIL",
                   "TATAPOWER","ADANIGREEN","ADANIPOWER"],
    },
    "Nifty Oil & Gas": {
        "idx": "Nifty Oil and Gas",
        "stocks": ["RELIANCE","ONGC","BPCL","IOC","GAIL","HINDPETRO","MGL","IGL",
                   "PETRONET","GSPL","OIL","MRPL","GUJGASLTD"],
    },
    "Nifty Power": {
        "idx": "Nifty Power",
        "stocks": ["NTPC","POWERGRID","TATAPOWER","ADANIPOWER","ADANIGREEN",
                   "CESC","JSWENERGY","TORNTPOWER","NHPC","SJVN",
                   "INOXWIND","GREENKO"],
    },
    "Nifty Auto": {
        "idx": "Nifty Auto",
        "stocks": ["MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT",
                   "BOSCHLTD","BHARATFORG","ASHOKLEY","TVSMOTORS","MOTHERSON",
                   "UNOMINDA","TIINDIA","SONACOMS","EXIDEIND"],
    },
    "Nifty FMCG": {
        "idx": "Nifty FMCG",
        "stocks": ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO",
                   "COLPAL","GODREJCP","EMAMILTD","TATACONSUM","UBL","MCDOWELL-N",
                   "RADICO","VBL","BIKAJI"],
    },
    "Nifty IT": {
        "idx": "Nifty IT",
        "stocks": ["TCS","INFY","HCLTECH","WIPRO","TECHM","LTIM",
                   "PERSISTENT","MPHASIS","COFORGE","OFSS"],
    },
    "Nifty Metal": {
        "idx": "Nifty Metal",
        "stocks": ["TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","VEDL","SAIL",
                   "NMDC","APLAPOLLO","NATIONALUM","HINDCOPPER","MOIL","WELCORP",
                   "RATNAMANI","JINDALSAW"],
    },
    "Nifty Pharma": {
        "idx": "Nifty Pharma",
        "stocks": ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP","TORNTPHARM",
                   "ALKEM","AUROPHARMA","LUPIN","BIOCON"],
    },
    "Nifty Healthcare": {
        "idx": "Nifty Healthcare Index",
        "stocks": ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP","TORNTPHARM",
                   "ALKEM","AUROPHARMA","LUPIN","BIOCON","MAXHEALTH","FORTIS",
                   "LALPATHLAB","METROPOLIS","ZYDUSLIFE"],
    },
    "Nifty Hospital": {
        "idx": "Nifty Healthcare Index",
        "stocks": ["APOLLOHOSP","MAXHEALTH","FORTIS","MEDANTA","NH",
                   "KIMS","RAINBOW","YATHARTH"],
    },
    "Nifty Realty": {
        "idx": "Nifty Realty",
        "stocks": ["DLF","GODREJPROP","OBEROIRLTY","PHOENIXLTD","PRESTIGE",
                   "BRIGADE","SOBHA","SUNTECK","KOLTEPATIL","MAHLIFE"],
    },
    "Nifty Cement": {
        "idx": "Nifty Cement",
        "stocks": ["ULTRACEMCO","SHREECEM","AMBUJACEM","ACC","JKCEMENT",
                   "RAMCOCEM","HEIDELBERGCEMENT","BIRLACORPN","PRISMJOINTS","NUVOCO"],
    },
    "Nifty Construction": {
        "idx": "Nifty Infrastructure",
        "stocks": ["LT","ADANIPORTS","NBCC","IRB","KNRCON","PNCINFRA",
                   "ASHOKA","HG INFRA","GPPL","CAPACITE"],
    },
    "Nifty Media": {
        "idx": "Nifty Media",
        "stocks": ["SUNTV","ZEEL","PVRINOX","NAZARA","NXTDIGITAL",
                   "SAREGAMA","TIPS","BALAJITELE"],
    },
    "Nifty Capital Goods": {
        "idx": "Nifty India Manufacturing",
        "stocks": ["LT","SIEMENS","ABB","BHEL","BEL","HAL","CUMMINSIND",
                   "THERMAX","VOLTAS","HAVELLS","POLYCAB","KEI"],
    },
    "Nifty Consumer Durables": {
        "idx": "Nifty Consumer Durables",
        "stocks": ["TITAN","VOLTAS","HAVELLS","WHIRLPOOL","BLUESTAR","CROMPTON",
                   "VGUARD","DIXON","AMBER","RAJESHEXPO","KAJARIACER","POLYCAB"],
    },
    "Nifty Retail": {
        "idx": "Nifty India Consumption",
        "stocks": ["DMART","TRENT","ABFRL","NYKAA","ETAIL","JUBLFOOD",
                   "DEVYANI","SAPPHIRE","BARBEQUE","WESTLIFE"],
    },
    "Nifty Telecommunication": {
        "idx": "Nifty FMCG",
        "stocks": ["BHARTIARTL","IDEA","TATACOMM","INDIAMART","RAILTEL",
                   "HFCL","STLTECH","TTML"],
    },
    "Nifty Capital Markets": {
        "idx": "Nifty Capital Markets",
        "stocks": ["BSE","MCX","CAMS","CDSL","KFINTECH","ANGELONE",
                   "NUVAMA","IIFL","MOTILALOFS","5PAISA"],
    },
    "Nifty Commodities": {
        "idx": "Nifty Commodities",
        "stocks": ["RELIANCE","ONGC","COALINDIA","VEDL","HINDALCO","NMDC",
                   "SAIL","TATASTEEL","JSWSTEEL","NATIONALUM"],
    },
    "Nifty Defence": {
        "idx": "Nifty India Defence",
        "stocks": ["HAL","BEL","BHEL","BEML","COCHINSHIP","GRSE",
                   "MAZAGON","PARAS","MTAR","DATAPATTNS"],
    },
    "Nifty Commercial & Transport": {
        "idx": "Nifty Transportation & Logistics",
        "stocks": ["DELHIVERY","BLUEDART","GATI","VRL","TCI",
                   "MAHINDRALOG","CONCOR","GATEWAY","ALLCARGO","AEGISLOG"],
    },
    "Nifty India Digital": {
        "idx": "Nifty India Digital",
        "stocks": ["INFY","TCS","WIPRO","HCLTECH","TECHM","ETERNAL","NYKAA",
                   "DELHIVERY","INDIAMART","JUSTDIAL","POLICYBZR","PAYTM"],
    },
    "Nifty India Manufacturing": {
        "idx": "Nifty India Manufacturing",
        "stocks": ["RELIANCE","LT","MARUTI","TATAMOTORS","SUNPHARMA","TATASTEEL",
                   "ULTRACEMCO","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT",
                   "MOTHERSON","BOSCHLTD","SIEMENS","ABB","CUMMINSIND"],
    },
    "Nifty India Tourism": {
        "idx": "Nifty India Tourism",
        "stocks": ["INDHOTEL","LEMONTREE","CHALET","MAHINDRAHOLIDAY",
                   "THOMASCOOK","COX&KINGS","IRCTC","EASEMYTRIP"],
    },
    "Nifty Transport & Logistics": {
        "idx": "Nifty Transportation & Logistics",
        "stocks": ["ADANIPORTS","CONCOR","BLUEDART","DELHIVERY","VRL",
                   "TCI","MAHINDRALOG","GATEWAY","ALLCARGO","GATI"],
    },
    "Nifty India Railways PSU": {
        "idx": "Nifty India Railways PSU Index",
        "stocks": ["RVNL","IRFC","IRCON","RAILTEL","RITES","IRCTC",
                   "BEML","RVNL","NTPC","NBCC"],
    },
}

# All index names for Compare tab
ALL_INDEX_NAMES = BROAD_INDICES + [s["idx"] for s in SECTORS.values()]
ALL_INDEX_NAMES = list(dict.fromkeys(ALL_INDEX_NAMES))


# ── COLOUR FUNCTION ───────────────────────────────────────────────────────────
def cell_bg(val, cap=20):
    try:
        v = float(val)
    except Exception:
        return ""
    if pd.isna(v):
        return ""
    i = min(abs(v) / cap, 1.0)
    if v >= 0:
        r, g, b = int(255 - i*195), int(255 - i*55), int(255 - i*195)
    else:
        r, g, b = int(255 - i*35), int(255 - i*205), int(255 - i*205)
    return f"background-color:rgb({r},{g},{b});color:#000;font-weight:600;"

def style_table(df, pct_cols, cap=20):
    cols = [c for c in pct_cols if c in df.columns]
    num  = [c for c in df.columns if c not in ("Name",)]
    fmt  = {c: "{:.2f}" for c in num}
    s    = df.style.format(fmt, na_rep="—")
    fn   = s.map if hasattr(s, "map") else s.applymap
    return fn(lambda v: cell_bg(v, cap), subset=cols)

RET_COLS = ["1D %","1W %","2W %","1M %","2M %","3M %","6M %","1Y %"]
EMA_COLS = ["4 EMA","10 EMA","20 EMA","50 EMA","100 EMA"]
PCT_COLS = RET_COLS


# ── DATA LOADING ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def load_stock_history():
    import re; date_pat = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    files = sorted(f for f in STOCK_DIR.glob("*.csv") if date_pat.match(f.stem))
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, low_memory=False)
            df.columns = df.columns.str.strip()
            # Handle all NSE bhavcopy column name variants
            df = df.rename(columns={
                "SYMBOL":    "TckrSymb",
                "SERIES":    "SctySrs",
                "HIGH":      "HghPric",
                "LOW":       "LwPric",
                "CLOSE":     "ClsPric",
                "PREVCLOSE": "PrvsClsgPric",
                "OPEN":      "OpnPric",
                # Some old files use these names
                "Symbol":    "TckrSymb",
                "Series":    "SctySrs",
                "High":      "HghPric",
                "Low":       "LwPric",
                "Close":     "ClsPric",
                "Prev Close":"PrvsClsgPric",
            })
            if "TradDt" not in df.columns:
                df["TradDt"] = f.stem
            # Ensure price columns are numeric
            for c in ["ClsPric","HghPric","LwPric","PrvsClsgPric"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
                else:
                    df[c] = np.nan
            dfs.append(df[["TradDt","TckrSymb","SctySrs","ClsPric","HghPric","LwPric","PrvsClsgPric"]])
        except Exception:
            continue
    if not dfs:
        return pd.DataFrame()
    hist = pd.concat(dfs, ignore_index=True)
    if "SctySrs" in hist.columns:
        hist = hist[hist["SctySrs"].astype(str).str.strip() == "EQ"]
    hist["TradDt"]   = pd.to_datetime(hist["TradDt"], errors="coerce")
    hist["TckrSymb"] = hist["TckrSymb"].astype(str).str.strip().str.upper()
    for c in ["ClsPric","HghPric","LwPric","PrvsClsgPric"]:
        if c in hist.columns:
            hist[c] = pd.to_numeric(hist[c], errors="coerce")
    return hist.dropna(subset=["TradDt","TckrSymb","ClsPric"]).sort_values("TradDt").reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=3600)
def load_index_history():
    files = sorted(INDEX_DIR.glob("*.csv"))
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, low_memory=False)
            df.columns = df.columns.str.strip()
            # Handle both column name formats NSE has used over the years
            df = df.rename(columns={
                "Index Name":          "TckrSymb",
                "Closing Index Value": "ClsPric",
                "Closing":             "ClsPric",
            })
            if "TckrSymb" not in df.columns or "ClsPric" not in df.columns:
                continue
            df["TradDt"]   = f.stem
            df["ClsPric"]  = pd.to_numeric(df["ClsPric"], errors="coerce")
            df["TckrSymb"] = df["TckrSymb"].astype(str).str.strip()
            df = df.dropna(subset=["ClsPric"])
            dfs.append(df[["TradDt","TckrSymb","ClsPric"]])
        except Exception:
            continue
    if not dfs:
        return pd.DataFrame()
    hist = pd.concat(dfs, ignore_index=True)
    hist["TradDt"]   = pd.to_datetime(hist["TradDt"], errors="coerce")
    hist["TckrSymb"] = hist["TckrSymb"].astype(str).str.strip()
    hist["ClsPric"]  = pd.to_numeric(hist["ClsPric"], errors="coerce")
    return hist.dropna(subset=["TradDt","TckrSymb","ClsPric"]).sort_values("TradDt").reset_index(drop=True)


# ── METRIC CALCULATION ────────────────────────────────────────────────────────
def calc(hist, sym, label=None):
    df = hist[hist["TckrSymb"] == sym].sort_values("TradDt")
    if len(df) < 5:
        return None
    close = df["ClsPric"].astype(float).values
    ltp   = float(close[-1])
    prev  = (float(df["PrvsClsgPric"].iloc[-1])
             if "PrvsClsgPric" in df.columns and not pd.isna(df["PrvsClsgPric"].iloc[-1])
             else float(close[-2]))
    cs = pd.Series(close)

    # Date-based return: find exact trading day n days before last date
    # This is accurate even when some holiday dates are missing from data
    last_dt = df["TradDt"].iloc[-1]
    dates   = df["TradDt"].values  # sorted ascending

    def ret(n):
        """Return n trading-days ago using actual dates, not row index."""
        target = last_dt - pd.Timedelta(days=int(n * 365.25 / 252) + n)
        # Find the closest available date on or before target
        mask = dates <= target
        if not mask.any():
            return np.nan
        idx_pos = int(np.where(mask)[0][-1])
        p = float(close[idx_pos])
        return round(((ltp - p) / p) * 100, 2) if p else np.nan

    def ema(span):
        return round(float(cs.ewm(span=span, adjust=False).mean().iloc[-1]), 2)

    has_hl = "HghPric" in df.columns and "LwPric" in df.columns
    h52 = round(float(df["HghPric"].astype(float).max()), 2) if has_hl else np.nan
    l52 = round(float(df["LwPric"].astype(float).min()),  2) if has_hl else np.nan

    return {
        "Name":      label or sym,
        "LTP":       round(ltp, 2),
        "1D %":      round(((ltp-prev)/prev)*100, 2) if prev else np.nan,
        "1W %":      ret(5),
        "2W %":      ret(10),
        "1M %":      ret(21),
        "2M %":      ret(42),
        "3M %":      ret(63),
        "6M %":      ret(126),
        "1Y %":      ret(251),
        "4 EMA":     ema(4),
        "10 EMA":    ema(10),
        "20 EMA":    ema(20),
        "50 EMA":    ema(50),
        "100 EMA":   ema(100),
        "52W High":  h52,
        "vs 52WH%":  round(((ltp-h52)/h52)*100, 2) if not np.isnan(h52) else np.nan,
        "52W Low":   l52,
        "vs 52WL%":  round(((ltp-l52)/l52)*100, 2) if not np.isnan(l52) else np.nan,
    }


def build_rows(hist, symbols, labels=None):
    rows = []
    for i, sym in enumerate(symbols):
        lbl = labels[i] if labels else None
        r   = calc(hist, sym, lbl)
        if r:
            rows.append(r)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ── SHOW TABLE ────────────────────────────────────────────────────────────────
ALL_PCT = RET_COLS + ["vs 52WH%","vs 52WL%"]

def show_table(df, cap=20):
    if df.empty:
        st.info("No data available.")
        return
    cols_order = ["Name","LTP"] + RET_COLS + EMA_COLS + ["52W High","vs 52WH%","52W Low","vs 52WL%"]
    cols_show  = [c for c in cols_order if c in df.columns]
    st.dataframe(style_table(df[cols_show], ALL_PCT, cap),
                 width='stretch', height=min(600, 60 + len(df)*38))


# ── LOAD DATA ─────────────────────────────────────────────────────────────────
# session state for navigation
if "sector_view" not in st.session_state:
    st.session_state.sector_view = None
if "compare_indices" not in st.session_state:
    st.session_state.compare_indices = []
if "compare_stocks" not in st.session_state:
    st.session_state.compare_stocks = []

# ── LOAD DATA WITH FULL ERROR VISIBILITY ─────────────────────────────────────
try:
    with st.spinner("Loading EOD data…"):
        sh = load_stock_history()
        ih = load_index_history()
    has_stocks = not sh.empty
    has_index  = not ih.empty
    last_date  = sh["TradDt"].max().date() if has_stocks else None
    all_syms   = sorted(sh["TckrSymb"].unique()) if has_stocks else []
except Exception as _load_err:
    st.error(f"❌ Data loading error: {_load_err}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

from pathlib import Path as _P
_stock_files = list(_P("data").glob("*.csv"))
_index_files = list(_P("data/index").glob("*.csv")) if _P("data/index").exists() else []

if not has_stocks and not has_index:
    st.title("📈 NSE EOD Tracker")
    st.info("⏳ **Data not yet loaded.** GitHub Actions is downloading NSE data. Refreshing every 30 seconds...")
    st.markdown(f"**data/ folder:** {len(_stock_files)} files found")
    st.markdown(f"**data/index/ folder:** {len(_index_files)} files found")
    st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)
    st.stop()

st.sidebar.title("📈 NSE Tracker")
if last_date:
    st.sidebar.markdown(f"📅 **Last EOD:** `{last_date}`")
    st.sidebar.markdown(f"🏷️ **Stocks:** {len(all_syms)}")
    idx_count = ih["TckrSymb"].nunique() if has_index else 0
    if idx_count:
        st.sidebar.markdown(f"📊 **Indices:** {idx_count}")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Index Dashboard", "🏭 Sectoral", "⚖️ Compare"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 – INDEX DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("📊 Index Dashboard")

    if not has_index:
        st.warning(
            "⏳ Index data not yet downloaded. "
            "Go to your GitHub repo → Actions tab → Run workflow manually. "
            "After it completes, reboot this app."
        )
    else:
        # ── Broad Indices ──────────────────────────────────────────────────────
        st.subheader("Broad Market Indices")
        broad_rows = []
        for idx_name in BROAD_INDICES:
            r = calc(ih, idx_name, idx_name)
            if r:
                broad_rows.append(r)
        if broad_rows:
            show_table(pd.DataFrame(broad_rows))
        else:
            st.info("Broad index names not matched yet — data may still be loading.")

        st.markdown("---")

        # ── Sectoral Indices ───────────────────────────────────────────────────
        st.subheader("Sectoral Indices")

        # Exact NSE index names as they appear in ind_close_all file
        SECTOR_NSE_NAME = {
            "Nifty Bank":                    "Nifty Bank",
            "Nifty PSU Bank":                "Nifty PSU Bank",
            "Nifty Private Bank":            "Nifty Private Bank",
            "Nifty Financial Services":      "Nifty Financial Services",
            "Nifty Housing Finance":         "Nifty Housing Finance",
            "Nifty NBFC":                    "Nifty Non-Cyclical Consumer",
            "Nifty Insurance":               "Nifty India Insurance",
            "Nifty Energy":                  "Nifty Energy",
            "Nifty Oil & Gas":               "Nifty Oil and Gas",
            "Nifty Power":                   "Nifty Power",
            "Nifty Auto":                    "Nifty Auto",
            "Nifty FMCG":                    "Nifty FMCG",
            "Nifty IT":                      "Nifty IT",
            "Nifty Metal":                   "Nifty Metal",
            "Nifty Pharma":                  "Nifty Pharma",
            "Nifty Healthcare":              "Nifty Healthcare Index",
            "Nifty Hospital":                "Nifty Healthcare Index",
            "Nifty Realty":                  "Nifty Realty",
            "Nifty Cement":                  "Nifty Infrastructure",
            "Nifty Construction":            "Nifty Infrastructure",
            "Nifty Media":                   "Nifty Media",
            "Nifty Capital Goods":           "Nifty India Manufacturing",
            "Nifty Consumer Durables":       "Nifty Consumer Durables",
            "Nifty Retail":                  "Nifty India Consumption",
            "Nifty Telecommunication":       "Nifty Communication Services",
            "Nifty Capital Markets":         "Nifty Capital Markets",
            "Nifty Commodities":             "Nifty Commodities",
            "Nifty Defence":                 "Nifty India Defence",
            "Nifty Commercial & Transport":  "Nifty India Transportation and Logistics",
            "Nifty India Digital":           "Nifty India Digital",
            "Nifty India Manufacturing":     "Nifty India Manufacturing",
            "Nifty India Tourism":           "Nifty India Tourism",
            "Nifty Transport & Logistics":   "Nifty India Transportation and Logistics",
            "Nifty India Railways PSU":      "Nifty India Railways PSU Index",
        }

        sectoral_rows = []
        for sec_label in SECTORS.keys():
            nse_name = SECTOR_NSE_NAME.get(sec_label, sec_label)
            r = calc(ih, nse_name, sec_label)
            if r:
                sectoral_rows.append(r)

        if sectoral_rows:
            show_table(pd.DataFrame(sectoral_rows))
        else:
            st.info("Sectoral index data not matched yet.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 – SECTORAL (click sector → see stocks)
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    # Back button
    if st.session_state.sector_view:
        if st.button("← Back to all sectors"):
            st.session_state.sector_view = None
            st.rerun()

    if st.session_state.sector_view is None:
        # Show all sectors as a grid of buttons
        st.header("🏭 Sectoral Index")
        st.caption("Click any sector to see all constituent stocks with returns and EMAs")

        sector_names = list(SECTORS.keys())
        cols_per_row = 4
        for row_start in range(0, len(sector_names), cols_per_row):
            row_sectors = sector_names[row_start:row_start + cols_per_row]
            cols = st.columns(len(row_sectors))
            for col, sec in zip(cols, row_sectors):
                with col:
                    if st.button(sec, key=f"sec_{sec}", width='stretch'):
                        st.session_state.sector_view = sec
                        st.rerun()
    else:
        # Show stocks in selected sector
        sec      = st.session_state.sector_view
        sec_data = SECTORS[sec]
        stocks   = sec_data["stocks"]
        idx_name = sec_data["idx"]

        st.header(f"🏭 {sec}")

        # Index row at top
        if has_index:
            idx_row = calc(ih, idx_name, f"▶ {sec} INDEX")
            if idx_row:
                st.subheader("Index")
                show_table(pd.DataFrame([idx_row]))

        st.subheader("Constituent Stocks")
        if not has_stocks:
            st.warning("Stock data not yet available.")
        else:
            available = [s for s in stocks if s in all_syms]
            missing   = [s for s in stocks if s not in all_syms]
            if missing:
                st.caption(f"ℹ️ Not in data yet: {', '.join(missing)}")
            if available:
                df_stocks = build_rows(sh, available)
                # Add sector avg row
                if not df_stocks.empty:
                    num_cols = [c for c in df_stocks.columns if c != "Name"]
                    avg_row  = {"Name": f"📊 {sec} AVG"}
                    avg_row.update(df_stocks[num_cols].mean(numeric_only=True).round(2).to_dict())
                    df_display = pd.concat([pd.DataFrame([avg_row]), df_stocks], ignore_index=True)
                    show_table(df_display)
            else:
                st.warning("None of these stocks found in data.")



# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 – COMPARE
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:

    # ── Init session state ────────────────────────────────────────────────────
    for _k, _v in [("cmp_stocks",[]), ("cmp_indices",[]), ("cmp_view",None)]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # ── DETAIL PAGE (index or stock drilldown) ────────────────────────────────
    if st.session_state.cmp_view is not None:
        view_type, view_name = st.session_state.cmp_view

        if st.button("← Back to Compare", key="cmp_back"):
            st.session_state.cmp_view = None
            st.rerun()

        _SECTOR_IDX_MAP = {
            "Nifty Bank":"Nifty Bank","Nifty PSU Bank":"Nifty PSU Bank",
            "Nifty Private Bank":"Nifty Private Bank",
            "Nifty Financial Services":"Nifty Financial Services",
            "Nifty Auto":"Nifty Auto","Nifty FMCG":"Nifty FMCG",
            "Nifty IT":"Nifty IT","Nifty Metal":"Nifty Metal",
            "Nifty Pharma":"Nifty Pharma","Nifty Realty":"Nifty Realty",
            "Nifty Energy":"Nifty Energy","Nifty Healthcare":"Nifty Healthcare Index",
            "Nifty Media":"Nifty Media","Nifty Defence":"Nifty India Defence",
            "Nifty Consumer Durables":"Nifty Consumer Durables",
            "Nifty Capital Markets":"Nifty Capital Markets",
            "Nifty Commodities":"Nifty Commodities",
            "Nifty 50":"Nifty 50","Nifty Next 50":"Nifty Next 50",
            "Nifty 100":"Nifty 100","Nifty 200":"Nifty 200",
            "Nifty 500":"Nifty 500","Nifty Total Market":"Nifty Total Market",
            "Nifty Midcap 50":"Nifty Midcap 50","Nifty Midcap 100":"Nifty Midcap 100",
            "Nifty Smallcap 50":"Nifty Smallcap 50","Nifty Smallcap 100":"Nifty Smallcap 100",
            "Nifty Oil & Gas":"Nifty Oil and Gas","Nifty Power":"Nifty Power",
            "Nifty Housing Finance":"Nifty Housing Finance",
            "Nifty India Manufacturing":"Nifty India Manufacturing",
            "Nifty India Digital":"Nifty India Digital",
            "Nifty India Tourism":"Nifty India Tourism",
            "Nifty Transport & Logistics":"Nifty India Transportation and Logistics",
            "Nifty India Railways PSU":"Nifty India Railways PSU Index",
        }

        if view_type == "index":
            st.header(f"📊 {view_name}")
            # Index row
            if has_index:
                nse_nm = _SECTOR_IDX_MAP.get(view_name, view_name)
                ir = calc(ih, nse_nm, f"▶ {view_name} INDEX")
                if ir:
                    st.subheader("Index Value")
                    show_table(pd.DataFrame([ir]))
            # Constituent stocks
            sec = SECTORS.get(view_name)
            if sec and has_stocks:
                avail = [s for s in sec["stocks"] if s in all_syms]
                miss  = [s for s in sec["stocks"] if s not in all_syms]
                if miss:
                    st.caption(f"ℹ️ Not in data: {', '.join(miss)}")
                if avail:
                    st.subheader("Constituent Stocks")
                    df_cs = build_rows(sh, avail)
                    if not df_cs.empty:
                        nc = [c for c in df_cs.columns if c != "Name"]
                        ar = {"Name": f"📊 {view_name} AVG"}
                        ar.update(df_cs[nc].mean(numeric_only=True).round(2).to_dict())
                        show_table(pd.concat([pd.DataFrame([ar]), df_cs], ignore_index=True))
            elif not sec:
                st.info("Constituent stock list not available for broad indices.")

        elif view_type == "stock":
            st.header(f"🏷️ {view_name}")
            if has_stocks:
                r = calc(sh, view_name, view_name)
                if r:
                    show_table(pd.DataFrame([r]))
                else:
                    st.warning(f"{view_name} not found in data.")

    # ── MAIN COMPARE PAGE ────────────────────────────────────────────────────
    else:
        st.header("⚖️ Compare")
        st.caption("Type index or stock names on the left — results appear on the right.")

        left, right = st.columns([1, 2], gap="large")

        with left:
            # Index input
            st.markdown("#### 📊 Indices")
            idx_inp = st.text_input("Index name", key="cmp_idx_inp",
                                    placeholder="e.g. Nifty Bank",
                                    label_visibility="collapsed")
            if idx_inp:
                hits = [n for n in ALL_INDEX_NAMES if idx_inp.lower() in n.lower()][:5]
                for h in hits:
                    if st.button(h, key=f"isug_{h}"):
                        if h not in st.session_state.cmp_indices:
                            st.session_state.cmp_indices.append(h)
                        st.rerun()

            ca, cb = st.columns(2)
            with ca:
                if st.button("➕ Add", key="add_idx") and idx_inp:
                    hits = [n for n in ALL_INDEX_NAMES if idx_inp.lower() in n.lower()]
                    if hits and hits[0] not in st.session_state.cmp_indices:
                        st.session_state.cmp_indices.append(hits[0])
                        st.rerun()
                    elif not hits:
                        st.warning(f"No match for '{idx_inp}'")
            with cb:
                if st.button("🗑 Clear", key="clr_idx"):
                    st.session_state.cmp_indices = []
                    st.rerun()

            if st.session_state.cmp_indices:
                for i, n in enumerate(st.session_state.cmp_indices):
                    c1, c2 = st.columns([5,1])
                    c1.markdown(f"• **{n}**")
                    if c2.button("✕", key=f"ri_{i}"):
                        st.session_state.cmp_indices.pop(i); st.rerun()

            st.markdown("---")

            # Stock input
            st.markdown("#### 🏷️ Stocks")
            stk_inp = st.text_input("Stock symbol", key="cmp_stk_inp",
                                    placeholder="e.g. RELIANCE or RIL,TCS",
                                    label_visibility="collapsed").upper().strip()
            if stk_inp and has_stocks:
                hits = [s for s in all_syms if stk_inp in s][:5]
                for h in hits:
                    if st.button(h, key=f"ssug_{h}"):
                        if h not in st.session_state.cmp_stocks:
                            st.session_state.cmp_stocks.append(h)
                        st.rerun()

            ca2, cb2 = st.columns(2)
            with ca2:
                if st.button("➕ Add", key="add_stk") and stk_inp:
                    for s in [x.strip() for x in stk_inp.split(",") if x.strip()]:
                        if s not in st.session_state.cmp_stocks:
                            st.session_state.cmp_stocks.append(s)
                    st.rerun()
            with cb2:
                if st.button("🗑 Clear", key="clr_stk"):
                    st.session_state.cmp_stocks = []
                    st.rerun()

            if st.session_state.cmp_stocks:
                for i, s in enumerate(st.session_state.cmp_stocks):
                    c1, c2 = st.columns([5,1])
                    c1.markdown(f"• **{s}**")
                    if c2.button("✕", key=f"rs_{i}"):
                        st.session_state.cmp_stocks.pop(i); st.rerun()

        # ── RIGHT: RESULTS ────────────────────────────────────────────────────
        with right:
            _SECTOR_IDX_MAP2 = {
                "Nifty Bank":"Nifty Bank","Nifty PSU Bank":"Nifty PSU Bank",
                "Nifty Private Bank":"Nifty Private Bank",
                "Nifty Financial Services":"Nifty Financial Services",
                "Nifty Auto":"Nifty Auto","Nifty FMCG":"Nifty FMCG",
                "Nifty IT":"Nifty IT","Nifty Metal":"Nifty Metal",
                "Nifty Pharma":"Nifty Pharma","Nifty Realty":"Nifty Realty",
                "Nifty Energy":"Nifty Energy","Nifty Healthcare":"Nifty Healthcare Index",
                "Nifty Media":"Nifty Media","Nifty Defence":"Nifty India Defence",
                "Nifty Consumer Durables":"Nifty Consumer Durables",
                "Nifty Capital Markets":"Nifty Capital Markets",
                "Nifty Commodities":"Nifty Commodities",
                "Nifty 50":"Nifty 50","Nifty Next 50":"Nifty Next 50",
                "Nifty 100":"Nifty 100","Nifty 200":"Nifty 200",
                "Nifty 500":"Nifty 500","Nifty Total Market":"Nifty Total Market",
                "Nifty Midcap 50":"Nifty Midcap 50","Nifty Midcap 100":"Nifty Midcap 100",
                "Nifty Smallcap 50":"Nifty Smallcap 50","Nifty Smallcap 100":"Nifty Smallcap 100",
                "Nifty Oil & Gas":"Nifty Oil and Gas","Nifty Power":"Nifty Power",
                "Nifty Housing Finance":"Nifty Housing Finance",
                "Nifty India Manufacturing":"Nifty India Manufacturing",
                "Nifty India Digital":"Nifty India Digital",
            }

            if not st.session_state.cmp_indices and not st.session_state.cmp_stocks:
                st.info("Add indices or stocks on the left to compare.")
            else:
                # Indices table
                if st.session_state.cmp_indices:
                    st.markdown("#### 📊 Indices")
                    irows = []
                    for name in st.session_state.cmp_indices:
                        nse = _SECTOR_IDX_MAP2.get(name, name)
                        r   = calc(ih, nse, name) if has_index else None
                        irows.append(r if r else {"Name": f"{name} (no data)"})
                    show_table(pd.DataFrame(irows))

                    st.markdown("**Drill into index:**")
                    _cols = st.columns(min(4, len(st.session_state.cmp_indices)))
                    for ci, name in enumerate(st.session_state.cmp_indices):
                        with _cols[ci % 4]:
                            if st.button(f"🔍 {name}", key=f"vw_idx_{name}"):
                                st.session_state.cmp_view = ("index", name)
                                st.rerun()

                # Stocks table
                if st.session_state.cmp_stocks:
                    st.markdown("#### 🏷️ Stocks")
                    srows = []
                    for sym in st.session_state.cmp_stocks:
                        r = calc(sh, sym, sym) if has_stocks else None
                        srows.append(r if r else {"Name": f"{sym} (not found)"})
                    show_table(pd.DataFrame(srows))

                    st.markdown("**Drill into stock:**")
                    _scols = st.columns(min(4, len(st.session_state.cmp_stocks)))
                    for si, sym in enumerate(st.session_state.cmp_stocks):
                        with _scols[si % 4]:
                            if st.button(f"🔍 {sym}", key=f"vw_stk_{sym}"):
                                st.session_state.cmp_view = ("stock", sym)
                                st.rerun()

                # Performance chart
                total = len(st.session_state.cmp_indices)+len(st.session_state.cmp_stocks)
                if total >= 2:
                    st.markdown("---")
                    st.markdown("#### 📈 Relative Performance (Rebased to 100)")
                    cd = {}
                    for name in st.session_state.cmp_indices:
                        nse = _SECTOR_IDX_MAP2.get(name, name)
                        if has_index:
                            s = ih[ih["TckrSymb"]==nse].sort_values("TradDt").set_index("TradDt")["ClsPric"].dropna()
                            if not s.empty: cd[name] = s/s.iloc[0]*100
                    for sym in st.session_state.cmp_stocks:
                        if has_stocks:
                            s = sh[sh["TckrSymb"]==sym].sort_values("TradDt").set_index("TradDt")["ClsPric"].dropna()
                            if not s.empty: cd[sym] = s/s.iloc[0]*100
                    if cd:
                        st.line_chart(pd.DataFrame(cd).dropna(how="all"), height=350)
