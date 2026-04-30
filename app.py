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

# ================= KPI FUNCTIONS =================
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

cols1 = st.columns(6)
kpis1 = [
    ("Revenue","REVENUE"),
    ("Sales Qty","SALES_QTY"),
    ("Current SOH","SOH_QTY"),
    ("Margin","MARGIN"),
    ("ROS","ROS"),
    ("Sell Through","SELL_THROUGH"),
]

for col, (title, kpi) in zip(cols1, kpis1):
    with col:
        smart_kpi_card(title, kpi)

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Insights", "📈 Trends"])

# =========================================================
# ================= OVERVIEW ===============================
# =========================================================
with tab1:

    # KPI Breakdown
    st.markdown("## 📋 KPI Breakdown by Level")

    level = st.selectbox(
        "Select Level",
        levels,
        key="level_select"
    )

    kpi_table = df.groupby(level).agg({
        'REVENUE':'sum',
        'SALES_QTY':'sum',
        'SOH_QTY':'sum',
        'MARGIN':'sum',
        'ROS':'mean',
        'COVER':'mean',
        'SELL_THROUGH':'mean'
    }).reset_index()

    st.dataframe(kpi_table, use_container_width=True)

    # KPI Comparison
    st.markdown("## 🍩 KPI Comparison")

    kpi_map = {
        "Revenue":"REVENUE",
        "Quantity":"SALES_QTY",
        "Margin":"MARGIN",
        "ROS":"ROS",
        "Cover":"COVER",
        "Sell Through":"SELL_THROUGH"
    }

    col1, col2 = st.columns(2)

    with col1:
        kpi_selected = st.selectbox("Select KPI", list(kpi_map.keys()), key="kpi_sel")
        kpi_col = kpi_map[kpi_selected]

    with col2:
        period = st.selectbox("Period Type", ["Weekly","Monthly","Quarterly","Yearly"], key="period_sel")

    n_periods = st.slider("Periods", 1, 12, 4)

    df_sorted = df.sort_values('TRDNG_WK_END_DT').copy()

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
        "Period":["Current","Previous"],
        "Value":[current,previous]
    })

    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(donut_df, names='Period', values='Value', hole=0.6)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        change = ((current-previous)/previous*100) if previous!=0 else 0
        st.metric("Change %", f"{round(change,2)}%")

    # Stock vs Demand (FIXED WebGL)
    st.markdown("## 📍 Stock vs Demand")

    df_sample = df.sample(min(len(df), 5000))

    fig2 = px.scatter(
        df_sample,
        x='COVER',
        y='SELL_THROUGH',
        color='Department',
        render_mode='svg'   # ✅ FIX
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
        ["Overstock Risk","Stockout Risk","No Stock"],
        default="Healthy"
    )

    st.bar_chart(df['ALERT'].value_counts())

    # Performance Bucket
    st.markdown("## 📊 Performance Bucket")

    perf = df.groupby('Sub Class').agg({
        'CURR_MD':'mean',
        'SELL_THROUGH':'mean',
        'REVENUE':'sum'
    }).reset_index().dropna()

    md = perf['CURR_MD'].median()
    st_ = perf['SELL_THROUGH'].median()

    def bucket(row):
        if row['CURR_MD'] > md and row['SELL_THROUGH'] > st_:
            return "Reduce MKD"
        elif row['SELL_THROUGH'] > st_:
            return "Best Performer"
        elif row['CURR_MD'] > md:
            return "Fix Strategy"
        else:
            return "Increase MKD"

    perf['Bucket'] = perf.apply(bucket, axis=1)

    fig_perf = px.scatter(
        perf,
        x='CURR_MD',
        y='SELL_THROUGH',
        color='Bucket',
        size='REVENUE',
        text='Sub Class',
        render_mode='svg'   # ✅ FIX
    )

    fig_perf.add_vline(x=md)
    fig_perf.add_hline(y=st_)

    st.plotly_chart(fig_perf, use_container_width=True)

# =========================================================
# ================= TRENDS ================================
# =========================================================
with tab3:

    st.markdown("## 📈 Trend Analysis")

    col1, col2 = st.columns(2)

    with col1:
        trend_period = st.selectbox("Trend Period", ["Weekly","Monthly","Quarterly","Yearly"], key="trend_period")

    with col2:
        metric = st.selectbox("Metric", ['REVENUE','ROS','SELL_THROUGH','CURR_MD','COVER'], key="trend_metric")

    df_trend = df.copy()

    if trend_period == "Monthly":
        df_trend['TIME'] = df_trend['TRDNG_WK_END_DT'].dt.to_period('M').astype(str)
    elif trend_period == "Quarterly":
        df_trend['TIME'] = df_trend['TRDNG_WK_END_DT'].dt.to_period('Q').astype(str)
    elif trend_period == "Yearly":
        df_trend['TIME'] = df_trend['TRDNG_WK_END_DT'].dt.to_period('Y').astype(str)
    else:
        df_trend['TIME'] = df_trend['TRDNG_WK_END_DT']

    trend = df_trend.groupby('TIME')[metric].mean().reset_index()

    fig = px.line(trend, x='TIME', y=metric)
    st.plotly_chart(fig, use_container_width=True)

# ================= EXPORT =================
st.sidebar.subheader("📤 Export")

output = io.BytesIO()
df.to_excel(output, index=False)

st.sidebar.download_button("Download Report", output.getvalue(), "report.xlsx")
