import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# =========================
# TITLE
# =========================
st.title("Monthly Billing Adjustment Tracker")

st.markdown("---")

# =========================
# FILE UPLOAD SECTION
# =========================
st.header("Upload Files")

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("Upload Current Month Billing (CSV)", type=["csv"])
    st.caption(
        "Required columns: Order_No, cust_no, cust_name, invoice_dt, Period_To, order_locn\n"
        "• Dates should be in standard date format\n"
        "• Each row represents a billing entry"
    )

with col2:
    uploaded_file_2 = st.file_uploader("Upload Hub Branch Mapping (CSV/Excel)", type=["csv","xlsx","xls"])
    st.caption(
        "Required columns: Cust_No, so_locn, branch_finance_lead\n"
        "• Maps customers + location to finance owner\n"
        "• Prefer CSV format for best compatibility"
    )

# =========================
# RUN BUTTON
# =========================
st.markdown("")
run = st.button("Run Analysis")

st.markdown("---")

# =========================
# DOCUMENTATION SECTIONS
# =========================

with st.expander("What This Tool Does"):
    st.write(
        """
        This tool analyzes monthly billing data to identify **changes in customer billing activity**.

        It compares billing presence across months and highlights:
        - Customers/orders that are newly added
        - Customers/orders that are no longer billed

        It also maps each record to a **Branch Finance Lead** for accountability.
        """
    )

with st.expander("How to Use"):
    st.write(
        """
        1. Upload the **Current Month Billing file (CSV)**  
        2. Upload the **Hub Branch Mapping file (CSV/Excel)**  
        3. Click **Run Analysis**  
        4. Review the output table  
        5. Download results for reporting or sharing  

        Ensure:
        - Column names match exactly
        - Dates are properly formatted
        """
    )

with st.expander("Output Details"):
    st.write(
        """
        The output provides:

        - Customer details (Customer No, Name, Order No)
        - Monthly billing counts (pivoted format)
        - Assigned Branch Finance Lead
        - Status indicator:
            • Added → Appears in latest month but not previous  
            • Removed → Missing in latest month but present earlier  

        This helps track **billing movement trends** across months.
        """
    )

with st.expander("Financial Logic"):
    st.write(
        """
        **1. Month-on-Month Comparison**

        Billing records are compared across consecutive months.

        **2. Status Determination**

        - Added:
            Current Month ≠ 0 AND Previous Month = 0  
        - Removed:
            Current Month = 0 AND Previous Month ≠ 0  

        **3. Data Filtering Rules**

        - Only records from year 2026 are considered  
        - Invoice month must be exactly one month after service period  

        **4. Key Matching Logic**

        A unique key is created using:

        """)
    
    st.latex(r"\text{Key} = \text{Customer Number} + \text{Location}")
    
    st.write(
        """
        This ensures accurate mapping between billing data and finance ownership.

        **5. Aggregation**

        Billing counts are calculated per:
        - Customer
        - Order
        - Month
        """
    )

# =========================
# MAIN LOGIC (UNCHANGED)
# =========================

if run:
    if uploaded_file is not None and uploaded_file_2 is not None:

        encodings = ["utf-8", "latin1", "cp1252"]

        for enc in encodings:
            try:
                df = pd.read_csv(
                    uploaded_file,
                    usecols=["Order_No", "cust_no", "cust_name", "invoice_dt", "Period_To", "order_locn"],
                    encoding=enc
                )
                break
            except UnicodeDecodeError:
                continue

        if uploaded_file_2 is not None:

            if uploaded_file_2.name.endswith(".csv"):
                bfl = pd.read_csv(
                    uploaded_file_2,
                    usecols=["Cust_No","so_locn","branch_finance_lead"],
                    encoding="latin1"
                )
        
            else:  # Excel file
                bfl = pd.read_excel(uploaded_file_2, sheet_name=0)
                
                bfl.columns = bfl.columns.str.strip().str.lower()
                st.write('If you see an error at bfl = bfl[["cust_no","so_locn","branch_finance_lead"]], please upload the mapping file in CSV format (Save As CSV in Excel and upload).')
                bfl = bfl[["cust_no","so_locn","branch_finance_lead"]]

        
        # Clean BFL columns
        bfl["Cust_No"] = (
            bfl["Cust_No"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )
        
        bfl["so_locn"] = (
            bfl["so_locn"]
            .astype(str)
            .str.strip()
        )
        
        # Clean DF columns
        df["cust_no"] = (
            df["cust_no"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )
        
        df["order_locn"] = (
            df["order_locn"]
            .astype(str)
            .str.strip()
        )
        
        # Create keys
        bfl["key"] = (bfl["Cust_No"] + bfl["so_locn"]).str.upper()
        df["key"] = (df["cust_no"] + df["order_locn"]).str.upper()

        
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

        st.subheader("Results")
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
