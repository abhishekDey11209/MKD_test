import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
from backend import process_data

st.set_page_config(layout="wide")

# ================= GLOBAL UI =================
st.markdown("""
<style>
body { background-color: #0e1117; color: white; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(#1f77b4, #2ca02c);
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown("""
<div style="
    background: linear-gradient(90deg, #1f77b4, #2ca02c);
    padding: 20px;
    border-radius: 12px;
    color: white;
    text-align: center;
    font-size: 28px;
    font-weight: bold;
">
    📊 RETAIL SALES OVERVIEW
</div>
<br>
""", unsafe_allow_html=True)

# ================= LOAD =================
@st.cache_data
def load():
    return pd.read_excel("demo.xlsx", engine="openpyxl")

df = process_data(load())

# ================= FILTERS =================
st.sidebar.title("🎯 Filters")

levels = ["STND_TRRTRY_NM","Group","Department","Class","Sub Class"]

for col in levels:
    selected = st.sidebar.multiselect(col, df[col].unique(), df[col].unique())
    df = df[df[col].isin(selected)]

# ================= KPI LOGIC =================
def get_kpi_trend(df, col):
    df_sorted = df.sort_values('TRDNG_WK_END_DT')
    trend = df_sorted.groupby('TRDNG_WK_END_DT')[col].sum()

    current = trend.tail(1).values[0]
    previous = trend.tail(2).values[0] if len(trend) > 1 else current

    change = ((current - previous) / previous * 100) if previous != 0 else 0
    arrow = "↑" if change > 0 else "↓"
    color = "#2f9e44" if change > 0 else "#fa5252"

    return current, change, arrow, color, trend.tail(20)

def smart_kpi_card(title, col_name):
    value, change, arrow, color, trend = get_kpi_trend(df, col_name)

    fig = px.line(trend)
    fig.update_layout(
        height=70,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_visible=False,
        yaxis_visible=False
    )

    st.markdown(f"""
    <div style="
        background:#1c1f26;
        padding:12px;
        border-radius:12px;
        color:white;
    ">
        <div style="font-size:13px;">{title}</div>
        <div style="font-size:20px; font-weight:bold;">
            {round(value,2)}
        </div>
        <div style="color:{color}; font-size:12px;">
            {arrow} {round(change,2)}%
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.plotly_chart(fig, use_container_width=True)

# ================= KPI SECTION =================
st.markdown("## 📊 Performance & Insights")

# -------- ROW 1 --------
st.markdown("### 💰 Financial Metrics")

cols1 = st.columns(6)
kpis1 = [
    ("Revenue","REVENUE"),
    ("Sales Qty","SALES_QTY"),
    ("Current SOH","SOH_QTY"),
    ("Intake Margin","INTAKE_MARGIN"),
    ("Margin","MARGIN"),
    ("Margin %","MARGIN_PCT"),
]

for col, (title, kpi) in zip(cols1, kpis1):
    with col:
        smart_kpi_card(title, kpi)

# -------- ROW 2 --------
st.markdown("### 📦 Inventory & Performance")

cols2 = st.columns(6)
kpis2 = [
    ("ASP","ASP"),
    ("Markdown","CURR_MD"),
    ("ROS","ROS"),
    ("Cover","COVER"),
    ("Sell Through","SELL_THROUGH"),
    ("OOS %","OOS_PCT"),
]

for col, (title, kpi) in zip(cols2, kpis2):
    with col:
        smart_kpi_card(title, kpi)

# -------- ROW 3 --------
st.markdown("### 📈 Efficiency Metrics")

cols3 = st.columns(2)
kpis3 = [
    ("Stock to Sales","STOCK_TO_SALES"),
    ("GMROI","GMROI"),
]

for col, (title, kpi) in zip(cols3, kpis3):
    with col:
        smart_kpi_card(title, kpi)

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Insights", "📈 Trends"])

# =========================================================
# ================= OVERVIEW ===============================
# =========================================================
with tab1:

    st.markdown("## 📊 KPI Breakdown")

    level = st.selectbox("Select Level", levels)

    kpi = df.groupby(level).agg({
        'REVENUE':'sum',
        'SALES_QTY':'sum',
        'SOH_QTY':'sum',
        'MARGIN':'sum',
        'ROS':'mean',
        'COVER':'mean'
    }).reset_index()

    st.dataframe(kpi, use_container_width=True)

    # ================= DONUT =================
    st.markdown("## 🍩 KPI Comparison")

    kpi_col = st.selectbox("Select KPI", ['REVENUE','SALES_QTY','MARGIN'])

    df_sorted = df.sort_values('TRDNG_WK_END_DT')

    current = df_sorted.tail(4)[kpi_col].sum()
    previous = df_sorted.iloc[-8:-4][kpi_col].sum()

    donut_df = pd.DataFrame({
        "Period":["Current","Previous"],
        "Value":[current,previous]
    })

    fig = px.pie(donut_df, names='Period', values='Value', hole=0.6)
    st.plotly_chart(fig, use_container_width=True)

    # ================= DECISION MAP =================
    st.markdown("## 📍 Stock vs Demand")

    fig2 = px.scatter(
        df.sample(min(len(df),5000)),
        x='COVER',
        y='SELL_THROUGH',
        color='Department'
    )

    st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# ================= INSIGHTS ===============================
# =========================================================
with tab2:

    st.markdown("## 🚨 Alerts")

    df['ALERT'] = np.select(
        [
            (df['SELL_THROUGH'] < 0.3) & (df['COVER'] > 16),
            (df['SELL_THROUGH'] > 0.6) & (df['COVER'] < 12),
            (df['SOH_QTY'] == 0)
        ],
        ["Overstock","Stockout","No Stock"],
        default="Healthy"
    )

    st.bar_chart(df['ALERT'].value_counts())

# =========================================================
# ================= TRENDS ================================
# =========================================================
with tab3:

    st.markdown("## 📈 Trends")

    df['TIME'] = df['TRDNG_WK_END_DT']

    metric = st.selectbox("Metric", ['REVENUE','ROS','SELL_THROUGH'])

    trend = df.groupby('TIME')[metric].mean().reset_index()

    fig4 = px.line(trend, x='TIME', y=metric)
    st.plotly_chart(fig4, use_container_width=True)

# ================= EXPORT =================
st.sidebar.subheader("📤 Export")

output = io.BytesIO()
df.to_excel(output, index=False)

st.sidebar.download_button("Download Report", output.getvalue(), "report.xlsx")
