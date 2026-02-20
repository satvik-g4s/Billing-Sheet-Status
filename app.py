import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("Upload Current Month Billing (CSV)", type=["csv"])

with col2:
    uploaded_file_2 = st.file_uploader("Upload Hub Branch Mapping (CSV)", type=["csv"])

run = st.button("Run")

if run:
    if uploaded_file is not None and uploaded_file_2 is not None:

        df = pd.read_csv(
            uploaded_file,
            usecols=["Order_No", "cust_no", "cust_name", "invoice_dt", "Period_To","order_locn"]
        )

        bfl = pd.read_csv(
            uploaded_file_2,
            usecols=["Cust_No","so_locn", "branch_finance_lead"]
        )

        bfl["key"]=bfl["Cust_No"].astype(str)+bfl["so_locn"].astype(str)
        df["key"]=df["cust_no"].astype(str)+df["order_locn"].astype(str)
        bfl["key"]=bfl["key"].str.upper()
        df["key"]=df["key"].str.upper()
        df["invoice_dt"] = pd.to_datetime(df["invoice_dt"])
        df["Period_To"] = pd.to_datetime(df["Period_To"])

        df = df[df["invoice_dt"].dt.year == 2026]

        df = df[
            ((df["invoice_dt"].dt.month - df["Period_To"].dt.month) == 1) |
            ((df["invoice_dt"].dt.month == 1) & (df["Period_To"].dt.month == 12))
        ]

        df = df[df["Period_To"] >= "2025-12-01"]

        count_df = (
            df.groupby(
                ["cust_no","key", "cust_name", "Order_No", "Period_To"]
            )
            .size()
            .reset_index(name="Count")
        )

        count_df["Period_To"] = count_df["Period_To"].dt.strftime("%b %Y")

        pivot = (
            count_df.pivot_table(
                index=["cust_no","key", "cust_name", "Order_No"],
                columns="Period_To",
                values="Count",
                fill_value=0
            )
            .reset_index()
        )

        pivot = pivot.merge(
            bfl,
            on="key",
            how="left"
        ).drop(columns=["Cust_No"])

        non_month_cols = [
            "cust_no",
            "key",
            "cust_name",
            "Order_No",
            "so_locn",
            "branch_finance_lead"
        ]
        
        month_cols = sorted(
            [col for col in pivot.columns if col not in non_month_cols],
            key=lambda x: pd.to_datetime(x, format="%b %Y")
        )

        pivot = pivot[
            ["cust_no", "cust_name", "Order_No", "branch_finance_lead"] + month_cols
        ]

        if len(month_cols) >= 2:
            last_col = month_cols[-1]
            second_last_col = month_cols[-2]

            def status(row):
                if row[last_col] == 0 and row[second_last_col] != 0:
                    return "Removed"
                elif row[last_col] != 0 and row[second_last_col] == 0:
                    return "Added"
                else:
                    return ""

            pivot["Status"] = pivot.apply(status, axis=1)

        st.dataframe(pivot)

        csv = pivot.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Output",
            data=csv,
            file_name="output.csv",
            mime="text/csv"
        )

    else:
        st.warning("Please upload both files.")
