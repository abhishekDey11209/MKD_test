import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io

st.set_page_config(layout="wide")

# ================= LOAD =================
@st.cache_data
def load_data():
    df = pd.read_excel("demo.xlsx", engine="openpyxl")
    df['TRDNG_WK_END_DT'] = pd.to_datetime(df['TRDNG_WK_END_DT'])
    df['LST_GRN_DT'] = pd.to_datetime(df['LST_GRN_DT'])
    return df.fillna(0)

df = load_data()

# ================= KPI ENGINE =================
# Age / lifecycle
df['AGE_DAYS'] = (df['TRDNG_WK_END_DT'] - df['LST_GRN_DT']).dt.days
df['AGE_WEEKS'] = df['AGE_DAYS'] / 7
df['LIFECYCLE_PCT'] = df['AGE_WEEKS'] / 16

# Stock
df['TOTAL_STOCK'] = df['SOH_QTY'] + df['IN_TRNST_QTY']

# Sales
df['REVENUE'] = df['NET_SLS_AMT_AED']
df['SALES_QTY'] = df['RTL_QTY']
df['ASP'] = df['REVENUE'] / df['SALES_QTY'].replace(0, np.nan)

# Margin
df['MARGIN'] = df['REVENUE'] - df['COST_AED']

# Sell-through
df['SELL_THROUGH'] = np.where(
    (df['SALES_QTY'] + df['SOH_QTY']) > 0,
    df['SALES_QTY'] / (df['SALES_QTY'] + df['SOH_QTY']),
    0
)

# ROS (corrected)
weeks_traded = (
    df[df['SALES_QTY'] > 0]
    .groupby(['ITM_CD', 'LOC_CD'])['TRDNG_WK_END_DT']
    .nunique()
    .reset_index()
    .rename(columns={'TRDNG_WK_END_DT': 'WEEKS_TRADED'})
)

df = df.merge(weeks_traded, on=['ITM_CD', 'LOC_CD'], how='left')
df['WEEKS_TRADED'] = df['WEEKS_TRADED'].fillna(0)
df['EFFECTIVE_WEEKS'] = df[['AGE_WEEKS', 'WEEKS_TRADED']].min(axis=1)
df['ROS'] = df['SALES_QTY'] / df['EFFECTIVE_WEEKS'].replace(0, np.nan)

# Cover (weeks)
df['COVER'] = df['TOTAL_STOCK'] / df['ROS'].replace(0, np.nan)

# Price / Markdown
df['PRICE'] = df['REVENUE'] / df['SALES_QTY'].replace(0, np.nan)
df['CURR_MD'] = 1 - (df['REVENUE'] / df['REG_RTL_AED'].replace(0, np.nan))
df['CURR_MD'] = df['CURR_MD'].clip(0, 1)

# ================= ELASTICITY (per SKU-store) =================
df['LOG_QTY'] = np.log(df['SALES_QTY'].replace(0, np.nan))
df['LOG_PRICE'] = np.log(df['PRICE'])

def calc_elasticity(group):
    g = group.dropna(subset=['LOG_QTY', 'LOG_PRICE'])
    if len(g) < 3:
        return np.nan
    return np.polyfit(g['LOG_PRICE'], g['LOG_QTY'], 1)[0]

elasticity_df = (
    df.groupby(['ITM_CD', 'LOC_CD'])
    .apply(calc_elasticity)
    .reset_index()
    .rename(columns={0: 'ELASTICITY'})
)

df = df.merge(elasticity_df, on=['ITM_CD', 'LOC_CD'], how='left')

def elasticity_type(e):
    if pd.isna(e): return "No Data"
    if e > 0: return "Positive ⚠️"
    if e < -2: return "Highly Elastic 🔥"
    if e < -1: return "Elastic"
    if e < 0: return "Inelastic"
    return "Check"

df['ELASTICITY_TYPE'] = df['ELASTICITY'].apply(elasticity_type)

# ================= ALERTS =================
# thresholds tuned to your business (lead time ~16 weeks)
df['ALERT'] = np.select(
    [
        (df['SELL_THROUGH'] < 0.3) & (df['COVER'] > 16),    # slow + high cover
        (df['SELL_THROUGH'] > 0.6) & (df['COVER'] < 12),    # fast + low cover
        (df['SOH_QTY'] == 0)                                # no stock
    ],
    [
        "Overstock Risk ❌",
        "Stockout Risk 🔥",
        "No Stock ⚠️"
    ],
    default="Healthy"
)

# ================= AUTO RECOMMENDATIONS =================
def recommendation(row):
    if (row['ELASTICITY'] < -1.5) and (row['SELL_THROUGH'] < 0.4) and (row['COVER'] > 16):
        return "Increase Markdown 🔻"
    if (row['SELL_THROUGH'] > 0.6) and (row['COVER'] < 12):
        return "Replenish 🚀"
    if (row['ELASTICITY'] > -0.5) and (row['SELL_THROUGH'] < 0.4):
        return "Avoid Discount ⚠️"
    return "Monitor"

df['RECOMMENDATION'] = df.apply(recommendation, axis=1)

# ================= SIDEBAR FILTERS =================
st.sidebar.title("Filters")

dept = st.sidebar.multiselect("Department", df['Department'].unique(), default=df['Department'].unique())
store = st.sidebar.multiselect("Store", df['LOC_CD'].unique(), default=df['LOC_CD'].unique())

df_f = df[(df['Department'].isin(dept)) & (df['LOC_CD'].isin(store))].copy()

# Drill-down SKU selector (based on filtered set)
sku_options = ["All"] + sorted(df_f['ITM_CD'].unique().tolist())
sku = st.sidebar.selectbox("SKU (drill-down)", sku_options)

if sku != "All":
    df_f = df_f[df_f['ITM_CD'] == sku]

# ================= KPI CARDS =================
st.title("🚀 Retail Intelligence – Decision Dashboard")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue", round(df_f['REVENUE'].sum(), 2))
c2.metric("Margin", round(df_f['MARGIN'].sum(), 2))
c3.metric("ROS", round(df_f['ROS'].mean(), 2))
c4.metric("Cover", round(df_f['COVER'].mean(), 2))
c5.metric("Sell-through", round(df_f['SELL_THROUGH'].mean(), 2))

# ================= ELASTICITY PANEL (PER SKU) =================
st.subheader("📊 Elasticity (Per SKU View)")

# If user picked a SKU, show its price-demand curve across stores/time
if sku != "All":
    sku_df = df_f.copy()
    if sku_df[['PRICE','SALES_QTY']].dropna().shape[0] >= 3:
        fig = px.scatter(
            sku_df,
            x='PRICE', y='SALES_QTY',
            color='LOC_CD',
            trendline="ols",
            title=f"Price vs Demand for SKU: {sku}"
        )
        st.plotly_chart(fig, use_container_width=True)
        e_val = sku_df['ELASTICITY'].mean()
        st.metric("Elasticity", round(e_val, 2) if pd.notna(e_val) else "N/A")
        st.caption("Interpretation: < -1 elastic (good for markdown), > 0 suspicious/constraints.")
    else:
        st.info("Not enough data points for this SKU to estimate elasticity.")
else:
    # Portfolio view: distribution
    fig = px.histogram(
        df_f.dropna(subset=['ELASTICITY']),
        x='ELASTICITY',
        nbins=40,
        title="Elasticity Distribution (Filtered Portfolio)"
    )
    st.plotly_chart(fig, use_container_width=True)

    by_type = df_f['ELASTICITY_TYPE'].value_counts().reset_index()
    by_type.columns = ['Type', 'Count']
    fig2 = px.bar(by_type, x='Type', y='Count', title="Elasticity Buckets")
    st.plotly_chart(fig2, use_container_width=True)

# ================= ALERTS =================
st.subheader("🚨 Alerts")

alert_counts = df_f['ALERT'].value_counts().reset_index()
alert_counts.columns = ['Alert', 'Count']
fig_alert = px.bar(alert_counts, x='Alert', y='Count', color='Alert', title="Alert Summary")
st.plotly_chart(fig_alert, use_container_width=True)

# Show worst cases table
st.markdown("**Top Alert Items**")
alert_table = df_f[df_f['ALERT'] != "Healthy"] \
    .sort_values(by=['COVER','SELL_THROUGH'], ascending=[False, True]) \
    [['ITM_CD','LOC_CD','COVER','SELL_THROUGH','ALERT']] \
    .head(20)
st.dataframe(alert_table, use_container_width=True)

# ================= AUTO RECOMMENDATIONS =================
st.subheader("🤖 Auto Recommendations")

rec_counts = df_f['RECOMMENDATION'].value_counts().reset_index()
rec_counts.columns = ['Recommendation', 'Count']
fig_rec = px.bar(rec_counts, x='Recommendation', y='Count', color='Recommendation', title="Recommendation Summary")
st.plotly_chart(fig_rec, use_container_width=True)

st.markdown("**Top Actionable SKUs**")
rec_table = df_f[df_f['RECOMMENDATION'] != "Monitor"] \
    .sort_values(by=['ELASTICITY','SELL_THROUGH'], ascending=[True, True]) \
    [['ITM_CD','LOC_CD','ELASTICITY','SELL_THROUGH','COVER','RECOMMENDATION']] \
    .head(20)
st.dataframe(rec_table, use_container_width=True)

# ================= CORE SCATTER =================
st.subheader("📍 Stock vs Demand (Decision Map)")

fig_scatter = px.scatter(
    df_f,
    x='COVER', y='SELL_THROUGH',
    color='Department',
    hover_data=['ITM_CD','LOC_CD','ELASTICITY','RECOMMENDATION','ALERT'],
    title='Cover vs Sell-through'
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ================= TRENDS =================
st.subheader("📈 Trends")

sales_trend = df_f.groupby('TRDNG_WK_END_DT')['REVENUE'].sum().reset_index()
ros_trend = df_f.groupby('TRDNG_WK_END_DT')['ROS'].mean().reset_index()
cover_trend = df_f.groupby('TRDNG_WK_END_DT')['COVER'].mean().reset_index()

colA, colB, colC = st.columns(3)
colA.plotly_chart(px.line(sales_trend, x='TRDNG_WK_END_DT', y='REVENUE', title='Revenue'), use_container_width=True)
colB.plotly_chart(px.line(ros_trend, x='TRDNG_WK_END_DT', y='ROS', title='ROS'), use_container_width=True)
colC.plotly_chart(px.line(cover_trend, x='TRDNG_WK_END_DT', y='COVER', title='Cover'), use_container_width=True)

# ================= EXPORT =================
st.subheader("📤 Export Report")

# Prepare sheets
kpi_summary = pd.DataFrame({
    "Metric": ["Revenue","Margin","ROS","Cover","Sell-through"],
    "Value": [
        df_f['REVENUE'].sum(),
        df_f['MARGIN'].sum(),
        df_f['ROS'].mean(),
        df_f['COVER'].mean(),
        df_f['SELL_THROUGH'].mean()
    ]
})

elasticity_out = df_f[['ITM_CD','LOC_CD','ELASTICITY','ELASTICITY_TYPE']]
alerts_out = df_f[['ITM_CD','LOC_CD','ALERT']]
recs_out = df_f[['ITM_CD','LOC_CD','RECOMMENDATION']]

output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_f.to_excel(writer, sheet_name='Data', index=False)
    kpi_summary.to_excel(writer, sheet_name='KPI', index=False)
    elasticity_out.to_excel(writer, sheet_name='Elasticity', index=False)
    alerts_out.to_excel(writer, sheet_name='Alerts', index=False)
    recs_out.to_excel(writer, sheet_name='Recommendations', index=False)

st.download_button(
    "Download Full Report",
    data=output.getvalue(),
    file_name="retail_decision_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ================= DATA VIEW =================
with st.expander("🔎 View Filtered Data"):
    st.dataframe(df_f, use_container_width=True)
