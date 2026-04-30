import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
from backend import process_data

st.set_page_config(layout="wide")

# ================= HEADER =================
st.markdown("""
<div style="background: linear-gradient(90deg, #1f77b4, #2ca02c);
padding: 20px;border-radius: 12px;color: white;text-align: center;
font-size: 28px;font-weight: bold;">
📊 RETAIL SALES OVERVIEW
</div><br>
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
    trend = df.sort_values('TRDNG_WK_END_DT').groupby('TRDNG_WK_END_DT')[col].sum()
    current = trend.iloc[-1]
    previous = trend.iloc[-2] if len(trend) > 1 else current
    change = ((current - previous) / previous * 100) if previous != 0 else 0
    arrow = "↑" if change > 0 else "↓"
    color = "#2f9e44" if change > 0 else "#fa5252"
    return current, change, arrow, color, trend.tail(20)

def smart_kpi_card(title, col_name):
    value, change, arrow, color, trend = get_kpi_trend(df, col_name)

    st.markdown(f"""
    <div style="background:#1c1f26;padding:12px;border-radius:12px;color:white;">
        <div>{title}</div>
        <div style="font-size:20px;font-weight:bold;">{round(value,2)}</div>
        <div style="color:{color}">{arrow} {round(change,2)}%</div>
    </div>
    """, unsafe_allow_html=True)

    fig = px.line(trend)
    fig.update_layout(height=60, margin=dict(l=0,r=0,t=0,b=0),
                      xaxis_visible=False, yaxis_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Insights", "📈 Trends"])

# ================= TAB 1 =================
with tab1:

    st.markdown("## 📊 Performance & Insights")

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

    cols3 = st.columns(2)
    kpis3 = [
        ("Stock to Sales","STOCK_TO_SALES"),
        ("GMROI","GMROI"),
    ]
    for col, (title, kpi) in zip(cols3, kpis3):
        with col:
            smart_kpi_card(title, kpi)

# ================= TAB 2 =================
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

    # AUTO INSIGHTS
    st.markdown("## 🧠 Auto Insights")

    dept_perf = df.groupby('Department').agg({
        'REVENUE':'sum',
        'ROS':'mean',
        'COVER':'mean',
        'SELL_THROUGH':'mean'
    }).reset_index()

    insights = []

    for _, row in dept_perf.nsmallest(3, 'ROS').iterrows():
        insights.append(f"🔻 {row['Department']} low ROS")

    for _, row in dept_perf.nlargest(3, 'COVER').iterrows():
        insights.append(f"⚠️ {row['Department']} high Cover")

    for i in insights[:6]:
        st.markdown(f"- {i}")

    # ================= PERFORMANCE GRID (FIXED) =================
    st.markdown("## 📊 Performance Grid")

    perf = df.groupby('Sub Class').agg({
        'CURR_MD':'mean',
        'SELL_THROUGH':'mean',
        'REVENUE':'sum'
    }).reset_index()

    perf = perf.replace([np.inf, -np.inf], np.nan).dropna()

    if len(perf) > 0:
        fig_perf = px.scatter(
            perf,
            x='CURR_MD',
            y='SELL_THROUGH',
            size='REVENUE',
            text='Sub Class',
            render_mode='svg'
        )
        st.plotly_chart(fig_perf, use_container_width=True)

# ================= TAB 3 =================
with tab3:

    st.markdown("## 📈 Trends")

    metric = st.selectbox("Metric", ['REVENUE','ROS','SELL_THROUGH','CURR_MD','COVER'])

    trend = df.groupby('TRDNG_WK_END_DT')[metric].mean().reset_index()

    st.plotly_chart(px.line(trend, x='TRDNG_WK_END_DT', y=metric),
                    use_container_width=True)

# ================= EXPORT =================
st.sidebar.subheader("📤 Export")

output = io.BytesIO()
df.to_excel(output, index=False)

st.sidebar.download_button("Download Report", output.getvalue(), "report.xlsx")
