import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Nassau Candy | Profitability Intelligence", page_icon="🍬", layout="wide")

# ---------- Theme ----------
st.markdown("""
<style>
    .stApp { background: #0b1020; color: #e8edf7; }
    section[data-testid="stSidebar"] { background: #11182a; border-right: 1px solid #26324a; }
    .block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px; }
    h1, h2, h3 { color: #f3f6fc !important; letter-spacing: -0.025em; }
    p, label, span, div { }
    .hero { background: linear-gradient(120deg,#171f35,#142b3a); border: 1px solid #2c405a;
            border-radius: 18px; padding: 24px 28px; margin-bottom: 18px; }
    .eyebrow { color: #7dd3fc; text-transform: uppercase; font-size: 11px; letter-spacing: .16em; font-weight: 700; }
    .hero-title { font-size: 31px; font-weight: 800; margin: 7px 0 5px; color: #f8fafc; }
    .hero-sub { color: #b7c4d9; font-size: 14px; }
    .metric-card { background: #121b2d; border: 1px solid #28364d; border-radius: 14px; padding: 16px 18px; min-height: 112px; }
    .metric-label { color: #9eacc4; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .metric-value { color: #f8fafc; font-size: 26px; font-weight: 800; margin-top: 7px; }
    .metric-note { color: #93a4bf; font-size: 11px; margin-top: 2px; }
    .section-note { color: #9eacc4; font-size: 13px; }
    div[data-testid="stDataFrame"] { border: 1px solid #28364d; border-radius: 10px; overflow: hidden; }
    .risk { color: #fca5a5; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "Nassau Candy Distributor.csv")

def money(v):
    return f"${v:,.0f}"

def pct(v):
    return f"{v:.1f}%"

@st.cache_data(show_spinner=False)
def load_data(file_bytes=None):
    if file_bytes is not None:
        import io
        if file_bytes[:4] == b"PK\x03\x04":
            data = pd.read_excel(io.BytesIO(file_bytes))
        else:
            data = pd.read_csv(io.BytesIO(file_bytes))
    else:
        if os.path.exists(DATA_PATH):
            data = pd.read_csv(DATA_PATH)
        else:
            return pd.DataFrame()
    data.columns = [str(c).strip() for c in data.columns]
    required = ["Order Date", "Division", "Product Name", "Sales", "Units", "Gross Profit", "Cost"]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    for c in ["Sales", "Units", "Gross Profit", "Cost"]:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data["Order Date"] = pd.to_datetime(data["Order Date"], errors="coerce", dayfirst=True)
    if "Ship Date" in data:
        data["Ship Date"] = pd.to_datetime(data["Ship Date"], errors="coerce", dayfirst=True)
    for c in ["Division", "Product Name", "Region", "State/Province", "Ship Mode"]:
        if c in data:
            data[c] = data[c].fillna("Unknown").astype(str).str.strip()
    data = data.dropna(subset=["Sales", "Gross Profit", "Cost", "Units", "Order Date", "Product Name", "Division"])
    data = data[data["Sales"] > 0].copy()
    data["Gross Margin (%)"] = np.where(data["Sales"] != 0, data["Gross Profit"] / data["Sales"] * 100, np.nan)
    data["Profit per Unit"] = np.where(data["Units"] > 0, data["Gross Profit"] / data["Units"], np.nan)
    data["Revenue Contribution (%)"] = data["Sales"] / data["Sales"].sum() * 100 if data["Sales"].sum() else 0
    total_profit = data["Gross Profit"].sum()
    data["Profit Contribution (%)"] = data["Gross Profit"] / total_profit * 100 if total_profit else 0
    data["Month"] = data["Order Date"].dt.to_period("M").dt.to_timestamp()
    return data

def metric(label, value, note=""):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

def chart_layout(fig, height=360):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#dbe5f5", family="Inter, Arial"),
        margin=dict(l=15, r=15, t=45, b=15),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#263248", zerolinecolor="#263248"),
        yaxis=dict(gridcolor="#263248", zerolinecolor="#263248")
    )
    return fig

st.sidebar.markdown("## 🍬 NASSAU CANDY")
st.sidebar.caption("PROFITABILITY INTELLIGENCE")
st.sidebar.divider()
uploaded = st.sidebar.file_uploader("Upload transaction dataset", type=["csv", "xlsx"])
st.sidebar.caption("Default source: Nassau Candy Distributor CSV bundled with this project.")
st.sidebar.divider()
st.sidebar.markdown("### Analysis controls")

try:
    raw = load_data(uploaded.getvalue() if uploaded else None)
except Exception as e:
    st.error(f"Could not load dataset: {e}")
    st.stop()

if raw.empty:
    st.warning("No dataset found. Upload the Nassau Candy CSV or Excel workbook to begin.")
    st.stop()

min_date = raw["Order Date"].min().date()
max_date = raw["Order Date"].max().date()
date_range = st.sidebar.date_input("Order date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
divisions = sorted(raw["Division"].dropna().unique().tolist())
selected_divisions = st.sidebar.multiselect("Division", divisions, default=divisions)
margin_threshold = st.sidebar.slider("Low-margin threshold (%)", 0, 100, 25, 1)
search = st.sidebar.text_input("Search product", placeholder="Type a product name…")
metric_choice = st.sidebar.radio("Analyze by", ["Gross Profit", "Sales", "Units"], horizontal=False)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = raw[
    raw["Order Date"].dt.date.between(start_date, end_date)
    & raw["Division"].isin(selected_divisions)
].copy()
if search.strip():
    filtered = filtered[filtered["Product Name"].str.contains(search.strip(), case=False, na=False)]

if filtered.empty:
    st.warning("No records match these filters. Adjust the date range, division, or product search.")
    st.stop()

total_sales = filtered["Sales"].sum()
total_profit = filtered["Gross Profit"].sum()
total_cost = filtered["Cost"].sum()
total_units = filtered["Units"].sum()
overall_margin = total_profit / total_sales * 100 if total_sales else 0
order_count = filtered["Order ID"].nunique() if "Order ID" in filtered else len(filtered)
product_count = filtered["Product Name"].nunique()

st.markdown("""
<div class="hero">
  <div class="eyebrow">Commercial performance • Margin intelligence</div>
  <div class="hero-title">Product Line Profitability & Margin Performance</div>
  <div class="hero-sub">Nassau Candy Distributor · Find the products and divisions creating real financial value—not just sales volume.</div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["Executive Overview", "Product Profitability", "Division Performance", "Cost & Margin Diagnostics", "Profit Concentration", "Data Quality"])

with tabs[0]:
    st.markdown("### Executive overview")
    st.markdown('<div class="section-note">Filtered view of revenue, gross profit, costs, and portfolio margin.</div>', unsafe_allow_html=True)
    c = st.columns(5)
    with c[0]: metric("Revenue", money(total_sales), "Sales in selected period")
    with c[1]: metric("Gross profit", money(total_profit), "Sales minus cost")
    with c[2]: metric("Gross margin", pct(overall_margin), "Gross profit / sales")
    with c[3]: metric("Total cost", money(total_cost), "Reported product cost")
    with c[4]: metric("Products", f"{product_count:,}", f"{order_count:,} distinct orders")
    left, right = st.columns([1.2, 1])
    div = filtered.groupby("Division", as_index=False).agg(Sales=("Sales","sum"), Profit=("Gross Profit","sum"), Cost=("Cost","sum"), Units=("Units","sum"))
    div["Margin (%)"] = np.where(div["Sales"] != 0, div["Profit"]/div["Sales"]*100, 0)
    with left:
        fig = px.bar(div, x="Division", y=["Sales","Profit"], barmode="group", title="Revenue vs gross profit by division", color_discrete_sequence=["#7dd3fc","#a78bfa"])
        st.plotly_chart(chart_layout(fig), use_container_width=True)
    with right:
        fig = px.pie(div, names="Division", values="Profit", hole=.62, title="Gross profit mix by division", color_discrete_sequence=["#7dd3fc","#a78bfa","#fbbf24","#f472b6"])
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(chart_layout(fig), use_container_width=True)
    monthly = filtered.groupby("Month", as_index=False).agg(Sales=("Sales","sum"), Profit=("Gross Profit","sum"))
    if not monthly.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Sales"], mode="lines+markers", name="Sales", line=dict(width=3, color="#7dd3fc")))
        fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Profit"], mode="lines+markers", name="Gross profit", line=dict(width=3, color="#a78bfa")))
        fig.update_layout(title="Monthly revenue and profit trend")
        st.plotly_chart(chart_layout(fig, 320), use_container_width=True)

with tabs[1]:
    st.markdown("### Product-level profitability")
    products = filtered.groupby(["Division","Product Name"], as_index=False).agg(
        Sales=("Sales","sum"), Profit=("Gross Profit","sum"), Cost=("Cost","sum"), Units=("Units","sum"),
        Rows=("Row ID","count") if "Row ID" in filtered.columns else ("Sales","count")
    )
    products["Gross Margin (%)"] = np.where(products["Sales"] != 0, products["Profit"]/products["Sales"]*100, 0)
    products["Profit per Unit"] = np.where(products["Units"] > 0, products["Profit"]/products["Units"], np.nan)
    products["Revenue Contribution (%)"] = products["Sales"]/products["Sales"].sum()*100
    products["Profit Contribution (%)"] = products["Profit"]/products["Profit"].sum()*100 if products["Profit"].sum() else 0
    sort_by = st.selectbox("Rank products by", ["Gross Profit", "Gross Margin (%)", "Sales", "Profit per Unit", "Revenue Contribution (%)"])
    top_n = st.slider("Number of products to show", 5, min(30, max(5, len(products))), min(15, max(5, len(products))))
    ranked = products.sort_values(sort_by, ascending=False).head(top_n)
    fig = px.bar(ranked.sort_values(sort_by), x=sort_by, y="Product Name", color="Division", orientation="h", title=f"Top {top_n} products by {sort_by}", color_discrete_sequence=["#7dd3fc","#a78bfa","#fbbf24","#f472b6"])
    st.plotly_chart(chart_layout(fig, max(360, top_n*28)), use_container_width=True)
    products["Margin status"] = np.where(products["Gross Margin (%)"] < margin_threshold, "Margin risk", "Healthy")
    display = products.sort_values("Profit", ascending=False).copy()
    for col in ["Sales","Profit","Cost","Profit per Unit"]:
        display[col] = display[col].round(2)
    for col in ["Gross Margin (%)","Revenue Contribution (%)","Profit Contribution (%)"]:
        display[col] = display[col].round(2)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button("Download product profitability CSV", display.to_csv(index=False).encode("utf-8"), "product_profitability.csv", "text/csv")

with tabs[2]:
    st.markdown("### Division performance")
    div = filtered.groupby("Division", as_index=False).agg(Sales=("Sales","sum"), Profit=("Gross Profit","sum"), Cost=("Cost","sum"), Units=("Units","sum"))
    div["Gross Margin (%)"] = np.where(div["Sales"] != 0, div["Profit"]/div["Sales"]*100, 0)
    div["Profit per Unit"] = np.where(div["Units"] > 0, div["Profit"]/div["Units"], np.nan)
    a,b = st.columns(2)
    with a:
        fig = px.bar(div, x="Division", y="Gross Margin (%)", color="Gross Margin (%)", title="Gross margin by division", color_continuous_scale=["#f87171","#fbbf24","#34d399"])
        st.plotly_chart(chart_layout(fig), use_container_width=True)
    with b:
        fig = px.scatter(div, x="Sales", y="Profit", size="Units", color="Division", hover_data=["Gross Margin (%)"], title="Revenue vs profit (bubble size = units)", color_discrete_sequence=["#7dd3fc","#a78bfa","#fbbf24","#f472b6"])
        st.plotly_chart(chart_layout(fig), use_container_width=True)
    st.dataframe(div.sort_values("Profit", ascending=False).round(2), use_container_width=True, hide_index=True)

with tabs[3]:
    st.markdown("### Cost & margin diagnostics")
    diag = filtered.groupby(["Division","Product Name"], as_index=False).agg(Sales=("Sales","sum"), Profit=("Gross Profit","sum"), Cost=("Cost","sum"), Units=("Units","sum"))
    diag["Gross Margin (%)"] = np.where(diag["Sales"] != 0, diag["Profit"]/diag["Sales"]*100, 0)
    diag["Profit per Unit"] = np.where(diag["Units"] > 0, diag["Profit"]/diag["Units"], np.nan)
    diag["Risk flag"] = np.select(
        [diag["Gross Margin (%)"] < margin_threshold, (diag["Cost"]/diag["Sales"] > 0.85), (diag["Profit"] < 0)],
        ["Low margin", "Cost-heavy", "Loss-making"], default="Healthy"
    )
    fig = px.scatter(diag, x="Sales", y="Cost", size=np.maximum(diag["Units"],1), color="Gross Margin (%)",
                     hover_name="Product Name", hover_data=["Division","Profit","Gross Margin (%)","Risk flag"],
                     title="Product cost vs sales", color_continuous_scale=["#f87171","#fbbf24","#34d399"], size_max=30)
    fig.add_shape(type="line", x0=0, y0=0, x1=max(diag["Sales"].max(),1), y1=max(diag["Sales"].max(),1), line=dict(dash="dash", color="#8da0bb"))
    st.plotly_chart(chart_layout(fig, 420), use_container_width=True)
    risk = diag[diag["Risk flag"] != "Healthy"].sort_values(["Gross Margin (%)","Profit"])
    st.markdown("#### Products to review")
    st.caption("Risk flags are screening signals, not automatic discontinuation decisions. Validate with commercial and sourcing context.")
    st.dataframe(risk.round(2), use_container_width=True, hide_index=True)
    st.download_button("Download margin-risk list", risk.to_csv(index=False).encode("utf-8"), "margin_risk_products.csv", "text/csv")

with tabs[4]:
    st.markdown("### Profit concentration & dependency")
    prod = filtered.groupby("Product Name", as_index=False).agg(Sales=("Sales","sum"), Profit=("Gross Profit","sum"))
    mode = st.radio("Concentration measure", ["Revenue", "Gross profit"], horizontal=True)
    col = "Sales" if mode == "Revenue" else "Profit"
    prod = prod.sort_values(col, ascending=False).reset_index(drop=True)
    total = prod[col].sum()
    prod["Contribution (%)"] = prod[col]/total*100 if total else 0
    prod["Cumulative contribution (%)"] = prod["Contribution (%)"].cumsum()
    prod["Rank"] = np.arange(1, len(prod)+1)
    n80 = int((prod["Cumulative contribution (%)"] < 80).sum() + 1) if len(prod) else 0
    dep = n80/len(prod)*100 if len(prod) else 0
    a,b,c = st.columns(3)
    with a: metric("Products in 80% share", f"{n80}", f"of {len(prod)} products")
    with b: metric("Portfolio share", pct(dep), "Products needed to reach ~80%")
    with c: metric("Top 5 share", pct(prod.head(5)["Contribution (%)"].sum() if len(prod) else 0), f"by {mode.lower()}")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=prod["Product Name"], y=prod["Contribution (%)"], name="Individual contribution", marker_color="#7dd3fc"))
    fig.add_trace(go.Scatter(x=prod["Product Name"], y=prod["Cumulative contribution (%)"], name="Cumulative contribution", yaxis="y2", line=dict(color="#fbbf24", width=3)))
    fig.add_hline(y=80, line_dash="dash", line_color="#f87171", yref="y2")
    fig.update_layout(title=f"Pareto analysis by {mode.lower()}", xaxis_tickangle=-55, yaxis_title="Contribution (%)",
                      yaxis2=dict(title="Cumulative (%)", overlaying="y", side="right", range=[0,105], showgrid=False))
    st.plotly_chart(chart_layout(fig, 470), use_container_width=True)
    st.dataframe(prod.head(25).round(2), use_container_width=True, hide_index=True)
    if "State/Province" in filtered.columns:
        state = filtered.groupby("State/Province", as_index=False).agg(Sales=("Sales","sum"), Profit=("Gross Profit","sum"), Orders=("Order ID","nunique") if "Order ID" in filtered else ("Sales","count"))
        state = state.sort_values("Sales", ascending=False).head(15)
        fig = px.bar(state, x="Sales", y="State/Province", orientation="h", title="Top states by sales", color="Profit", color_continuous_scale=["#fbbf24","#7dd3fc"])
        st.plotly_chart(chart_layout(fig, 400), use_container_width=True)

with tabs[5]:
    st.markdown("### Data quality & validation")
    quality = pd.DataFrame({
        "Check": ["Rows loaded", "Rows after filters", "Missing order dates", "Missing product names", "Non-positive sales excluded", "Negative gross profit rows", "Units <= 0 rows", "Cost vs sales mismatch (gross profit != sales - cost)"],
        "Result": [
            f"{len(raw):,}", f"{len(filtered):,}",
            f"{raw['Order Date'].isna().sum():,}",
            f"{raw['Product Name'].isna().sum():,}",
            f"{(raw['Sales'] <= 0).sum():,}",
            f"{(raw['Gross Profit'] < 0).sum():,}",
            f"{(raw['Units'] <= 0).sum():,}",
            f"{((raw['Sales'] - raw['Cost'] - raw['Gross Profit']).abs() > 0.02).sum():,}"
        ]
    })
    st.dataframe(quality, use_container_width=True, hide_index=True)
    st.caption("The dashboard removes records with missing core numeric/date fields and non-positive sales for profitability analysis. Original uploaded data is not modified.")
    st.markdown("#### Dataset preview")
    st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)
    st.download_button("Download filtered data CSV", filtered.to_csv(index=False).encode("utf-8"), "filtered_nassau_candy_data.csv", "text/csv")

st.sidebar.divider()
st.sidebar.caption("Profitability signals support decision-making; confirm pricing, supplier terms, and strategic role before changing a product.")

