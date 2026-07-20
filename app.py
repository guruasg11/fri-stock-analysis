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
st.set_page_config(page_title="NSE Tracker", layout="wide", page_icon="📈")
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
        "idx": "Nifty Oil & Gas",
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
        "idx": "Nifty India Healthcare",
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
        "idx": "Nifty Capital Markets Index",
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
            df = df.rename(columns={
                "SYMBOL":"TckrSymb","SERIES":"SctySrs",
                "HIGH":"HghPric","LOW":"LwPric",
                "CLOSE":"ClsPric","PREVCLOSE":"PrvsClsgPric",
            })
            if "TradDt" not in df.columns:
                df["TradDt"] = f.stem
            dfs.append(df)
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
            if "Index Name" not in df.columns:
                continue
            df = df.rename(columns={"Closing": "ClsPric", "Index Name": "TckrSymb"})
            df["TradDt"] = f.stem
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

    def ret(n):
        if len(close) <= n: return np.nan
        p = float(close[-(n+1)])
        return round(((ltp-p)/p)*100, 2) if p else np.nan

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
                 use_container_width=True, height=min(600, 60 + len(df)*38))


# ── LOAD DATA ─────────────────────────────────────────────────────────────────
# session state for navigation
if "sector_view" not in st.session_state:
    st.session_state.sector_view = None
if "compare_indices" not in st.session_state:
    st.session_state.compare_indices = []
if "compare_stocks" not in st.session_state:
    st.session_state.compare_stocks = []

with st.spinner("Loading EOD data…"):
    sh = load_stock_history()   # stock history
    ih = load_index_history()   # index history

# Determine data status
has_stocks = not sh.empty
has_index  = not ih.empty
last_date  = sh["TradDt"].max().date() if has_stocks else None
all_syms   = sorted(sh["TckrSymb"].unique()) if has_stocks else []

if not has_stocks and not has_index:
    st.title("📈 NSE EOD Tracker")
    st.info(
        "⏳ **Data not yet loaded.**\n\n"
        "GitHub Actions is downloading NSE data now. "
        "This takes 5–10 minutes on first deploy. "
        "The page refreshes automatically."
    )
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
        st.warning("Index data not yet available. Check that `data/index/` folder has CSV files.")
    else:
        # ── Broad Indices ──────────────────────────────────────────────────────
        st.subheader("Broad Market Indices")
        broad_rows = []
        for idx_name in BROAD_INDICES:
            r = calc(ih, idx_name, idx_name)
            if r:
                broad_rows.append(r)

        if broad_rows:
            df_broad = pd.DataFrame(broad_rows)
            show_table(df_broad)
        else:
            st.info("No broad index data found. Check index name spelling in data files.")

        st.markdown("---")

        # ── Sectoral Indices ───────────────────────────────────────────────────
        st.subheader("Sectoral Indices")
        sectoral_rows = []
        for sec_label, sec_data in SECTORS.items():
            r = calc(ih, sec_data["idx"], sec_label)
            if r:
                sectoral_rows.append(r)

        if sectoral_rows:
            df_sect = pd.DataFrame(sectoral_rows)
            show_table(df_sect)
        else:
            st.info("No sectoral index data found in index files.")


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
                    if st.button(sec, key=f"sec_{sec}", use_container_width=True):
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
    st.header("⚖️ Compare Indices & Stocks")
    st.caption("Add any combination of indices and stocks. Press Enter after each.")

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**📊 Add Indices**")
        idx_input = st.selectbox(
            "Search and select an index",
            options=[""] + ALL_INDEX_NAMES,
            key="idx_sel",
            label_visibility="collapsed",
        )
        if st.button("➕ Add Index") and idx_input:
            if idx_input not in st.session_state.compare_indices:
                st.session_state.compare_indices.append(idx_input)
        if st.session_state.compare_indices:
            for i, name in enumerate(st.session_state.compare_indices):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"• {name}")
                if c2.button("✕", key=f"ri_{i}"):
                    st.session_state.compare_indices.pop(i)
                    st.rerun()

    with col_r:
        st.markdown("**🏷️ Add Stocks**")
        stk_input = st.text_input(
            "Type NSE symbol (e.g. RELIANCE) and press Add",
            key="stk_inp",
            label_visibility="collapsed",
            placeholder="e.g. RELIANCE",
        ).upper().strip()
        if st.button("➕ Add Stock") and stk_input:
            if stk_input not in st.session_state.compare_stocks:
                st.session_state.compare_stocks.append(stk_input)
        if st.session_state.compare_stocks:
            for i, sym in enumerate(st.session_state.compare_stocks):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"• {sym}")
                if c2.button("✕", key=f"rs_{i}"):
                    st.session_state.compare_stocks.pop(i)
                    st.rerun()

    if st.button("🗑 Clear All"):
        st.session_state.compare_indices = []
        st.session_state.compare_stocks  = []
        st.rerun()

    all_selected = st.session_state.compare_indices + st.session_state.compare_stocks

    if not all_selected:
        st.info("Add indices and/or stocks above to compare them side-by-side.")
    else:
        st.markdown("---")
        st.subheader("Comparison Table")

        rows = []
        for name in st.session_state.compare_indices:
            r = calc(ih, name, name) if has_index else None
            if r:
                rows.append(r)
            else:
                rows.append({"Name": f"{name} (no data)"})

        for sym in st.session_state.compare_stocks:
            r = calc(sh, sym, sym) if has_stocks else None
            if r:
                rows.append(r)
            else:
                rows.append({"Name": f"{sym} (not found)"})

        if rows:
            df_cmp = pd.DataFrame(rows)
            show_table(df_cmp)

        # Relative performance chart
        if len(all_selected) >= 2 and (has_stocks or has_index):
            st.markdown("---")
            st.subheader("Relative Performance (Rebased to 100)")
            chart_data = {}
            for name in st.session_state.compare_indices:
                if has_index:
                    df_i = ih[ih["TckrSymb"]==name].sort_values("TradDt").set_index("TradDt")["ClsPric"]
                    if not df_i.empty:
                        chart_data[name] = (df_i / df_i.iloc[0] * 100)
            for sym in st.session_state.compare_stocks:
                if has_stocks:
                    df_s = sh[sh["TckrSymb"]==sym].sort_values("TradDt").set_index("TradDt")["ClsPric"]
                    if not df_s.empty:
                        chart_data[sym] = (df_s / df_s.iloc[0] * 100)
            if chart_data:
                df_chart = pd.DataFrame(chart_data).dropna(how="all")
                st.line_chart(df_chart, height=350)
