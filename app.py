import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
from backend import process_data

st.set_page_config(layout="wide")

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
# ================= KPI SECTION =================
st.markdown("## 📊 Performance & Insights")

# -------- KPI LIST --------
kpis = [
    ("Revenue","REVENUE"),
    ("Sold Qty","SALES_QTY"),
    ("Current SOH","SOH_QTY"),
    ("Intake Margin","INTAKE_MARGIN"),
    ("Margin","MARGIN"),
    ("Margin %","MARGIN_PCT"),
    ("ASP","ASP"),
    ("Markdown","CURR_MD"),
    ("ROS","ROS"),
    ("Cover","COVER"),
    ("Sell Through","SELL_THROUGH"),
    ("OOS %","OOS_PCT"),
    ("Stock to Sales","STOCK_TO_SALES"),
    ("GMROI","GMROI")
]

# -------- GRID DISPLAY (AUTO WRAP) --------
cols = st.columns(7)

for i, (title, col_name) in enumerate(kpis):
    with cols[i % 7]:
        smart_kpi_card(title, col_name)


# ================= AUTO INSIGHTS =================
st.markdown("## 🧠 Auto Insights")

insights = []

# Aggregate properly
dept_perf = df.groupby('Department').agg({
    'REVENUE':'sum',
    'ROS':'mean',
    'COVER':'mean',
    'SELL_THROUGH':'mean'
}).reset_index()

# Benchmarks
ros_med = dept_perf['ROS'].median()
cover_med = dept_perf['COVER'].median()
rev_mean = dept_perf['REVENUE'].mean()

# ---- Insight Logic ----

# 1. Low ROS
low_ros = dept_perf.nsmallest(3, 'ROS')
for _, row in low_ros.iterrows():
    insights.append(
        f"🔻 {row['Department']} has low ROS ({round(row['ROS'],2)}) → weak demand"
    )

# 2. High Cover
high_cover = dept_perf.nlargest(3, 'COVER')
for _, row in high_cover.iterrows():
    insights.append(
        f"⚠️ {row['Department']} has high Cover ({round(row['COVER'],1)} weeks) → overstock risk"
    )

# 3. Declining Logic (SMART)
for _, row in dept_perf.iterrows():
    if (row['ROS'] < ros_med) and (row['COVER'] > cover_med):
        insights.append(
            f"🔻 {row['Department']} declining due to low ROS + high inventory"
        )

# 4. Star Performers
top_perf = dept_perf.nlargest(3, 'SELL_THROUGH')
for _, row in top_perf.iterrows():
    insights.append(
        f"🚀 {row['Department']} strong performer (Sell Through {round(row['SELL_THROUGH'],2)})"
    )

# 5. Revenue Drivers
top_rev = dept_perf.nlargest(2, 'REVENUE')
for _, row in top_rev.iterrows():
    insights.append(
        f"💰 {row['Department']} driving revenue ({round(row['REVENUE'],0)})"
    )

# -------- DISPLAY --------
if insights:
    for i in insights[:6]:
        st.markdown(f"- {i}")
else:
    st.success("All departments are performing well 🚀")
# ================= ALERTS =================
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

# ================= PERFORMANCE GRID =================
st.markdown("## 📊 Performance Grid")

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
    render_mode='svg'
)

fig_perf.add_vline(x=md)
fig_perf.add_hline(y=st_)

st.plotly_chart(fig_perf, use_container_width=True)

# ================= STOCK VS DEMAND =================
st.markdown("## 📍 Stock vs Demand")

fig2 = px.scatter(
    df.sample(min(len(df),5000)),
    x='COVER',
    y='SELL_THROUGH',
    color='Department',
    render_mode='svg'
)

st.plotly_chart(fig2, use_container_width=True)

# ================= TREND =================
st.markdown("## 📈 Trend Analysis")

metric = st.selectbox("Metric", ['REVENUE','ROS','SELL_THROUGH','CURR_MD','COVER'])

trend = df.groupby('TRDNG_WK_END_DT')[metric].mean().reset_index()

fig = px.line(trend, x='TRDNG_WK_END_DT', y=metric)
st.plotly_chart(fig, use_container_width=True)

# ================= EXPORT =================
st.sidebar.subheader("📤 Export")

output = io.BytesIO()
df.to_excel(output, index=False)

st.sidebar.download_button("Download Report", output.getvalue(), "report.xlsx")
