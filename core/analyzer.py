import pandas as pd
import numpy as np

def analyze_dataframe(df: pd.DataFrame, metrics_config: dict) -> dict:
    if df.empty:
        return {"empty": True}

    analysis = {}
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    # Базовые
    if metrics_config.get("shape"):
        analysis["shape"] = df.shape
    if metrics_config.get("missing"):
        analysis["missing"] = df.isnull().sum().to_dict()
        analysis["missing_pct"] = (df.isnull().mean() * 100).round(2).to_dict()
    if metrics_config.get("unique"):
        analysis["unique"] = df.nunique().to_dict()

    # Числовые
    if num_cols:
        desc = df[num_cols].describe()
        if any(metrics_config.get(k) for k in ["mean", "median", "std", "quantiles", "min_max"]):
            analysis["numeric_stats"] = desc.to_dict()
        if metrics_config.get("skew_kurt_iqr"):
            analysis["skew"] = df[num_cols].skew().round(3).to_dict()
            analysis["kurtosis"] = df[num_cols].kurtosis().round(3).to_dict()
            analysis["iqr"] = (desc.loc["75%"] - desc.loc["25%"]).round(3).to_dict()
            analysis["mode"] = df[num_cols].mode().iloc[0].to_dict()

    # Категориальные
    if cat_cols and metrics_config.get("top_values"):
        analysis["categorical_top"] = {
            col: df[col].value_counts().head(5).to_dict()
            for col in cat_cols if not df[col].isnull().all()
        }

    return analysis