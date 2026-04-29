import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

from backend import process_data, calculate_mix

st.set_page_config(layout="wide")

# LOAD
@st.cache_data
def load():
    return pd.read_excel("demo.xlsx")

df = process_data(load())

# FILTERS
st.sidebar.title("Filters")

dept = st.sidebar.multiselect("Department", df['Department'].unique(), df['Department'].unique())
store = st.sidebar.multiselect("Store", df['LOC_CD'].unique(), df['LOC_CD'].unique())
item = st.sidebar.multiselect("Item", df['ITM_CD'].unique(), df['ITM_CD'].unique())

df = df[
    (df['Department'].isin(dept)) &
    (df['LOC_CD'].isin(store)) &
    (df['ITM_CD'].isin(item))
]

# KPI
st.title("Retail Dashboard")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Revenue", round(df['REVENUE'].sum(), 2))
c2.metric("Margin", round(df['MARGIN'].sum(), 2))
c3.metric("ROS", round(df['ROS'].mean(), 2))
c4.metric("Cover", round(df['COVER'].mean(), 2))

# TRENDS
st.subheader("Trends")

sales = df.groupby('TRDNG_WK_END_DT')['REVENUE'].sum()
ros = df.groupby('TRDNG_WK_END_DT')['ROS'].mean()
cover = df.groupby('TRDNG_WK_END_DT')['COVER'].mean()

st.line_chart(sales)
st.line_chart(ros)
st.line_chart(cover)

# MIX
st.subheader("Mix")
mix = calculate_mix(df)
st.dataframe(mix)

# ELASTICITY
st.subheader("Elasticity")
st.metric("Avg Elasticity", round(df['ELASTICITY'].mean(), 2))

# SIMULATION
st.subheader("Markdown Simulation")

md = st.slider("Markdown %", 0.0, 0.8, 0.2)

elasticity = df['ELASTICITY'].mean()

if pd.notna(elasticity):
    base_qty = df['SALES_QTY'].mean()
    new_qty = base_qty * (1 + elasticity * md)

    price = df['REG_RTL_AED'].mean() * (1 - md)
    revenue = new_qty * price

    st.metric("Predicted Revenue", round(revenue, 2))

# EXPORT
st.subheader("Export Report")

output = io.BytesIO()

with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Data', index=False)
    mix.to_excel(writer, sheet_name='Mix', index=False)

st.download_button(
    "Download Report",
    data=output.getvalue(),
    file_name="retail_report.xlsx"
)
