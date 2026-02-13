import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

uploaded_file = st.file_uploader(
    "Upload Current Month Billing (CSV)",
    type=["csv"],
    key="file1"
)

uploaded_file2 = st.file_uploader(
    "Upload Hub Branch Mapping (CSV)",
    type=["csv"],
    key="file2"
)

if st.button("Run"):
    if uploaded_file is not None and uploaded_file2 is not None:

        df = pd.read_csv(
            uploaded_file,
            index_col=False,
            usecols=["Order_No","cust_no","cust_name","invoice_dt","Period_To"]
        )

        bfl = pd.read_csv(
            uploaded_file2,
            usecols=["Cust_No","branch_finance_lead"]
        )

        df["invoice_dt"] = pd.to_datetime(df["invoice_dt"])
        df["Period_To"] = pd.to_datetime(df["Period_To"])

        df["invoice_dt"] = df["invoice_dt"].dt.strftime('%b %Y')
        df["Period_To"] = df["Period_To"].dt.strftime('%b %Y')

        df = df[["Order_No","cust_no","cust_name","invoice_dt","Period_To"]]

        df = df[
            pd.to_datetime(df["invoice_dt"], format='%b %Y').dt.year == 2026
        ]

        df = df[
            (
                (pd.to_datetime(df["invoice_dt"], format='%b %Y').dt.month -
                 pd.to_datetime(df["Period_To"], format='%b %Y').dt.month) == 1
            ) |
            (
                (pd.to_datetime(df["invoice_dt"], format='%b %Y').dt.month == 1) &
                (pd.to_datetime(df["Period_To"], format='%b %Y').dt.month == 12)
            )
        ]

        df = pd.merge(
            df,
            bfl,
            left_on="cust_no",
            right_on="Cust_No",
            how="left"
        )

        df = df.drop(columns=["Cust_No"])

        temp = df.groupby(["Order_No","Period_To"]).size().unstack(fill_value=0)

        df = df.merge(temp, on="Order_No", how="left")

        df = df.drop_duplicates(subset=["Order_No"])

        df = df.drop(columns=["invoice_dt","Period_To"])

        month_cols = sorted(
            df.columns[4:],
            key=lambda x: pd.to_datetime(x, format="%b %Y")
        )

        df = df[["cust_no","cust_name","Order_No","branch_finance_lead"] + month_cols]

        last_col = month_cols[-1]
        second_last_col = month_cols[-2]

        def status(row):
            if (row[last_col] == 0) and (row[second_last_col] != 0):
                return "Removed"
            elif (row[last_col] != 0) and (row[second_last_col] == 0):
                return "Added"
            else:
                return row[last_col]

        df[last_col] = df.apply(status, axis=1)

        st.dataframe(df)

    else:
        st.warning("Please upload both files.")
