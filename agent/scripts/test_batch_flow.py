import akshare as ak
try:
    df = ak.stock_individual_fund_flow_rank()
    print("stock_individual_fund_flow_rank columns:", df.columns)
    print("rows:", len(df))
    print("sample:", df.head(3).to_dict(orient="records"))
except Exception as e:
    print("Failed:", e)
