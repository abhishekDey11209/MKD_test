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
def get_kpi_trend(df, col):
    df_sorted = df.sort_values('TRDNG_WK_END_DT')
    trend = df_sorted.groupby('TRDNG_WK_END_DT')[col].sum()

    current = trend.iloc[-1]
    previous = trend.iloc[-2] if len(trend) > 1 else current

    change = ((current - previous) / previous * 100) if previous != 0 else 0
    arrow = "↑" if change > 0 else "↓"
    color = "green" if change > 0 else "red"

    return current, change, arrow, color, trend.tail(20)

def smart_kpi_card(title, col_name):
    value, change, arrow, color, trend = get_kpi_trend(df, col_name)

    st.markdown(f"""
    <div style="background:#1c1f26;padding:12px;border-radius:12px;">
        <div>{title}</div>
        <div style="font-size:20px;font-weight:bold;">{round(value,2)}</div>
        <div style="color:{color}">{arrow} {round(change,2)}%</div>
    </div>
    """, unsafe_allow_html=True)

    fig = px.line(trend)
    fig.update_layout(height=60, margin=dict(l=0,r=0,t=0,b=0),
                      xaxis_visible=False, yaxis_visible=False)

    st.plotly_chart(fig, use_container_width=True)

# ================= KPI CARDS =================
st.markdown("## 📊 Performance & Insights")

cols = st.columns(6)
kpis = [
    ("Revenue","REVENUE"),
    ("Sales Qty","SALES_QTY"),
    ("SOH","SOH_QTY"),
    ("Margin","MARGIN"),
    ("ROS","ROS"),
    ("Cover","COVER"),
]

for col, (title, kpi) in zip(cols, kpis):
    with col:
        smart_kpi_card(title, kpi)

# ================= KPI BREAKDOWN =================
st.markdown("## 📋 KPI Breakdown")

level = st.selectbox("Select Level", levels)

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

# ================= DONUT =================
st.markdown("## 🍩 KPI Comparison")

kpi_map = {
    "Revenue":"REVENUE",
    "Quantity":"SALES_QTY",
    "Margin":"MARGIN",
    "ROS":"ROS",
    "Cover":"COVER",
    "Sell Through":"SELL_THROUGH"
}

kpi_selected = st.selectbox("Select KPI", list(kpi_map.keys()))
kpi_col = kpi_map[kpi_selected]

period = st.selectbox("Period Type", ["Weekly","Monthly","Quarterly","Yearly"])
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
    "Period":["Current","Previous"],
    "Value":[current,previous]
})

col1, col2 = st.columns(2)

with col1:
    fig = px.pie(donut_df, names='Period', values='Value', hole=0.6)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    change = ((current-previous)/previous*100) if previous!=0 else 0
    st.metric("Change %", round(change,2))

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
