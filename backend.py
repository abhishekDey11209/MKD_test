import pandas as pd
import numpy as np

def process_data(df):

    df['TRDNG_WK_END_DT'] = pd.to_datetime(df['TRDNG_WK_END_DT'])
    df['LST_GRN_DT'] = pd.to_datetime(df['LST_GRN_DT'])
    df = df.fillna(0)

    # SALES
    df['REVENUE'] = df['NET_SLS_AMT_AED']
    df['SALES_QTY'] = df['RTL_QTY']

    # STOCK
    df['TOTAL_STOCK'] = df['SOH_QTY'] + df['IN_TRNST_QTY']

    # AGE
    df['AGE_WEEKS'] = (df['TRDNG_WK_END_DT'] - df['LST_GRN_DT']).dt.days / 7

    # ROS
    weeks_traded = (
        df[df['SALES_QTY'] > 0]
        .groupby(['ITM_CD','LOC_CD'])['TRDNG_WK_END_DT']
        .nunique()
        .reset_index()
        .rename(columns={'TRDNG_WK_END_DT':'WEEKS_TRADED'})
    )

    df = df.merge(weeks_traded, on=['ITM_CD','LOC_CD'], how='left')
    df['WEEKS_TRADED'] = df['WEEKS_TRADED'].fillna(0)

    df['EFFECTIVE_WEEKS'] = df[['AGE_WEEKS','WEEKS_TRADED']].min(axis=1)
    df['ROS'] = df['SALES_QTY'] / df['EFFECTIVE_WEEKS'].replace(0,np.nan)

    # COVER
    df['COVER'] = df['TOTAL_STOCK'] / df['ROS'].replace(0,np.nan)

    # MARGIN
    df['MARGIN'] = df['REVENUE'] - df['COST_AED']
    df['MARGIN_PCT'] = df['MARGIN'] / df['REVENUE'].replace(0,np.nan)

    # INTAKE
    df['INTAKE_MARGIN'] = df['REG_RTL_AED'] - df['COST_AED']

    # SELL THROUGH
    df['SELL_THROUGH'] = df['SALES_QTY'] / (df['SALES_QTY'] + df['SOH_QTY']).replace(0,np.nan)

    # PRICE
    df['ASP'] = df['REVENUE'] / df['SALES_QTY'].replace(0,np.nan)
    df['CURR_MD'] = 1 - (df['REVENUE'] / df['REG_RTL_AED'].replace(0,np.nan))

    # STOCK KPIs
    df['STOCK_TO_SALES'] = df['TOTAL_STOCK'] / df['SALES_QTY'].replace(0,np.nan)
    df['OOS_PCT'] = (df['SOH_QTY'] == 0).astype(int)

    # GMROI
    avg_inv = df['SOH_COGS_2_AED'].mean()
    df['GMROI'] = df['MARGIN'] / avg_inv if avg_inv != 0 else 0

    return df
