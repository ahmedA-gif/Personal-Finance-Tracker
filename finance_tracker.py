import pandas as pd
import numpy as np
from datetime import datetime
import os
import logging
from scipy import optimize
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from contextlib import contextmanager
import csv
from collections import defaultdict
import uuid

# Configure logging
logging.basicConfig(filename='finance.log', level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Decorator to log actions
def log_action(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            logging.info(f"{func.__name__} called with args={args}, kwargs={kwargs}")
            return result
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper

# Context manager for file handling
@contextmanager
def file_handler(filename, mode='r'):
    file = None
    try:
        file = open(filename, mode, newline='')
        yield file
    except IOError as e:
        logging.error(f"File operation failed for {filename}: {str(e)}")
        raise
    finally:
        if file is not None:
            file.close()

# Transaction class with improved validation
class Transaction:
    def __init__(self, trans_id, date, amount, category, trans_type, description=""):
        self._validate_inputs(amount, date, trans_type)
        self._trans_id = trans_id
        self._date = date
        self._amount = float(amount)
        self._category = category
        self._trans_type = trans_type.lower()
        self._description = description

    def _validate_inputs(self, amount, date, trans_type):
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        
        try:
            float(amount)
            if float(amount) <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            raise ValueError("Amount must be a positive number")
            
        if trans_type.lower() not in ('income', 'expense'):
            raise ValueError("Transaction type must be 'income' or 'expense'")

    def display(self):
        return f"ID: {self._trans_id}, Date: {self._date}, Amount: ${self._amount:.2f}, Category: {self._category}, Type: {self._trans_type}, Description: {self._description}"

# Budget class with enhanced functionality
class Budget:
    def __init__(self, category, limit):
        self._validate_inputs(limit)
        self._category = category
        self._limit = float(limit)
        
    def _validate_inputs(self, limit):
        try:
            if float(limit) <= 0:
                raise ValueError("Budget limit must be positive")
        except ValueError:
            raise ValueError("Budget limit must be a positive number")
        
    def check_limit(self, expenses):
        total = sum([e._amount for e in expenses if e._category == self._category])
        percentage = (total / self._limit) * 100 if self._limit > 0 else 0
        return {
            'exceeded': total > self._limit,
            'total': total,
            'remaining': max(0, self._limit - total),
            'percentage': min(100, percentage)
        }

# Data storage configuration
DATA_DIR = 'data'
DATA_FILE = os.path.join(DATA_DIR, 'transactions.csv')
BUDGET_FILE = os.path.join(DATA_DIR, 'budgets.csv')
REPORTS_DIR = os.path.join(DATA_DIR, 'reports')

# Initialize directories and files
def init_files():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        if not os.path.exists(DATA_FILE):
            with file_handler(DATA_FILE, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'date', 'amount', 'category', 'type', 'description'])
                
        if not os.path.exists(BUDGET_FILE):
            with file_handler(BUDGET_FILE, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['category', 'limit'])
    except Exception as e:
        logging.error(f"Initialization failed: {str(e)}")
        raise

init_files()

# Transaction Management
class TransactionManager:
    @log_action
    def load_transactions(self):
        transactions = []
        try:
            with file_handler(DATA_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        trans = Transaction(
                            row['id'],
                            row['date'],
                            row['amount'],
                            row['category'],
                            row['type'],
                            row.get('description', '')
                        )
                        transactions.append(trans)
                    except ValueError as e:
                        logging.warning(f"Skipping invalid transaction: {row}. Error: {str(e)}")
            return transactions
        except FileNotFoundError:
            return []

    @log_action
    def add_transaction(self, date, amount, category, trans_type, description=""):
        trans_id = str(uuid.uuid4())
        try:
            trans = Transaction(trans_id, date, amount, category, trans_type, description)
            with file_handler(DATA_FILE, 'a') as f:
                writer = csv.writer(f)
                writer.writerow([trans_id, date, amount, category, trans_type, description])
            return trans
        except Exception as e:
            logging.error(f"Failed to add transaction: {str(e)}")
            raise

    @log_action
    def delete_transaction(self, trans_id):
        transactions = self.load_transactions()
        updated_transactions = [t for t in transactions if t._trans_id != trans_id]
        
        try:
            with file_handler(DATA_FILE, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'date', 'amount', 'category', 'type', 'description'])
                for t in updated_transactions:
                    writer.writerow([
                        t._trans_id,
                        t._date,
                        t._amount,
                        t._category,
                        t._trans_type,
                        t._description
                    ])
            return True
        except Exception as e:
            logging.error(f"Failed to delete transaction: {str(e)}")
            raise

# Budget Management
class BudgetManager:
    @log_action
    def load_budgets(self):
        budgets = []
        try:
            with file_handler(BUDGET_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        budget = Budget(row['category'], row['limit'])
                        budgets.append(budget)
                    except ValueError as e:
                        logging.warning(f"Skipping invalid budget: {row}. Error: {str(e)}")
            return budgets
        except FileNotFoundError:
            return []

    @log_action
    def set_budget(self, category, limit):
        try:
            budget = Budget(category, limit)
            budgets = {b._category: b for b in self.load_budgets()}
            budgets[category] = budget
            
            with file_handler(BUDGET_FILE, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['category', 'limit'])
                for b in budgets.values():
                    writer.writerow([b._category, b._limit])
            return budget
        except Exception as e:
            logging.error(f"Failed to set budget: {str(e)}")
            raise

    @log_action
    def delete_budget(self, category):
        budgets = [b for b in self.load_budgets() if b._category != category]
        
        try:
            with file_handler(BUDGET_FILE, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['category', 'limit'])
                for b in budgets:
                    writer.writerow([b._category, b._limit])
            return True
        except Exception as e:
            logging.error(f"Failed to delete budget: {str(e)}")
            raise

# Analysis and Reporting
class FinanceAnalyzer:
    def __init__(self, transaction_manager, budget_manager):
        self.tm = transaction_manager
        self.bm = budget_manager

    @log_action
    def generate_monthly_report(self):
        transactions = self.tm.load_transactions()
        if not transactions:
            return None

        df = pd.DataFrame([{
            'date': t._date,
            'amount': t._amount,
            'category': t._category,
            'type': t._trans_type,
            'description': t._description
        } for t in transactions])

        df['date'] = pd.to_datetime(df['date'])
        monthly_data = df.groupby([df['date'].dt.to_period('M'), 'type'])['amount'].sum().unstack(fill_value=0)
        monthly_data['savings'] = monthly_data.get('income', 0) - monthly_data.get('expense', 0)

        report_path = os.path.join(REPORTS_DIR, f"monthly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        monthly_data.to_csv(report_path)
        return report_path

    @log_action
    def generate_category_report(self):
        transactions = self.tm.load_transactions()
        if not transactions:
            return None

        df = pd.DataFrame([{
            'category': t._category,
            'amount': t._amount,
            'type': t._trans_type
        } for t in transactions])

        category_data = df.groupby(['category', 'type'])['amount'].sum().unstack(fill_value=0)
        category_data['net'] = category_data.get('income', 0) - category_data.get('expense', 0)

        report_path = os.path.join(REPORTS_DIR, f"category_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        category_data.to_csv(report_path)
        return report_path

    @log_action
    def generate_plots(self):
        transactions = self.tm.load_transactions()
        if not transactions:
            return None

        df = pd.DataFrame([{
            'date': t._date,
            'amount': t._amount,
            'category': t._category,
            'type': t._trans_type
        } for t in transactions])

        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M')
        df['day'] = df['date'].dt.day

        plots = {}
        
        # Monthly Trends Line Plot
        monthly_trends = df.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0)
        fig, ax = plt.subplots(figsize=(12, 6))
        for col in monthly_trends.columns:
            ax.plot(monthly_trends.index.astype(str), monthly_trends[col], label=col, marker='o')
        ax.set_title('Monthly Income vs Expense Trends')
        ax.set_xlabel('Month')
        ax.set_ylabel('Amount ($)')
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        plots['monthly_trends'] = self._fig_to_base64(fig)

        # Category Spending Pie Chart
        expense_data = df[df['type'] == 'expense'].groupby('category')['amount'].sum()
        if not expense_data.empty:
            fig, ax = plt.subplots(figsize=(10, 10))
            ax.pie(expense_data, labels=expense_data.index, autopct='%1.1f%%', startangle=90)
            ax.set_title('Category-Wise Spending Distribution')
            plots['category_spending'] = self._fig_to_base64(fig)

        # Budget Status Bar Chart
        budgets = self.bm.load_budgets()
        budget_data = []
        for budget in budgets:
            status = budget.check_limit([t for t in transactions if t._trans_type == 'expense'])
            budget_data.append({
                'category': budget._category,
                'limit': budget._limit,
                'spent': status['total'],
                'remaining': status['remaining']
            })
        
        if budget_data:
            budget_df = pd.DataFrame(budget_data)
            fig, ax = plt.subplots(figsize=(12, 6))
            budget_df.plot(x='category', y=['spent', 'remaining'], kind='bar', stacked=True, ax=ax)
            ax.set_title('Budget Status')
            ax.set_ylabel('Amount ($)')
            ax.legend(['Spent', 'Remaining'])
            plt.xticks(rotation=45)
            plots['budget_status'] = self._fig_to_base64(fig)

        # Daily Spending Trend
        daily_spending = df[df['type'] == 'expense'].groupby('day')['amount'].sum()
        if not daily_spending.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(daily_spending.index, daily_spending.values, color='red', marker='o')
            ax.set_title('Daily Spending Trend')
            ax.set_xlabel('Day of Month')
            ax.set_ylabel('Amount Spent ($)')
            ax.grid(True)
            plots['daily_spending'] = self._fig_to_base64(fig)

        return plots

    def _fig_to_base64(self, fig):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    @log_action
    def get_financial_summary(self):
        transactions = self.tm.load_transactions()
        if not transactions:
            return None

        incomes = [t._amount for t in transactions if t._trans_type == 'income']
        expenses = [t._amount for t in transactions if t._trans_type == 'expense']
        
        total_income = sum(incomes)
        total_expense = sum(expenses)
        net_savings = total_income - total_expense
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'net_savings': net_savings,
            'savings_rate': (net_savings / total_income * 100) if total_income > 0 else 0
        }

# Main Finance Tracker Class
class FinanceTracker:
    def __init__(self):
        self.transaction_manager = TransactionManager()
        self.budget_manager = BudgetManager()
        self.analyzer = FinanceAnalyzer(self.transaction_manager, self.budget_manager)

    @log_action
    def add_transaction(self, date, amount, category, trans_type, description=""):
        return self.transaction_manager.add_transaction(date, amount, category, trans_type, description)

    @log_action
    def get_transactions(self):
        return self.transaction_manager.load_transactions()

    @log_action
    def delete_transaction(self, trans_id):
        return self.transaction_manager.delete_transaction(trans_id)

    @log_action
    def set_budget(self, category, limit):
        return self.budget_manager.set_budget(category, limit)

    @log_action
    def get_budgets(self):
        return self.budget_manager.load_budgets()

    @log_action
    def delete_budget(self, category):
        return self.budget_manager.delete_budget(category)

    @log_action
    def get_monthly_report(self):
        return self.analyzer.generate_monthly_report()

    @log_action
    def get_category_report(self):
        return self.analyzer.generate_category_report()

    @log_action
    def get_visualizations(self):
        return self.analyzer.generate_plots()

    @log_action
    def get_budget_status(self):
        budgets = self.budget_manager.load_budgets()
        transactions = self.transaction_manager.load_transactions()
        expenses = [t for t in transactions if t._trans_type == 'expense']
        
        status = []
        for budget in budgets:
            budget_status = budget.check_limit(expenses)
            status.append({
                'category': budget._category,
                'limit': budget._limit,
                'spent': budget_status['total'],
                'remaining': budget_status['remaining'],
                'percentage': budget_status['percentage'],
                'exceeded': budget_status['exceeded']
            })
        return status

    @log_action
    def get_financial_summary(self):
        return self.analyzer.get_financial_summary()