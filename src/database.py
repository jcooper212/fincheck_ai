# ABOUTME: SQLite database schema and operations for FinCheck AI
# ABOUTME: Manages transactions, statements, grift flags, and categories

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

DB_PATH = Path("data/fincheck.db")


class Database:
    """Manages SQLite database for financial transactions and analysis"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Statements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name TEXT NOT NULL,
                account_last4 TEXT,
                account_type TEXT DEFAULT 'credit_card',
                statement_date TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(bank_name, statement_date, account_last4)
            )
        """)

        # Add account_type column if it doesn't exist (for migration)
        try:
            cursor.execute("ALTER TABLE statements ADD COLUMN account_type TEXT DEFAULT 'credit_card'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statement_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                merchant TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT DEFAULT 'expense',
                category TEXT,
                description TEXT,
                metadata TEXT,
                FOREIGN KEY (statement_id) REFERENCES statements(id)
            )
        """)

        # Add transaction_type column if it doesn't exist (for migration)
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN transaction_type TEXT DEFAULT 'expense'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Grift flags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grift_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                flag_type TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                dismissed BOOLEAN DEFAULT 0,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            )
        """)

        # Categories table for custom user-defined categories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                keywords TEXT,
                parent_category TEXT
            )
        """)

        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_date
            ON transactions(date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_merchant
            ON transactions(merchant)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_category
            ON transactions(category)
        """)

        conn.commit()
        conn.close()

    def add_statement(self, bank_name: str, statement_date: str, pdf_path: str,
                     account_last4: Optional[str] = None, account_type: str = 'credit_card') -> int:
        """Add a new statement record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO statements (bank_name, account_last4, account_type, statement_date, pdf_path)
                VALUES (?, ?, ?, ?, ?)
            """, (bank_name, account_last4, account_type, statement_date, pdf_path))

            statement_id = cursor.lastrowid
            conn.commit()
            return statement_id
        except sqlite3.IntegrityError:
            # Statement already exists, return existing ID
            cursor.execute("""
                SELECT id FROM statements
                WHERE bank_name = ? AND statement_date = ? AND account_last4 = ?
            """, (bank_name, statement_date, account_last4))
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def add_transaction(self, statement_id: int, date: str, merchant: str, amount: float,
                       transaction_type: str = 'expense', category: Optional[str] = None,
                       description: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        """Add a new transaction"""
        conn = self.get_connection()
        cursor = conn.cursor()

        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute("""
            INSERT INTO transactions (statement_id, date, merchant, amount, transaction_type, category, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (statement_id, date, merchant, amount, transaction_type, category, description, metadata_json))

        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return transaction_id

    def add_grift_flag(self, transaction_id: int, flag_type: str, description: str,
                      severity: str = "medium") -> int:
        """Add a grift flag to a transaction"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO grift_flags (transaction_id, flag_type, description, severity)
            VALUES (?, ?, ?, ?)
        """, (transaction_id, flag_type, description, severity))

        flag_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return flag_id

    def get_transactions(self, filters: Optional[Dict] = None,
                        limit: Optional[int] = None) -> List[Dict]:
        """Get transactions with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT t.*, s.bank_name, s.account_last4
            FROM transactions t
            JOIN statements s ON t.statement_id = s.id
            WHERE 1=1
        """
        params = []

        if filters:
            if 'merchant' in filters:
                query += " AND t.merchant LIKE ?"
                params.append(f"%{filters['merchant']}%")
            if 'category' in filters:
                query += " AND t.category = ?"
                params.append(filters['category'])
            if 'date_from' in filters:
                query += " AND t.date >= ?"
                params.append(filters['date_from'])
            if 'date_to' in filters:
                query += " AND t.date <= ?"
                params.append(filters['date_to'])
            if 'min_amount' in filters:
                query += " AND t.amount >= ?"
                params.append(filters['min_amount'])
            if 'max_amount' in filters:
                query += " AND t.amount <= ?"
                params.append(filters['max_amount'])

        query += " ORDER BY t.date DESC"

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_transactions_with_grift_flags(self) -> List[Dict]:
        """Get all transactions that have grift flags"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.*, s.bank_name, s.account_last4,
                   GROUP_CONCAT(g.flag_type || ': ' || g.description, '; ') as flags
            FROM transactions t
            JOIN statements s ON t.statement_id = s.id
            JOIN grift_flags g ON t.id = g.transaction_id
            WHERE g.dismissed = 0
            GROUP BY t.id
            ORDER BY t.date DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_category_breakdown(self, date_from: Optional[str] = None,
                               date_to: Optional[str] = None) -> List[Dict]:
        """Get spending breakdown by category"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT category, COUNT(*) as transaction_count, SUM(amount) as total_amount
            FROM transactions
            WHERE 1=1
        """
        params = []

        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += " GROUP BY category ORDER BY total_amount DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_top_merchants(self, n: int = 10, date_from: Optional[str] = None,
                         date_to: Optional[str] = None) -> List[Dict]:
        """Get top N merchants by total spending"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT merchant, COUNT(*) as transaction_count, SUM(amount) as total_amount
            FROM transactions
            WHERE 1=1
        """
        params = []

        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += " GROUP BY merchant ORDER BY total_amount DESC LIMIT ?"
        params.append(n)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_recurring_transactions(self, min_occurrences: int = 2) -> List[Dict]:
        """Find recurring transactions (same merchant appearing multiple times)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT merchant,
                   COUNT(*) as occurrence_count,
                   AVG(amount) as avg_amount,
                   MIN(amount) as min_amount,
                   MAX(amount) as max_amount,
                   GROUP_CONCAT(date, ', ') as dates
            FROM transactions
            GROUP BY merchant
            HAVING COUNT(*) >= ?
            ORDER BY occurrence_count DESC, avg_amount DESC
        """, (min_occurrences,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_transaction_category(self, transaction_id: int, category: str):
        """Update the category of a transaction"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE transactions SET category = ? WHERE id = ?
        """, (category, transaction_id))

        conn.commit()
        conn.close()

    def dismiss_grift_flag(self, flag_id: int):
        """Mark a grift flag as dismissed"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE grift_flags SET dismissed = 1 WHERE id = ?
        """, (flag_id,))

        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM statements")
        statement_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transactions")
        transaction_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM grift_flags WHERE dismissed = 0")
        grift_count = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(amount) FROM transactions")
        total_spend = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT MIN(date), MAX(date) FROM transactions")
        date_range = cursor.fetchone()

        conn.close()

        return {
            "statements": statement_count,
            "transactions": transaction_count,
            "grift_flags": grift_count,
            "total_spend": total_spend,
            "date_range": {
                "start": date_range[0] if date_range else None,
                "end": date_range[1] if date_range else None
            }
        }

    def get_income_vs_expenses(self, date_from: Optional[str] = None,
                              date_to: Optional[str] = None) -> Dict[str, float]:
        """Get income vs expenses breakdown"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT transaction_type, SUM(amount) as total
            FROM transactions
            WHERE 1=1
        """
        params = []

        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += " GROUP BY transaction_type"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        result = {"income": 0.0, "expense": 0.0}
        for row in rows:
            result[row['transaction_type']] = row['total']

        result['net'] = result['income'] - result['expense']
        return result

    def get_cash_flow_by_month(self) -> List[Dict]:
        """Get cash flow summary grouped by month"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                substr(date, 1, 7) as month,
                SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as expense
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            result.append({
                "month": row['month'],
                "income": row['income'],
                "expense": row['expense'],
                "net": row['income'] - row['expense']
            })

        return result

    def get_all_accounts(self) -> List[Dict]:
        """Get all accounts with transaction counts"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                s.id,
                s.bank_name,
                s.account_last4,
                s.account_type,
                COUNT(t.id) as transaction_count,
                SUM(CASE WHEN t.transaction_type = 'income' THEN t.amount ELSE 0 END) as total_income,
                SUM(CASE WHEN t.transaction_type = 'expense' THEN t.amount ELSE 0 END) as total_expense
            FROM statements s
            LEFT JOIN transactions t ON s.id = t.statement_id
            GROUP BY s.id, s.bank_name, s.account_last4, s.account_type
            ORDER BY total_expense DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_spending_by_account(self, month: Optional[str] = None) -> List[Dict]:
        """Get spending breakdown by account, optionally filtered by month"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                s.bank_name,
                s.account_last4,
                s.account_type,
                COUNT(t.id) as transaction_count,
                SUM(CASE WHEN t.transaction_type = 'income' THEN t.amount ELSE 0 END) as total_income,
                SUM(CASE WHEN t.transaction_type = 'expense' THEN t.amount ELSE 0 END) as total_expense,
                AVG(CASE WHEN t.transaction_type = 'expense' THEN t.amount ELSE NULL END) as avg_expense
            FROM statements s
            LEFT JOIN transactions t ON s.id = t.statement_id
            WHERE 1=1
        """
        params = []

        if month:
            query += " AND substr(t.date, 1, 7) = ?"
            params.append(month)

        query += " GROUP BY s.bank_name, s.account_last4, s.account_type ORDER BY total_expense DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_transactions_by_statement_month_merchant(self,
                                                     month_filter: Optional[str] = None,
                                                     bank_filter: Optional[str] = None) -> List[Dict]:
        """
        Get transactions grouped by statement, month, and merchant
        Returns structured data for hierarchical display

        Args:
            month_filter: Optional YYYY-MM format to filter by month
            bank_filter: Optional bank name to filter by

        Returns:
            List of statement dicts with nested month/merchant/transaction structure
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Build the WHERE clause for filters
        where_clauses = []
        params = []

        if month_filter:
            where_clauses.append("substr(t.date, 1, 7) = ?")
            params.append(month_filter)

        if bank_filter:
            where_clauses.append("s.bank_name LIKE ?")
            params.append(f"%{bank_filter}%")

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        # Get all statements
        cursor.execute(f"""
            SELECT DISTINCT
                s.id,
                s.bank_name,
                s.account_last4,
                s.account_type,
                s.statement_date
            FROM statements s
            JOIN transactions t ON s.id = t.statement_id
            WHERE 1=1{where_sql}
            ORDER BY s.statement_date DESC
        """, params)

        statements = [dict(row) for row in cursor.fetchall()]

        # For each statement, get months
        for statement in statements:
            month_params = [statement['id']]
            month_query = """
                SELECT DISTINCT substr(date, 1, 7) as month
                FROM transactions
                WHERE statement_id = ?
            """
            if month_filter:
                month_query += " AND substr(date, 1, 7) = ?"
                month_params.append(month_filter)
            month_query += " ORDER BY month DESC"

            cursor.execute(month_query, month_params)

            months = [row['month'] for row in cursor.fetchall()]
            statement['months'] = []

            # For each month, get merchants with their transactions
            for month in months:
                cursor.execute("""
                    SELECT
                        merchant,
                        category,
                        COUNT(*) as transaction_count,
                        SUM(amount) as total_amount
                    FROM transactions
                    WHERE statement_id = ? AND substr(date, 1, 7) = ?
                    GROUP BY merchant, category
                    ORDER BY total_amount DESC
                """, (statement['id'], month))

                merchants = [dict(row) for row in cursor.fetchall()]

                # For each merchant, get individual transactions
                for merchant_data in merchants:
                    cursor.execute("""
                        SELECT
                            id,
                            date,
                            amount,
                            transaction_type,
                            category,
                            description
                        FROM transactions
                        WHERE statement_id = ?
                          AND substr(date, 1, 7) = ?
                          AND merchant = ?
                        ORDER BY date ASC
                    """, (statement['id'], month, merchant_data['merchant']))

                    merchant_data['transactions'] = [dict(row) for row in cursor.fetchall()]

                # Calculate month totals
                month_total = sum(m['total_amount'] for m in merchants)
                month_count = sum(m['transaction_count'] for m in merchants)

                statement['months'].append({
                    'month': month,
                    'total': month_total,
                    'transaction_count': month_count,
                    'merchants': merchants
                })

            # Calculate statement totals
            statement['total'] = sum(m['total'] for m in statement['months'])
            statement['transaction_count'] = sum(m['transaction_count'] for m in statement['months'])

        conn.close()
        return statements

    def is_pdf_already_uploaded(self, pdf_path: str) -> bool:
        """Check if a PDF file has already been uploaded"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM statements WHERE pdf_path = ?
        """, (pdf_path,))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    def get_all_uploaded_pdfs(self) -> List[str]:
        """Get list of all uploaded PDF paths"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT pdf_path FROM statements")
        rows = cursor.fetchall()
        conn.close()

        return [row['pdf_path'] for row in rows]
