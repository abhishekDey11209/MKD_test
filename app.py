import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
from backend import process_data

st.set_page_config(layout="wide")

# ================= GLOBAL CSS =================
st.markdown("""
<style>

/* Background */
body {
    background-color: #0e1117;
}

/* Header */
.header {
    background: linear-gradient(90deg, #1f77b4, #2ca02c);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    color: white;
    font-size: 28px;
    font-weight: bold;
    animation: fadeIn 1s ease-in;
}

/* KPI Cards */
.kpi-card {
    padding: 15px;
    border-radius: 15px;
    color: white;
    text-align: center;
    transition: 0.3s;
    animation: fadeUp 0.8s ease;
}

.kpi-card:hover {
    transform: translateY(-8px) scale(1.03);
    box-shadow: 0px 10px 25px rgba(0,0,0,0.5);
}

/* Card Container */
.card {
    background: #1c1f26;
    padding: 15px;
    border-radius: 15px;
    margin-top: 10px;
    animation: fadeUp 0.8s ease;
}

/* Animations */
@keyframes fadeUp {
    from { opacity:0; transform: translateY(20px);}
    to { opacity:1; transform: translateY(0);}
}

@keyframes fadeIn {
    from { opacity:0;}
    to { opacity:1;}
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(#1f77b4, #2ca02c);
    color: white;
}

</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown('<div class="header">📊 RETAIL SALES OVERVIEW</div>', unsafe_allow_html=True)

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
    <div class="kpi-card" style="background:{color}">
        <div style="font-size:14px;">{title}</div>
        <div style="font-size:22px;">{value}</div>
    </div>
    """

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Insights", "📈 Trends"])

# =========================================================
# ================= OVERVIEW ===============================
# =========================================================
with tab1:

    st.markdown("### KPI Summary")

    kpi_html = f"""
    <div style="display:flex; gap:10px;">
        {kpi_card("Revenue", round(df['REVENUE'].sum(),2), "#ff6b6b")}
        {kpi_card("Qty", round(df['SALES_QTY'].sum(),2), "#51cf66")}
        {kpi_card("Margin", round(df['MARGIN'].sum(),2), "#845ef7")}
        {kpi_card("ROS", round(df['ROS'].mean(),2), "#fcc419")}
        {kpi_card("Cover", round(df['COVER'].mean(),2), "#339af0")}
        {kpi_card("Sell Through", round(df['SELL_THROUGH'].mean(),2), "#20c997")}
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # KPI TABLE
    st.markdown('<div class="card">', unsafe_allow_html=True)

    level = st.selectbox("Breakdown Level", levels)

    kpi = df.groupby(level).agg({
        'REVENUE':'sum',
        'SALES_QTY':'sum',
        'MARGIN':'sum',
        'ROS':'mean',
        'COVER':'mean'
    }).reset_index()

    st.dataframe(kpi, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # DONUT
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.subheader("🍩 KPI Comparison")

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

    st.markdown('</div>', unsafe_allow_html=True)

    # DECISION MAP
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.subheader("📍 Stock vs Demand")

    fig2 = px.scatter(
        df.sample(min(len(df),5000)),
        x='COVER',
        y='SELL_THROUGH',
        color='Department',
        render_mode='svg'
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# ================= INSIGHTS ===============================
# =========================================================
with tab2:

    st.markdown("### Alerts")

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

    # PERFORMANCE GRID
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.subheader("📊 Performance Grid")

    perf = df.groupby('Sub Class').agg({
        'CURR_MD':'mean',
        'SELL_THROUGH':'mean',
        'REVENUE':'sum'
    }).reset_index().dropna()

    md = perf['CURR_MD'].median()
    st_ = perf['SELL_THROUGH'].median()

    perf['Bucket'] = np.where(
        (perf['CURR_MD'] > md) & (perf['SELL_THROUGH'] > st_), "Reduce MKD",
        np.where(perf['SELL_THROUGH'] > st_, "Best",
        np.where(perf['CURR_MD'] > md, "Fix", "Increase MKD"))
    )

    fig3 = px.scatter(
        perf,
        x='CURR_MD',
        y='SELL_THROUGH',
        color='Bucket',
        size='REVENUE',
        text='Sub Class',
        render_mode='svg'
    )

    fig3.add_vline(x=md)
    fig3.add_hline(y=st_)

    st.plotly_chart(fig3, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # DRILL DOWN
    st.subheader("🔍 Drill to SKU")

    subclass = st.selectbox("Select Subclass", ["All"] + list(perf['Sub Class']))

    if subclass != "All":
        sku = df[df['Sub Class'] == subclass]

        table = sku.groupby('ITM_CD').agg({
            'REVENUE':'sum',
            'SALES_QTY':'sum',
            'MARGIN':'sum'
        }).reset_index()

        st.dataframe(table, use_container_width=True)

# =========================================================
# ================= TRENDS ================================
# =========================================================
with tab3:

    st.subheader("📈 Trends")

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
