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
[data-testid="stMetricValue"] { font-size: 20px; }

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

# ================= KPI CARD FUNCTION =================
def kpi_card(title, value, color):
    return f"""
    <div style="
        background:{color};
        padding:15px;
        border-radius:12px;
        text-align:center;
        color:white;
        font-weight:bold;
    ">
        <div style="font-size:14px;">{title}</div>
        <div style="font-size:22px;">{value}</div>
    </div>
    """

# ================= KPI CARDS (ADDED) =================
kpi_html = f"""
<div style="display:flex; gap:10px;">
    {kpi_card("Revenue", round(df['REVENUE'].sum(),2), "#ff6b6b")}
    {kpi_card("Sales Qty", round(df['SALES_QTY'].sum(),2), "#51cf66")}
    {kpi_card("Margin", round(df['MARGIN'].sum(),2), "#845ef7")}
    {kpi_card("ROS", round(df['ROS'].mean(),2), "#fcc419")}
    {kpi_card("Cover", round(df['COVER'].mean(),2), "#339af0")}
    {kpi_card("Sell Through", round(df['SELL_THROUGH'].mean(),2), "#20c997")}
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Insights", "📈 Trends"])

# =========================================================
# ================= TAB 1 : OVERVIEW =======================
# =========================================================
with tab1:

    st.title("📊 Retail Overview")

    # (YOUR ORIGINAL KPI METRICS KEPT)
    row1 = st.columns(8)
    row1[0].metric("Revenue", round(df['REVENUE'].sum(),2))
    row1[1].metric("Qty", round(df['SALES_QTY'].sum(),2))
    row1[2].metric("SOH", round(df['SOH_QTY'].sum(),2))
    row1[3].metric("Intake", round(df['INTAKE_MARGIN'].sum(),2))
    row1[4].metric("Margin", round(df['MARGIN'].sum(),2))
    row1[5].metric("Margin %", round(df['MARGIN_PCT'].mean(),2))
    row1[6].metric("ASP", round(df['ASP'].mean(),2))
    row1[7].metric("Markdown", round(df['CURR_MD'].mean(),2))

    row2 = st.columns(6)
    row2[0].metric("ROS", round(df['ROS'].mean(),2))
    row2[1].metric("Cover", round(df['COVER'].mean(),2))
    row2[2].metric("Sell Through", round(df['SELL_THROUGH'].mean(),2))
    row2[3].metric("OOS %", round(df['OOS_PCT'].mean(),2))
    row2[4].metric("Stock/Sales", round(df['STOCK_TO_SALES'].mean(),2))
    row2[5].metric("GMROI", round(df['GMROI'].mean(),2))

    # ================= KPI TABLE =================
    st.subheader("📋 KPI Breakdown")

    level = st.selectbox("Select Level", levels)

    kpi = df.groupby(level).agg({
        'REVENUE':'sum',
        'SALES_QTY':'sum',
        'SOH_QTY':'sum',
        'INTAKE_MARGIN':'sum',
        'MARGIN':'sum',
        'MARGIN_PCT':'mean',
        'ASP':'mean',
        'CURR_MD':'mean',
        'ROS':'mean',
        'COVER':'mean',
        'SELL_THROUGH':'mean',
        'OOS_PCT':'mean'
    }).reset_index()

    st.dataframe(kpi, use_container_width=True)

    # ================= DONUT =================
    st.subheader("🍩 KPI Comparison")

    kpi_map = {
        "Revenue": "REVENUE",
        "Quantity": "SALES_QTY",
        "SOH": "SOH_QTY",
        "Intake Margin": "INTAKE_MARGIN",
        "Margin": "MARGIN",
        "Margin %": "MARGIN_PCT",
        "ASP": "ASP",
        "Markdown": "CURR_MD",
        "ROS": "ROS",
        "Cover": "COVER",
        "Sell Through": "SELL_THROUGH",
        "OOS %": "OOS_PCT"
    }

    kpi_name = st.selectbox("Select KPI", list(kpi_map.keys()))
    kpi_col = kpi_map[kpi_name]

    period = st.selectbox("Period", ["Weekly","Monthly","Quarterly","Yearly"])
    n_periods = st.slider("Periods", 1, 12, 4)

    df_sorted = df.sort_values('TRDNG_WK_END_DT')

    if period == "Monthly":
        df_sorted['TIME'] = df_sorted['TRDNG_WK_END_DT'].dt.to_period('M')
    elif period == "Quarterly":
        df_sorted['TIME'] = df_sorted['TRDNG_WK_END_DT'].dt.to_period('Q')
    elif period == "Yearly":
        df_sorted['TIME'] = df_sorted['TRDNG_WK_END_DT'].dt.to_period('Y')
    else:
        df_sorted['TIME'] = df_sorted['TRDNG_WK_END_DT']

    agg = df_sorted.groupby('TIME')[kpi_col].sum().reset_index()

    current = agg.tail(n_periods)[kpi_col].sum()
    previous = agg.iloc[-2*n_periods:-n_periods][kpi_col].sum()

    donut_df = pd.DataFrame({
        "Period": ["Current","Previous"],
        "Value": [current,previous]
    })

    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(donut_df, names='Period', values='Value', hole=0.6)

        st.markdown('<div style="background:#1c1f26;padding:15px;border-radius:12px;">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        change = ((current - previous)/previous*100) if previous != 0 else 0
        st.metric("Change", round(current,2), f"{round(change,2)}%")

    # ================= DECISION MAP =================
    st.subheader("📍 Stock vs Demand")

    fig2 = px.scatter(
        df.sample(min(len(df),5000)),
        x='COVER',
        y='SELL_THROUGH',
        color='Department',
        render_mode='svg'
    )

    st.markdown('<div style="background:#1c1f26;padding:15px;border-radius:12px;">', unsafe_allow_html=True)
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ================= INSIGHTS & TRENDS (UNCHANGED) =================
# (kept exactly as your original code)
