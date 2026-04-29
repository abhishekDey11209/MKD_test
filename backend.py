import pandas as pd
import numpy as np

def process_data(df):

    df['TRDNG_WK_END_DT'] = pd.to_datetime(df['TRDNG_WK_END_DT'])
    df['LST_GRN_DT'] = pd.to_datetime(df['LST_GRN_DT'])
    df = df.fillna(0)

    # AGE
    df['AGE_DAYS'] = (df['TRDNG_WK_END_DT'] - df['LST_GRN_DT']).dt.days
    df['AGE_WEEKS'] = df['AGE_DAYS'] / 7
    df['LIFECYCLE_PCT'] = df['AGE_WEEKS'] / 16

    # STOCK
    df['TOTAL_STOCK'] = df['SOH_QTY'] + df['IN_TRNST_QTY']

    # SALES
    df['REVENUE'] = df['NET_SLS_AMT_AED']
    df['SALES_QTY'] = df['RTL_QTY']
    df['ASP'] = df['REVENUE'] / df['SALES_QTY'].replace(0, np.nan)

    # MARGIN
    df['MARGIN'] = df['REVENUE'] - df['COST_AED']
    df['MARGIN_PCT'] = df['MARGIN'] / df['REVENUE'].replace(0, np.nan)

    # SELL THROUGH
    df['SELL_THROUGH'] = np.where(
        (df['SALES_QTY'] + df['SOH_QTY']) > 0,
        df['SALES_QTY'] / (df['SALES_QTY'] + df['SOH_QTY']),
        0
    )

    # ROS
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

    # COVER
    df['COVER'] = df['TOTAL_STOCK'] / df['ROS'].replace(0, np.nan)

    # PRICE
    df['PRICE'] = df['REVENUE'] / df['SALES_QTY'].replace(0, np.nan)
    df['CURR_MD'] = 1 - (df['REVENUE'] / df['REG_RTL_AED'].replace(0, np.nan))
    df['PRICE_REALIZATION'] = df['PRICE'] / df['REG_RTL_AED'].replace(0, np.nan)

    # ELASTICITY
    df['LOG_QTY'] = np.log(df['SALES_QTY'].replace(0, np.nan))
    df['LOG_PRICE'] = np.log(df['PRICE'])

    def calc_elasticity(group):
        group = group.dropna(subset=['LOG_QTY', 'LOG_PRICE'])
        if len(group) < 3:
            return np.nan
        return np.polyfit(group['LOG_PRICE'], group['LOG_QTY'], 1)[0]

    elasticity = (
        df.groupby(['ITM_CD', 'LOC_CD'])
        .apply(calc_elasticity)
        .reset_index()
        .rename(columns={0: 'ELASTICITY'})
    )

    df = df.merge(elasticity, on=['ITM_CD', 'LOC_CD'], how='left')

    return df


def calculate_mix(df):
    total_stock = df['TOTAL_STOCK'].sum()
    total_sales = df['SALES_QTY'].sum()
    total_rev = df['REVENUE'].sum()

    mix = df.groupby('Department').agg({
        'TOTAL_STOCK': 'sum',
        'SALES_QTY': 'sum',
        'REVENUE': 'sum'
    }).reset_index()

    mix['STOCK_MIX'] = mix['TOTAL_STOCK'] / total_stock
    mix['SALES_MIX'] = mix['SALES_QTY'] / total_sales
    mix['RETAIL_MIX'] = mix['REVENUE'] / total_rev

    return mix
