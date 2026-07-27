# NSE EOD TRACKER - BUILD 20260724
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import re

st.set_page_config(page_title="NSE EOD Tracker", layout="wide", page_icon="📈",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
  .block-container{padding-top:.5rem;padding-bottom:.5rem}
  .stTabs [data-baseweb="tab"]{font-size:14px;font-weight:500;padding:8px 18px}
  h2{font-size:1.15rem!important} h3{font-size:1rem!important}
  .metric-card{background:#0f172a;border:1px solid #1e293b;border-radius:10px;
    padding:14px 8px;text-align:center;margin-bottom:6px}
  .metric-card .num{font-size:1.8rem;font-weight:700;line-height:1.1}
  .metric-card .lbl{font-size:.7rem;color:#94a3b8;margin-top:3px}
  .g{color:#22c55e}.r{color:#ef4444}.w{color:#f1f5f9}
</style>""", unsafe_allow_html=True)

# ── PATHS ─────────────────────────────────────────────────────────────────────
STOCK_DIR = Path("data")
INDEX_DIR = Path("data/index")
DATE_PAT  = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ── SECTOR DEFINITIONS ────────────────────────────────────────────────────────
SECTORS = {
    "Nifty Bank":       {"idx":"Nifty Bank",       "stocks":["HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK","PNB","INDUSINDBK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","AUBANK","BANKBARODA"]},
    "Nifty PSU Bank":   {"idx":"Nifty PSU Bank",   "stocks":["SBIN","PNB","BANKBARODA","CANARABANK","UNIONBANK","BANKINDIA","CENTRALBK","UCOBANK","MAHABANK","INDIANB","IOB"]},
    "Nifty Private Bank":{"idx":"Nifty Private Bank","stocks":["HDFCBANK","ICICIBANK","KOTAKBANK","AXISBANK","INDUSINDBK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","AUBANK","RBLBANK"]},
    "Nifty Financial Services":{"idx":"Nifty Financial Services","stocks":["HDFCBANK","ICICIBANK","BAJFINANCE","KOTAKBANK","AXISBANK","SBIN","BAJAJFINSV","HDFCAMC","MUTHOOTFIN","CHOLAFIN","M&MFIN","SHRIRAMFIN","JIOFINSERV","HDFCLIFE","SBILIFE"]},
    "Nifty Housing Finance":{"idx":"Nifty Housing Finance","stocks":["LICHSGFIN","PNBHOUSING","AAVAS","CANFINHOME","HOMEFIRST","APTUS","REPCO"]},
    "Nifty NBFC":       {"idx":"Nifty Non-Cyclical Consumer","stocks":["BAJFINANCE","BAJAJFINSV","MUTHOOTFIN","CHOLAFIN","M&MFIN","SHRIRAMFIN","JIOFINSERV","MANAPPURAM","SUNDARMFIN"]},
    "Nifty Insurance":  {"idx":"Nifty India Insurance","stocks":["HDFCLIFE","SBILIFE","ICICIGI","LICI","STARHEALTH","GICRE","NIACL"]},
    "Nifty Energy":     {"idx":"Nifty Energy",     "stocks":["RELIANCE","ONGC","NTPC","POWERGRID","BPCL","IOC","GAIL","TATAPOWER","ADANIGREEN","ADANIPOWER"]},
    "Nifty Oil & Gas":  {"idx":"Nifty Oil and Gas","stocks":["RELIANCE","ONGC","BPCL","IOC","GAIL","HINDPETRO","MGL","IGL","PETRONET","GSPL","OIL","MRPL","GUJGASLTD"]},
    "Nifty Power":      {"idx":"Nifty Power",      "stocks":["NTPC","POWERGRID","TATAPOWER","ADANIPOWER","ADANIGREEN","CESC","JSWENERGY","TORNTPOWER","NHPC","SJVN"]},
    "Nifty Auto":       {"idx":"Nifty Auto",       "stocks":["MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","BOSCHLTD","BHARATFORG","ASHOKLEY","TVSMOTORS","MOTHERSON","UNOMINDA","TIINDIA","SONACOMS","EXIDEIND"]},
    "Nifty FMCG":       {"idx":"Nifty FMCG",       "stocks":["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO","COLPAL","GODREJCP","EMAMILTD","TATACONSUM","UBL","MCDOWELL-N","RADICO","VBL","BIKAJI"]},
    "Nifty IT":         {"idx":"Nifty IT",         "stocks":["TCS","INFY","HCLTECH","WIPRO","TECHM","LTIM","PERSISTENT","MPHASIS","COFORGE","OFSS"]},
    "Nifty Metal":      {"idx":"Nifty Metal",      "stocks":["TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","VEDL","SAIL","NMDC","APLAPOLLO","NATIONALUM","HINDCOPPER","MOIL","WELCORP","RATNAMANI","JINDALSAW"]},
    "Nifty Pharma":     {"idx":"Nifty Pharma",     "stocks":["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP","TORNTPHARM","ALKEM","AUROPHARMA","LUPIN","BIOCON"]},
    "Nifty Healthcare": {"idx":"Nifty Healthcare Index","stocks":["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","APOLLOHOSP","TORNTPHARM","ALKEM","AUROPHARMA","LUPIN","BIOCON","MAXHEALTH","FORTIS","LALPATHLAB","METROPOLIS","ZYDUSLIFE"]},
    "Nifty Hospital":   {"idx":"Nifty Healthcare Index","stocks":["APOLLOHOSP","MAXHEALTH","FORTIS","MEDANTA","NH","KIMS","RAINBOW","YATHARTH"]},
    "Nifty Realty":     {"idx":"Nifty Realty",     "stocks":["DLF","GODREJPROP","OBEROIRLTY","PHOENIXLTD","PRESTIGE","BRIGADE","SOBHA","SUNTECK","KOLTEPATIL","MAHLIFE"]},
    "Nifty Cement":     {"idx":"Nifty Infrastructure","stocks":["ULTRACEMCO","SHREECEM","AMBUJACEM","ACC","JKCEMENT","RAMCOCEM","HEIDELBERGCEMENT","BIRLACORPN","NUVOCO"]},
    "Nifty Construction":{"idx":"Nifty Infrastructure","stocks":["LT","ADANIPORTS","NBCC","IRB","KNRCON","PNCINFRA","ASHOKA","GPPL","CAPACITE"]},
    "Nifty Media":      {"idx":"Nifty Media",      "stocks":["SUNTV","ZEEL","PVRINOX","NAZARA","NXTDIGITAL","SAREGAMA","TIPS","BALAJITELE"]},
    "Nifty Capital Goods":{"idx":"Nifty India Manufacturing","stocks":["LT","SIEMENS","ABB","BHEL","BEL","HAL","CUMMINSIND","THERMAX","VOLTAS","HAVELLS","POLYCAB","KEI"]},
    "Nifty Consumer Durables":{"idx":"Nifty Consumer Durables","stocks":["TITAN","VOLTAS","HAVELLS","WHIRLPOOL","BLUESTAR","CROMPTON","VGUARD","DIXON","AMBER","KAJARIACER","POLYCAB"]},
    "Nifty Retail":     {"idx":"Nifty India Consumption","stocks":["DMART","TRENT","ABFRL","NYKAA","JUBLFOOD","DEVYANI","SAPPHIRE","WESTLIFE"]},
    "Nifty Telecom":    {"idx":"Nifty Communication Services","stocks":["BHARTIARTL","IDEA","TATACOMM","RAILTEL","HFCL","STLTECH"]},
    "Nifty Capital Markets":{"idx":"Nifty Capital Markets","stocks":["BSE","MCX","CAMS","CDSL","KFINTECH","ANGELONE","NUVAMA","IIFL","MOTILALOFS"]},
    "Nifty Commodities":{"idx":"Nifty Commodities","stocks":["RELIANCE","ONGC","COALINDIA","VEDL","HINDALCO","NMDC","SAIL","TATASTEEL","JSWSTEEL","NATIONALUM"]},
    "Nifty Defence":    {"idx":"Nifty India Defence","stocks":["HAL","BEL","BHEL","BEML","COCHINSHIP","GRSE","MAZAGON","MTAR","DATAPATTNS"]},
    "Nifty Transport":  {"idx":"Nifty India Transportation and Logistics","stocks":["DELHIVERY","BLUEDART","GATI","VRL","TCI","MAHINDRALOG","CONCOR","GATEWAY","ALLCARGO"]},
    "Nifty India Digital":{"idx":"Nifty India Digital","stocks":["INFY","TCS","WIPRO","HCLTECH","TECHM","ETERNAL","NYKAA","DELHIVERY","INDIAMART","JUSTDIAL","POLICYBZR","PAYTM"]},
    "Nifty India Manufacturing":{"idx":"Nifty India Manufacturing","stocks":["RELIANCE","LT","MARUTI","TATAMOTORS","SUNPHARMA","TATASTEEL","ULTRACEMCO","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","MOTHERSON","BOSCHLTD","SIEMENS","ABB","CUMMINSIND"]},
    "Nifty India Tourism":{"idx":"Nifty India Tourism","stocks":["INDHOTEL","LEMONTREE","CHALET","MAHINDRAHOLIDAY","THOMASCOOK","IRCTC","EASEMYTRIP"]},
    "Nifty Railways PSU":{"idx":"Nifty India Railways PSU Index","stocks":["RVNL","IRFC","IRCON","RAILTEL","RITES","IRCTC","BEML","NBCC"]},
}

BROAD_INDICES = ["Nifty 50","Nifty Next 50","Nifty 100","Nifty 200","Nifty 500",
                 "Nifty Total Market","Nifty Midcap 50","Nifty Midcap 100",
                 "Nifty Smallcap 50","Nifty Smallcap 100"]

ALL_INDEX_NAMES = BROAD_INDICES + list(SECTORS.keys())

RET_COLS = ["1D %","1W %","2W %","1M %","2M %","3M %","6M %","1Y %"]
EMA_COLS = ["4 EMA","10 EMA","20 EMA","50 EMA","100 EMA"]
PCT_COLS = RET_COLS + ["vs 52WH%","vs 52WL%"]

# ── COLOUR ────────────────────────────────────────────────────────────────────
def cell_bg(val, cap=20):
    try: v = float(val)
    except: return ""
    if pd.isna(v): return ""
    i = min(abs(v)/cap, 1.0)
    if v >= 0: r,g,b = int(255-i*195),int(255-i*55),int(255-i*195)
    else:      r,g,b = int(255-i*35), int(255-i*205),int(255-i*205)
    return f"background-color:rgb({r},{g},{b});color:#000;font-weight:600;"

def style_table(df, cap=20):
    cols = [c for c in PCT_COLS if c in df.columns]
    fmt  = {c:"{:.2f}" for c in df.columns if c != "Name"}
    s    = df.style.format(fmt, na_rep="—")
    fn   = s.map if hasattr(s,"map") else s.applymap
    return fn(lambda v: cell_bg(v, cap), subset=cols)

def show_table(df, cap=20, height=None):
    if df.empty: st.info("No data."); return
    order = ["Name","LTP"] + RET_COLS + EMA_COLS + ["52W High","vs 52WH%","52W Low","vs 52WL%"]
    cols  = [c for c in order if c in df.columns]
    h     = height or min(600, 55 + len(df)*38)
    st.dataframe(style_table(df[cols], cap), use_container_width=True, height=h)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def load_stocks():
    files = sorted(f for f in STOCK_DIR.glob("*.csv") if DATE_PAT.match(f.stem))
    if not files: return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, low_memory=False)
            df.columns = df.columns.str.strip()
            df = df.rename(columns={"SYMBOL":"TckrSymb","SERIES":"SctySrs",
                "HIGH":"HghPric","LOW":"LwPric","CLOSE":"ClsPric","PREVCLOSE":"PrvsClsgPric",
                "Symbol":"TckrSymb","Series":"SctySrs","High":"HghPric","Low":"LwPric",
                "Close":"ClsPric","Prev Close":"PrvsClsgPric"})
            if "TradDt" not in df.columns: df["TradDt"] = f.stem
            for c in ["ClsPric","HghPric","LwPric","PrvsClsgPric"]:
                df[c] = pd.to_numeric(df.get(c, np.nan), errors="coerce")
            if "HghPric" not in df.columns: df["HghPric"] = np.nan
            if "LwPric"  not in df.columns: df["LwPric"]  = np.nan
            dfs.append(df[["TradDt","TckrSymb","SctySrs","ClsPric","HghPric","LwPric","PrvsClsgPric"]])
        except: continue
    if not dfs: return pd.DataFrame()
    h = pd.concat(dfs, ignore_index=True)
    if "SctySrs" in h.columns:
        h = h[h["SctySrs"].astype(str).str.strip()=="EQ"]
    h["TradDt"]   = pd.to_datetime(h["TradDt"], errors="coerce")
    h["TckrSymb"] = h["TckrSymb"].astype(str).str.strip().str.upper()
    return h.dropna(subset=["TradDt","TckrSymb","ClsPric"]).sort_values("TradDt").reset_index(drop=True)

@st.cache_data(show_spinner=False, ttl=3600)
def load_index():
    files = sorted(f for f in INDEX_DIR.glob("*.csv") if DATE_PAT.match(f.stem)) if INDEX_DIR.exists() else []
    if not files: return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, low_memory=False)
            df.columns = df.columns.str.strip()
            df = df.rename(columns={"Index Name":"TckrSymb","Closing Index Value":"ClsPric","Closing":"ClsPric"})
            if "TckrSymb" not in df.columns or "ClsPric" not in df.columns: continue
            df["TradDt"]   = f.stem
            df["ClsPric"]  = pd.to_numeric(df["ClsPric"], errors="coerce")
            df["TckrSymb"] = df["TckrSymb"].astype(str).str.strip()
            dfs.append(df[["TradDt","TckrSymb","ClsPric"]].dropna())
        except: continue
    if not dfs: return pd.DataFrame()
    h = pd.concat(dfs, ignore_index=True)
    h["TradDt"] = pd.to_datetime(h["TradDt"], errors="coerce")
    return h.dropna().sort_values("TradDt").reset_index(drop=True)

# ── CALCULATE METRICS ─────────────────────────────────────────────────────────
def calc(hist, sym, label=None):
    df = hist[hist["TckrSymb"]==sym].sort_values("TradDt")
    if len(df) < 5: return None
    close   = df["ClsPric"].astype(float).values
    ltp     = float(close[-1])
    prev    = float(df["PrvsClsgPric"].iloc[-1]) if "PrvsClsgPric" in df.columns and not pd.isna(df["PrvsClsgPric"].iloc[-1]) else float(close[-2])
    cs      = pd.Series(close)
    last_dt = df["TradDt"].iloc[-1]
    dts     = df["TradDt"].values

    def ret(n):
        target = last_dt - pd.Timedelta(days=int(n*1.5)+n)
        mask   = dts <= target
        if not mask.any(): return np.nan
        p = float(close[int(np.where(mask)[0][-1])])
        return round(((ltp-p)/p)*100,2) if p else np.nan

    def ema(s): return round(float(cs.ewm(span=s,adjust=False).mean().iloc[-1]),2)

    has_hl = "HghPric" in df.columns and "LwPric" in df.columns
    h52    = round(float(df["HghPric"].astype(float).max()),2) if has_hl else np.nan
    l52    = round(float(df["LwPric"].astype(float).min()), 2) if has_hl else np.nan

    return {"Name":label or sym,"LTP":round(ltp,2),
            "1D %":round(((ltp-prev)/prev)*100,2) if prev else np.nan,
            "1W %":ret(5),"2W %":ret(10),"1M %":ret(21),"2M %":ret(42),
            "3M %":ret(63),"6M %":ret(126),"1Y %":ret(252),
            "4 EMA":ema(4),"10 EMA":ema(10),"20 EMA":ema(20),"50 EMA":ema(50),"100 EMA":ema(100),
            "52W High":h52,"vs 52WH%":round(((ltp-h52)/h52)*100,2) if not np.isnan(h52) else np.nan,
            "52W Low":l52,"vs 52WL%":round(((ltp-l52)/l52)*100,2) if not np.isnan(l52) else np.nan}

def build_rows(hist, syms):
    rows = [r for s in syms for r in [calc(hist,s,s)] if r]
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── INIT SESSION STATE ────────────────────────────────────────────────────────
for k,v in [("sector_view",None),("cmp_stocks",[]),("cmp_indices",[]),("cmp_view",None)]:
    if k not in st.session_state: st.session_state[k]=v

# ── LOAD ──────────────────────────────────────────────────────────────────────
with st.spinner("Loading EOD data…"):
    sh = load_stocks()
    ih = load_index()

has_s = not sh.empty
has_i = not ih.empty
last_date = sh["TradDt"].max().date() if has_s else None
all_syms  = sorted(sh["TckrSymb"].unique()) if has_s else []

if not has_s and not has_i:
    st.title("📈 NSE EOD Tracker")
    st.info("⏳ Data loading… GitHub Actions is running. Auto-refresh in 30s.")
    st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)
    st.stop()

st.sidebar.title("📈 NSE Tracker")
if last_date: st.sidebar.markdown(f"📅 **Last EOD:** `{last_date}`\n\n🏷️ **Stocks:** {len(all_syms)}")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Index Dashboard","🏭 Sectoral","⚖️ Compare"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 – INDEX DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("📊 Index Dashboard")

    # Broad indices
    st.subheader("Broad Market Indices")
    if has_i:
        rows = [r for n in BROAD_INDICES for r in [calc(ih,n,n)] if r]
        if rows: show_table(pd.DataFrame(rows))
        else: st.info("Broad index data not matched yet in index files.")
    else:
        st.warning("⏳ Index data not yet downloaded. Run GitHub Actions workflow.")

    st.markdown("---")

    # Sectoral indices
    st.subheader("Sectoral Indices")
    NSE_NAME = {k:v["idx"] for k,v in SECTORS.items()}
    if has_i:
        rows = [r for k,v in SECTORS.items() for r in [calc(ih,v["idx"],k)] if r]
        if rows: show_table(pd.DataFrame(rows))
        else: st.info("Sectoral index data not matched. Check data/index/ files.")
    else:
        st.warning("⏳ Index data not yet downloaded.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 – SECTORAL
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    if st.session_state.sector_view:
        if st.button("← Back to all sectors", key="back_sec"):
            st.session_state.sector_view = None
            st.rerun()

    if not st.session_state.sector_view:
        st.header("🏭 Sectoral Index")
        st.caption("Click any sector to see constituent stocks")
        names = list(SECTORS.keys())
        for row_start in range(0, len(names), 4):
            cols = st.columns(4)
            for col, sec in zip(cols, names[row_start:row_start+4]):
                with col:
                    if st.button(sec, key=f"sec_{sec}", use_container_width=True):
                        st.session_state.sector_view = sec
                        st.rerun()
    else:
        sec      = st.session_state.sector_view
        sec_data = SECTORS[sec]
        st.header(f"🏭 {sec}")

        if has_i:
            ir = calc(ih, sec_data["idx"], f"▶ {sec} INDEX")
            if ir:
                st.subheader("Index")
                show_table(pd.DataFrame([ir]))

        st.subheader("Constituent Stocks")
        avail   = [s for s in sec_data["stocks"] if s in all_syms]
        missing = [s for s in sec_data["stocks"] if s not in all_syms]
        if missing: st.caption(f"ℹ️ Not in data: {', '.join(missing)}")
        if avail and has_s:
            df_s = build_rows(sh, avail)
            if not df_s.empty:
                num  = [c for c in df_s.columns if c != "Name"]
                avg  = {"Name":f"📊 {sec} AVG"}
                avg.update(df_s[num].mean(numeric_only=True).round(2).to_dict())
                show_table(pd.concat([pd.DataFrame([avg]), df_s], ignore_index=True))

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 – COMPARE
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:

    # ── Detail view (drill-down) ───────────────────────────────────────────────
    if st.session_state.cmp_view:
        if st.button("← Back to Compare", key="back_cmp"):
            st.session_state.cmp_view = None
            st.rerun()

        vtype, vname = st.session_state.cmp_view

        if vtype == "index":
            st.header(f"📊 {vname}")
            sec_data = SECTORS.get(vname)

            # Index row
            if has_i:
                nse = sec_data["idx"] if sec_data else vname
                ir  = calc(ih, nse, f"▶ {vname} INDEX")
                if not ir: ir = calc(ih, vname, f"▶ {vname}")
                if ir:
                    st.subheader("Index Value")
                    show_table(pd.DataFrame([ir]))

            # Stocks
            if sec_data and has_s:
                st.subheader("Constituent Stocks")
                avail   = [s for s in sec_data["stocks"] if s in all_syms]
                missing = [s for s in sec_data["stocks"] if s not in all_syms]
                if missing: st.caption(f"ℹ️ Not in data: {', '.join(missing)}")
                if avail:
                    df_s = build_rows(sh, avail)
                    if not df_s.empty:
                        num = [c for c in df_s.columns if c != "Name"]
                        avg = {"Name":f"📊 {vname} AVG"}
                        avg.update(df_s[num].mean(numeric_only=True).round(2).to_dict())
                        show_table(pd.concat([pd.DataFrame([avg]), df_s], ignore_index=True))
            elif not sec_data:
                st.info("Broad index — constituent stock list not available here.")

        elif vtype == "stock":
            st.header(f"🏷️ {vname}")
            r = calc(sh, vname, vname) if has_s else None
            if r: show_table(pd.DataFrame([r]))
            else: st.warning(f"{vname} not found in data.")

        st.stop()

    # ── Main compare page ──────────────────────────────────────────────────────
    st.header("⚖️ Compare Indices & Stocks")

    left, right = st.columns([1, 2], gap="large")

    with left:
        # ── Index input ────────────────────────────────────────────────────────
        st.markdown("#### 📊 Index")
        idx_inp = st.text_input("Type index name", key="idx_inp",
                                placeholder="e.g. Nifty Bank",
                                label_visibility="collapsed")
        if idx_inp:
            matches = [n for n in ALL_INDEX_NAMES if idx_inp.lower() in n.lower()][:5]
            for m in matches:
                if st.button(m, key=f"is_{m}"):
                    if m not in st.session_state.cmp_indices:
                        st.session_state.cmp_indices.append(m)
                    st.rerun()

        ca, cb = st.columns(2)
        with ca:
            if st.button("➕ Add", key="add_i") and idx_inp:
                best = next((n for n in ALL_INDEX_NAMES if idx_inp.lower() in n.lower()), None)
                if best and best not in st.session_state.cmp_indices:
                    st.session_state.cmp_indices.append(best)
                    st.rerun()
        with cb:
            if st.button("🗑 Clear", key="clr_i"):
                st.session_state.cmp_indices = []
                st.rerun()

        for i, n in enumerate(st.session_state.cmp_indices):
            c1,c2 = st.columns([5,1])
            c1.markdown(f"• {n}")
            if c2.button("✕", key=f"di_{i}"):
                st.session_state.cmp_indices.pop(i); st.rerun()

        st.markdown("---")

        # ── Stock input ────────────────────────────────────────────────────────
        st.markdown("#### 🏷️ Stock")
        stk_inp = st.text_input("Type NSE symbol", key="stk_inp",
                                placeholder="e.g. RELIANCE or RELIANCE,TCS",
                                label_visibility="collapsed").upper().strip()
        if stk_inp and has_s:
            sym_matches = [s for s in all_syms if stk_inp.split(",")[0].strip() in s][:5]
            for m in sym_matches:
                if st.button(m, key=f"ss_{m}"):
                    if m not in st.session_state.cmp_stocks:
                        st.session_state.cmp_stocks.append(m)
                    st.rerun()

        da, db = st.columns(2)
        with da:
            if st.button("➕ Add", key="add_s") and stk_inp:
                for s in [x.strip() for x in stk_inp.split(",") if x.strip()]:
                    if s not in st.session_state.cmp_stocks:
                        st.session_state.cmp_stocks.append(s)
                st.rerun()
        with db:
            if st.button("🗑 Clear", key="clr_s"):
                st.session_state.cmp_stocks = []
                st.rerun()

        for i, s in enumerate(st.session_state.cmp_stocks):
            c1,c2 = st.columns([5,1])
            c1.markdown(f"• {s}")
            if c2.button("✕", key=f"ds_{i}"):
                st.session_state.cmp_stocks.pop(i); st.rerun()

    # ── Right panel – results ──────────────────────────────────────────────────
    with right:
        if not st.session_state.cmp_indices and not st.session_state.cmp_stocks:
            st.info("👈 Add indices or stocks on the left to compare them here.")
        else:
            NSE_MAP = {k:v["idx"] for k,v in SECTORS.items()}
            NSE_MAP.update({n:n for n in BROAD_INDICES})

            # Indices table
            if st.session_state.cmp_indices:
                st.markdown("#### 📊 Indices")
                rows = []
                for n in st.session_state.cmp_indices:
                    nse = NSE_MAP.get(n, n)
                    r   = calc(ih, nse, n) if has_i else None
                    rows.append(r if r else {"Name":f"{n} (no data)"})
                show_table(pd.DataFrame(rows))

                st.markdown("**Drill down →**")
                for n in st.session_state.cmp_indices:
                    if st.button(f"🔍 {n} stocks", key=f"drll_{n}"):
                        st.session_state.cmp_view = ("index", n)
                        st.rerun()

            # Stocks table
            if st.session_state.cmp_stocks:
                st.markdown("#### 🏷️ Stocks")
                rows = []
                for s in st.session_state.cmp_stocks:
                    r = calc(sh, s, s) if has_s else None
                    rows.append(r if r else {"Name":f"{s} (not found)"})
                show_table(pd.DataFrame(rows))

                for s in st.session_state.cmp_stocks:
                    if st.button(f"🔍 {s} detail", key=f"drll_{s}"):
                        st.session_state.cmp_view = ("stock", s)
                        st.rerun()

            # Chart
            if len(st.session_state.cmp_indices)+len(st.session_state.cmp_stocks) >= 2:
                st.markdown("---")
                st.markdown("#### 📈 Relative Performance (Rebased to 100)")
                chart = {}
                for n in st.session_state.cmp_indices:
                    nse = NSE_MAP.get(n,n)
                    if has_i:
                        s = ih[ih["TckrSymb"]==nse].sort_values("TradDt").set_index("TradDt")["ClsPric"].dropna()
                        if not s.empty: chart[n] = s/s.iloc[0]*100
                for sym in st.session_state.cmp_stocks:
                    if has_s:
                        s = sh[sh["TckrSymb"]==sym].sort_values("TradDt").set_index("TradDt")["ClsPric"].dropna()
                        if not s.empty: chart[sym] = s/s.iloc[0]*100
                if chart:
                    st.line_chart(pd.DataFrame(chart).dropna(how="all"), height=350)
