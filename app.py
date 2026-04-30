import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
from backend import process_data

st.set_page_config(layout="wide")

# ================= DARK UI =================
st.markdown("""
<style>
body { background-color: #0e1117; color: white; }
[data-testid="stMetricValue"] {
    font-size: 20px;
}
</style>
""", unsafe_allow_html=True)

# ================= LOAD =================
@st.cache_data
def load():
    return pd.read_excel("demo.xlsx", engine="openpyxl")

df = process_data(load())

# ================= SIDEBAR =================
st.sidebar.title("🎯 Filters")

levels = ["STND_TRRTRY_NM","Group","Department","Class","Sub Class"]

for col in levels:
    selected = st.sidebar.multiselect(col, df[col].unique(), df[col].unique())
    df = df[df[col].isin(selected)]

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Insights", "📈 Trends"])

# =========================================================
# ================= TAB 1 : OVERVIEW =======================
# =========================================================
with tab1:

    st.title("📊 Retail Overview")

    # KPI CARDS
    c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)

    c1.metric("Revenue", round(df['REVENUE'].sum(),2))
    c2.metric("Qty", round(df['SALES_QTY'].sum(),2))
    c3.metric("SOH", round(df['SOH_QTY'].sum(),2))
    c4.metric("Intake", round(df['INTAKE_MARGIN'].sum(),2))
    c5.metric("Margin", round(df['MARGIN'].sum(),2))
    c6.metric("Margin %", round(df['MARGIN_PCT'].mean(),2))
    c7.metric("ASP", round(df['ASP'].mean(),2))
    c8.metric("Markdown", round(df['CURR_MD'].mean(),2))

    c9,c10,c11,c12,c13,c14 = st.columns(6)

    c9.metric("ROS", round(df['ROS'].mean(),2))
    c10.metric("Cover", round(df['COVER'].mean(),2))
    c11.metric("Sell Through", round(df['SELL_THROUGH'].mean(),2))
    c12.metric("OOS %", round(df['OOS_PCT'].mean(),2))
    c13.metric("Stock/Sales", round(df['STOCK_TO_SALES'].mean(),2))
    c14.metric("GMROI", round(df['GMROI'].mean(),2))

    # KPI TABLE
    st.subheader("📋 KPI Breakdown")

    level = st.selectbox("Level", levels)

    kpi = df.groupby(level).agg({
        'REVENUE':'sum',
        'SALES_QTY':'sum',
        'MARGIN':'sum',
        'ROS':'mean',
        'COVER':'mean'
    }).reset_index()

    st.dataframe(kpi, use_container_width=True)

    # DECISION MAP
    st.subheader("📍 Stock vs Demand")

    fig = px.scatter(
        df.sample(min(len(df), 5000)),
        x='COVER',
        y='SELL_THROUGH',
        color='Department',
        render_mode='svg'
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# ================= TAB 2 : INSIGHTS =======================
# =========================================================
with tab2:

    st.title("🧠 Insights")

    # ALERTS
    df['ALERT'] = np.select(
        [
            (df['SELL_THROUGH'] < 0.3) & (df['COVER'] > 16),
            (df['SELL_THROUGH'] > 0.6) & (df['COVER'] < 12),
            (df['SOH_QTY'] == 0)
        ],
        ["Overstock","Stockout","No Stock"],
        default="Healthy"
    )

    st.subheader("🚨 Alerts")
    st.bar_chart(df['ALERT'].value_counts())

    # ================= PERFORMANCE GRID =================
    st.subheader("📊 Performance Grid (Click → SKU)")

    perf = df.groupby('Sub Class').agg({
        'CURR_MD':'mean',
        'SELL_THROUGH':'mean',
        'REVENUE':'sum'
    }).reset_index().dropna()

    md = perf['CURR_MD'].median()
    st_ = perf['SELL_THROUGH'].median()

    def bucket(r):
        if r['CURR_MD'] >= md and r['SELL_THROUGH'] >= st_:
            return "Reduce MKD"
        elif r['SELL_THROUGH'] >= st_:
            return "Best"
        elif r['CURR_MD'] >= md:
            return "Fix"
        else:
            return "Increase MKD"

    perf['Bucket'] = perf.apply(bucket, axis=1)

    fig = px.scatter(
        perf,
        x='CURR_MD',
        y='SELL_THROUGH',
        color='Bucket',
        size='REVENUE',
        text='Sub Class',
        render_mode='svg'
    )

    fig.add_vline(x=md)
    fig.add_hline(y=st_)

    st.plotly_chart(fig, use_container_width=True)

    # ================= DRILL-DOWN =================
    st.markdown("### 🔍 Drill into Subclass")

    selected_subclass = st.selectbox(
        "Select Sub Class",
        ["All"] + sorted(perf['Sub Class'].unique())
    )

    if selected_subclass != "All":

        sku_df = df[df['Sub Class'] == selected_subclass]

        st.subheader(f"📦 SKU Details — {selected_subclass}")

        sku_table = sku_df.groupby('ITM_CD').agg({
            'REVENUE':'sum',
            'SALES_QTY':'sum',
            'SOH_QTY':'sum',
            'MARGIN':'sum',
            'CURR_MD':'mean',
            'SELL_THROUGH':'mean',
            'ROS':'mean',
            'COVER':'mean'
        }).reset_index()

        st.dataframe(sku_table, use_container_width=True)

        st.subheader("🏆 Top SKUs")
        st.dataframe(sku_table.sort_values('REVENUE', ascending=False).head(10))

        st.subheader("⚠️ Low Performers")
        st.dataframe(sku_table.sort_values('SELL_THROUGH').head(10))

# =========================================================
# ================= TAB 3 : TRENDS =========================
# =========================================================
with tab3:

    st.title("📈 Trends")

    period = st.selectbox("Period", ["Weekly","Monthly","Quarterly","Yearly"])

    if period == "Monthly":
        df['TIME'] = df['TRDNG_WK_END_DT'].dt.to_period('M').astype(str)
    elif period == "Quarterly":
        df['TIME'] = df['TRDNG_WK_END_DT'].dt.to_period('Q').astype(str)
    elif period == "Yearly":
        df['TIME'] = df['TRDNG_WK_END_DT'].dt.to_period('Y').astype(str)
    else:
        df['TIME'] = df['TRDNG_WK_END_DT']

    metric = st.selectbox("Metric", ['REVENUE','ROS','SELL_THROUGH','CURR_MD','COVER'])

    trend = df.groupby('TIME')[metric].mean().reset_index()

    fig = px.line(trend, x='TIME', y=metric)

    st.plotly_chart(fig, use_container_width=True)

# ================= EXPORT =================
st.sidebar.subheader("📤 Export")

output = io.BytesIO()
df.to_excel(output, index=False)

st.sidebar.download_button("Download Report", output.getvalue(), "report.xlsx")
