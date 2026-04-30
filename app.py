import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
from backend import process_data

st.set_page_config(layout="wide")

# ================= LOAD =================
@st.cache_data
def load():
    return pd.read_excel("demo.xlsx", engine="openpyxl")

df = process_data(load())

# ================= FILTERS =================
st.sidebar.title("Filters")

cols = ["STND_TRRTRY_NM","Group","Department","Class","Sub Class"]

for c in cols:
    selected = st.sidebar.multiselect(c, df[c].unique(), df[c].unique())
    df = df[df[c].isin(selected)]

# ================= PLAYCARDS =================
st.title("📊 Retail Dashboard")

k1,k2,k3,k4,k5,k6,k7,k8 = st.columns(8)

k1.metric("Revenue", round(df['REVENUE'].sum(),2))
k2.metric("Qty Sold", round(df['SALES_QTY'].sum(),2))
k3.metric("Current SOH", round(df['SOH_QTY'].sum(),2))
k4.metric("Intake Margin", round(df['INTAKE_MARGIN'].sum(),2))
k5.metric("Margin", round(df['MARGIN'].sum(),2))
k6.metric("Margin %", round(df['MARGIN_PCT'].mean(),2))
k7.metric("ASP", round(df['ASP'].mean(),2))
k8.metric("Markdown", round(df['CURR_MD'].mean(),2))

k9,k10,k11,k12,k13,k14 = st.columns(6)

k9.metric("ROS", round(df['ROS'].mean(),2))
k10.metric("Cover", round(df['COVER'].mean(),2))
k11.metric("Sell Through", round(df['SELL_THROUGH'].mean(),2))
k12.metric("OOS %", round(df['OOS_PCT'].mean(),2))
k13.metric("Stock/Sales", round(df['STOCK_TO_SALES'].mean(),2))
k14.metric("GMROI", round(df['GMROI'].mean(),2))

# ================= KPI TABLE =================
st.subheader("📋 KPI Table")

level = st.selectbox("Select Level", cols)

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

st.dataframe(kpi)

# ================= PERFORMANCE GRID =================
st.subheader("📊 Performance Grid (Markdown vs Sell-through)")

perf_df = df.groupby('Sub Class').agg({
    'CURR_MD': 'mean',
    'SELL_THROUGH': 'mean',
    'REVENUE': 'sum'
}).reset_index()

md_threshold = perf_df['CURR_MD'].median()
st_threshold = perf_df['SELL_THROUGH'].median()

def perf_bucket(row):
    if row['CURR_MD'] >= md_threshold and row['SELL_THROUGH'] >= st_threshold:
        return "Reduce MKD 🔻"
    elif row['CURR_MD'] < md_threshold and row['SELL_THROUGH'] >= st_threshold:
        return "Best Performer 🚀"
    elif row['CURR_MD'] >= md_threshold and row['SELL_THROUGH'] < st_threshold:
        return "Fix Strategy ⚠️"
    else:
        return "Increase MKD 📈"

perf_df['PERFORMANCE'] = perf_df.apply(perf_bucket, axis=1)

fig_perf = px.scatter(
    perf_df,
    x='CURR_MD',
    y='SELL_THROUGH',
    color='PERFORMANCE',
    size='REVENUE',
    text='Sub Class',
    render_mode='svg'
)

fig_perf.add_vline(x=md_threshold, line_dash="dash")
fig_perf.add_hline(y=st_threshold, line_dash="dash")

fig_perf.update_traces(textposition='top center')

st.plotly_chart(fig_perf, use_container_width=True)

# ================= DECISION MAP =================
st.subheader("📍 Stock vs Demand")

df_plot = df.sample(min(len(df), 5000))

fig = px.scatter(
    df_plot,
    x='COVER',
    y='SELL_THROUGH',
    color='Department',
    render_mode='svg'
)

st.plotly_chart(fig, use_container_width=True)

# ================= TREND =================
st.subheader("📈 Trends")

period = st.selectbox("Period", ["Weekly","Monthly","Quarterly","Yearly"])

if period == "Monthly":
    df['TIME'] = df['TRDNG_WK_END_DT'].dt.to_period('M').astype(str)
elif period == "Quarterly":
    df['TIME'] = df['TRDNG_WK_END_DT'].dt.to_period('Q').astype(str)
elif period == "Yearly":
    df['TIME'] = df['TRDNG_WK_END_DT'].dt.to_period('Y').astype(str)
else:
    df['TIME'] = df['TRDNG_WK_END_DT']

metric = st.selectbox("Trend Metric", ['REVENUE','ROS','SELL_THROUGH','CURR_MD','COVER'])

trend = df.groupby('TIME')[metric].mean().reset_index()

fig_trend = px.line(trend, x='TIME', y=metric)
st.plotly_chart(fig_trend)

# ================= EXPORT =================
st.subheader("📤 Export")

output = io.BytesIO()

with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Data', index=False)
    kpi.to_excel(writer, sheet_name='KPI', index=False)

st.download_button("Download Report", data=output.getvalue(), file_name="report.xlsx")
