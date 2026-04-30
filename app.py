import streamlit as st
import pandas as pd
import plotly.express as px
from backend import process_data, generate_insights

st.set_page_config(layout="wide")

# LOAD
@st.cache_data
def load():
    return pd.read_excel("demo.xlsx", engine="openpyxl")

df = process_data(load())

# ================= DRILL-DOWN =================
st.sidebar.title("Drill-down")

level1 = st.sidebar.selectbox("Territory", ["All"] + list(df['STND_TRRTRY_NM'].unique()))
if level1 != "All":
    df = df[df['STND_TRRTRY_NM'] == level1]

level2 = st.sidebar.selectbox("Group", ["All"] + list(df['Group'].unique()))
if level2 != "All":
    df = df[df['Group'] == level2]

level3 = st.sidebar.selectbox("Department", ["All"] + list(df['Department'].unique()))
if level3 != "All":
    df = df[df['Department'] == level3]

level4 = st.sidebar.selectbox("Class", ["All"] + list(df['Class'].unique()))
if level4 != "All":
    df = df[df['Class'] == level4]

level5 = st.sidebar.selectbox("Sub Class", ["All"] + list(df['Sub Class'].unique()))
if level5 != "All":
    df = df[df['Sub Class'] == level5]

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Trends", "🧠 Insights"])

# ================= TAB 1 =================
with tab1:

    st.title("Overview Dashboard")

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Revenue", round(df['REVENUE'].sum(),2))
    c2.metric("Margin", round(df['MARGIN'].sum(),2))
    c3.metric("ROS", round(df['ROS'].mean(),2))
    c4.metric("Cover", round(df['COVER'].mean(),2))

    st.subheader("Stock vs Demand")

    fig = px.scatter(df, x='COVER', y='SELL_THROUGH', color='Department')
    st.plotly_chart(fig, use_container_width=True)

# ================= TAB 2 =================
with tab2:

    st.title("Trend Analysis")

    period = st.selectbox("Period", ["Weekly","Monthly","Yearly"])

    if period == "Monthly":
        df['TIME'] = df['TRDNG_WK_END_DT'].dt.to_period('M').astype(str)
    elif period == "Yearly":
        df['TIME'] = df['TRDNG_WK_END_DT'].dt.to_period('Y').astype(str)
    else:
        df['TIME'] = df['TRDNG_WK_END_DT']

    metric = st.selectbox("Metric", ['REVENUE','ROS','SELL_THROUGH','CURR_MD','COVER'])

    trend = df.groupby('TIME')[metric].mean().reset_index()

    fig = px.line(trend, x='TIME', y=metric)
    st.plotly_chart(fig, use_container_width=True)

# ================= TAB 3 =================
with tab3:

    st.title("Auto Insights")

    insights = generate_insights(df)

    for i in insights:
        st.success(i)

    st.subheader("Top Issues")

    issue_df = df[(df['SELL_THROUGH'] < 0.3) | (df['COVER'] > 16)]
    st.dataframe(issue_df.head(20))
