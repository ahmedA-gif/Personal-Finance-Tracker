import streamlit as st
from datetime import datetime
import pandas as pd
import base64
from io import BytesIO
import sys
import os
import logging
import time
from streamlit.runtime.scriptrunner import RerunData, RerunException

# Add the directory containing finance_tracker.py to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from finance_tracker import FinanceTracker
except ImportError as e:
    st.error(f"Failed to import FinanceTracker: {str(e)}")
    st.stop()

# Initialize finance tracker with error handling
try:
    tracker = FinanceTracker()
except Exception as e:
    st.error(f"Failed to initialize FinanceTracker: {str(e)}")
    st.stop()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('streamlit_app.log'),
        logging.StreamHandler()
    ]
)

# Page configuration
st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
def load_css():
    st.markdown("""
    <style>
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .progress-container {
            height: 25px;
            background-color: #e9ecef;
            border-radius: 12px;
            margin-bottom: 15px;
        }
        .progress-bar {
            height: 100%;
            border-radius: 12px;
            background-color: #4361ee;
            transition: width 0.6s ease;
        }
        .stDataFrame {
            width: 100%;
        }
        .stButton>button {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

load_css()

def display_error(message, error=None):
    """Display error message with optional details"""
    st.error(message)
    if error:
        logging.error(f"{message}: {str(error)}")
        with st.expander("Error Details"):
            st.exception(error)

def get_transactions_dataframe():
    """Get transactions as a DataFrame with error handling"""
    try:
        transactions = tracker.get_transactions()
        if not transactions:
            return None
            
        trans_data = []
        for t in transactions:
            trans_data.append({
                "ID": t._trans_id,
                "Date": t._date,
                "Amount": t._amount,
                "Category": t._category,
                "Type": t._trans_type.capitalize(),
                "Description": t._description
            })
        return pd.DataFrame(trans_data)
    except Exception as e:
        display_error("Failed to load transactions", e)
        return None

def display_financial_summary():
    """Display financial summary cards"""
    try:
        summary = tracker.get_financial_summary()
        if not summary:
            st.info("No financial data available")
            return
            
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Total Income</h3>
                <h2>${summary['total_income']:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Total Expenses</h3>
                <h2>${summary['total_expense']:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Net Savings</h3>
                <h2>${summary['net_savings']:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Savings Rate</h3>
                <h2>{summary['savings_rate']:.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        display_error("Failed to load financial summary", e)

def display_budget_status():
    """Display budget status with progress bars"""
    try:
        budget_status = tracker.get_budget_status()
        if not budget_status:
            st.info("No budgets set yet")
            return
            
        st.subheader("Budget Status")
        for budget in budget_status:
            progress = min(budget['percentage'] / 100, 1)
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                <div style="margin-bottom: 5px;">
                    <strong>{budget['category']}</strong> (${budget['limit']:,.2f})
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {progress*100}%;"></div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div style="text-align: right; padding-top: 8px;">
                    ${budget['spent']:,.2f} / ${budget['limit']:,.2f}<br>
                    ({budget['percentage']:.1f}%)
                </div>
                """, unsafe_allow_html=True)
                
            if budget['exceeded']:
                st.warning("Budget exceeded!")
                
    except Exception as e:
        display_error("Failed to load budget status", e)

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Transactions", "Budgets", "Reports"])

# Dashboard Page
if page == "Dashboard":
    st.title("💰 Personal Finance Dashboard")
    display_financial_summary()
    display_budget_status()
    
    st.subheader("Recent Transactions")
    df = get_transactions_dataframe()
    if df is not None:
        st.dataframe(df.tail(5))
    else:
        st.info("No transactions available")

# Transactions Page
elif page == "Transactions":
    st.title("💸 Transaction Management")
    
    tab1, tab2 = st.tabs(["Add Transaction", "View/Delete Transactions"])
    
    with tab1:
        with st.form("add_transaction_form"):
            st.subheader("Add New Transaction")
            
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date", datetime.now())
                amount = st.number_input("Amount", min_value=0.01, step=0.01, format="%.2f")
            with col2:
                category = st.text_input("Category", placeholder="e.g., Groceries")
                trans_type = st.selectbox("Type", ["income", "expense"])
            
            description = st.text_area("Description", placeholder="Optional details about the transaction")
            
            submitted = st.form_submit_button("Add Transaction")
            
            if submitted:
                try:
                    tracker.add_transaction(
                        date.strftime("%Y-%m-%d"),
                        amount,
                        category,
                        trans_type,
                        description
                    )
                    st.success("Transaction added successfully!")
                    time.sleep(1)  # Give user time to see the success message
                    raise RerunException(RerunData(None))
                except Exception as e:
                    display_error("Failed to add transaction", e)
    
    with tab2:
        st.subheader("All Transactions")
        df = get_transactions_dataframe()
        if df is not None:
            st.dataframe(df)
            
            st.subheader("Delete Transaction")
            trans_id = st.selectbox("Select transaction to delete", df["ID"].tolist())
            
            if st.button("Delete Selected Transaction"):
                try:
                    tracker.delete_transaction(trans_id)
                    st.success("Transaction deleted successfully!")
                    time.sleep(1)  # Give user time to see the success message
                    raise RerunException(RerunData(None))
                except Exception as e:
                    display_error("Failed to delete transaction", e)
        else:
            st.info("No transactions available")

# Budgets Page
elif page == "Budgets":
    st.title("📊 Budget Management")
    
    tab1, tab2 = st.tabs(["Set Budget", "View/Delete Budgets"])
    
    with tab1:
        with st.form("set_budget_form"):
            st.subheader("Set New Budget")
            
            category = st.text_input("Category", placeholder="e.g., Groceries")
            limit = st.number_input("Monthly Limit ($)", min_value=0.01, step=0.01, format="%.2f")
            
            submitted = st.form_submit_button("Set Budget")
            
            if submitted:
                try:
                    tracker.set_budget(category, limit)
                    st.success("Budget set successfully!")
                    time.sleep(1)  # Give user time to see the success message
                    raise RerunException(RerunData(None))
                except Exception as e:
                    display_error("Failed to set budget", e)
    
    with tab2:
        st.subheader("Current Budgets")
        try:
            budgets = tracker.get_budgets()
            if budgets:
                budget_data = []
                for b in budgets:
                    budget_data.append({
                        "Category": b._category,
                        "Monthly Limit": f"${b._limit:,.2f}"
                    })
                
                st.dataframe(pd.DataFrame(budget_data))
                
                st.subheader("Delete Budget")
                budget_categories = [b._category for b in budgets]
                budget_to_delete = st.selectbox("Select budget to delete", budget_categories)
                
                if st.button("Delete Selected Budget"):
                    try:
                        tracker.delete_budget(budget_to_delete)
                        st.success("Budget deleted successfully!")
                        time.sleep(1)  # Give user time to see the success message
                        raise RerunException(RerunData(None))
                    except Exception as e:
                        display_error("Failed to delete budget", e)
            else:
                st.info("No budgets set yet")
        except Exception as e:
            display_error("Failed to load budgets", e)

# Reports Page
elif page == "Reports":
    st.title("📈 Financial Reports")
    
    if st.button("Generate All Reports"):
        with st.spinner("Generating reports..."):
            try:
                # Generate reports
                monthly_report = tracker.get_monthly_report()
                category_report = tracker.get_category_report()
                visualizations = tracker.get_visualizations()
                
                # Display reports
                st.success("Reports generated successfully!")
                
                if visualizations:
                    cols = st.columns(2)
                    
                    with cols[0]:
                        if 'monthly_trends' in visualizations:
                            st.subheader("Monthly Trends")
                            st.image(BytesIO(base64.b64decode(visualizations['monthly_trends'])))
                        
                    with cols[1]:
                        if 'category_spending' in visualizations:
                            st.subheader("Category Spending")
                            st.image(BytesIO(base64.b64decode(visualizations['category_spending'])))
                    
                    with cols[0]:
                        if 'budget_status' in visualizations:
                            st.subheader("Budget Status")
                            st.image(BytesIO(base64.b64decode(visualizations['budget_status'])))
                    
                    with cols[1]:
                        if 'daily_spending' in visualizations:
                            st.subheader("Daily Spending")
                            st.image(BytesIO(base64.b64decode(visualizations['daily_spending'])))
                
                # Download buttons
                st.subheader("Download Reports")
                col1, col2 = st.columns(2)
                
                with col1:
                    if monthly_report:
                        with open(monthly_report, "rb") as f:
                            st.download_button(
                                label="Download Monthly Report (CSV)",
                                data=f,
                                file_name="monthly_report.csv",
                                mime="text/csv"
                            )
                
                with col2:
                    if category_report:
                        with open(category_report, "rb") as f:
                            st.download_button(
                                label="Download Category Report (CSV)",
                                data=f,
                                file_name="category_report.csv",
                                mime="text/csv"
                            )
                
            except Exception as e:
                display_error("Failed to generate reports", e)
    else:
        st.info("Click the button above to generate financial reports")