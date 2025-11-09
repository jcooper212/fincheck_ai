# ABOUTME: PDF parsing module for extracting transactions from bank and credit card statements
# ABOUTME: Handles multiple bank formats and normalizes transaction data

import pdfplumber
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Transaction:
    """Represents a single financial transaction"""

    def __init__(self, date: str, merchant: str, amount: float, transaction_type: str = "expense", description: str = ""):
        self.date = date
        self.merchant = merchant
        self.amount = amount
        self.transaction_type = transaction_type
        self.description = description

    def to_dict(self) -> Dict:
        return {
            "date": self.date,
            "merchant": self.merchant,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "description": self.description
        }


class PDFParser:
    """Parses bank/credit card statements from PDF files"""

    # Common date patterns
    DATE_PATTERNS = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # MM/DD/YYYY or MM-DD-YYYY
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',    # YYYY-MM-DD
        r'\b([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})\b',  # Jan 15, 2024
        r'\b(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})\b',    # 15 Jan 2024
        r'^(\d{2}/\d{2})\b',  # MM/DD (Chase format, start of line)
    ]

    # Common amount patterns
    AMOUNT_PATTERNS = [
        r'-?\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2}))',  # -$1,234.56 or $1,234.56 or 1,234.56
        r'(-?\d+\.\d{2})',  # -123.45 or 123.45
    ]

    def __init__(self):
        self.bank_name = None
        self.account_last4 = None
        self.account_type = "credit_card"  # Default to credit card
        self.statement_date = None

    def parse_pdf(self, pdf_path: Path) -> Tuple[Dict, List[Transaction]]:
        """
        Parse a bank statement PDF and extract transactions

        Returns:
            Tuple of (metadata dict, list of Transaction objects)
        """
        logger.info(f"Parsing PDF: {pdf_path}")

        transactions = []
        raw_text = ""

        with pdfplumber.open(pdf_path) as pdf:
            # Extract text from all pages
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"

            # Try to extract metadata from first page
            if pdf.pages:
                first_page = pdf.pages[0].extract_text()
                metadata = self._extract_metadata(first_page)
            else:
                metadata = {}

            # Try table extraction first (more structured)
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    table_transactions = self._parse_table(table)
                    transactions.extend(table_transactions)

        # If table extraction didn't work well, fall back to text parsing
        if len(transactions) < 5:  # Arbitrary threshold
            logger.info("Table extraction yielded few results, trying text parsing")
            text_transactions = self._parse_text(raw_text)
            if len(text_transactions) > len(transactions):
                transactions = text_transactions

        logger.info(f"Extracted {len(transactions)} transactions")

        # Store metadata
        self.bank_name = metadata.get("bank_name", "Unknown")
        self.account_last4 = metadata.get("account_last4")
        self.account_type = metadata.get("account_type", "credit_card")
        self.statement_date = metadata.get("statement_date", datetime.now().strftime("%Y-%m"))

        return metadata, transactions

    def _extract_metadata(self, first_page_text: str) -> Dict:
        """Extract metadata from the first page of the statement"""
        metadata = {}

        # Try to identify bank
        bank_patterns = {
            "Chase": r"Chase",
            "American Express": r"American\s+Express|AMEX",
            "Citi": r"Citibank|Citi",
            "Bank of America": r"Bank\s+of\s+America|BofA",
            "Wells Fargo": r"Wells\s+Fargo",
            "Capital One": r"Capital\s+One",
            "Discover": r"Discover",
        }

        for bank, pattern in bank_patterns.items():
            if re.search(pattern, first_page_text, re.IGNORECASE):
                metadata["bank_name"] = bank
                break

        # Try to extract account number (last 4 digits)
        account_match = re.search(r'(?:Account|Card)\s*(?:Number|#)?[:\s]*\*+(\d{4})', first_page_text, re.IGNORECASE)
        if account_match:
            metadata["account_last4"] = account_match.group(1)
        else:
            # Try alternative patterns
            account_match = re.search(r'ending\s+in\s+(\d{4})', first_page_text, re.IGNORECASE)
            if account_match:
                metadata["account_last4"] = account_match.group(1)
            else:
                # Try XXXX XXXX XXXX #### pattern (Chase format)
                account_match = re.search(r'XXXX\s+XXXX\s+XXXX\s+(\d{4})', first_page_text)
                if account_match:
                    metadata["account_last4"] = account_match.group(1)

        # Try to extract statement date
        date_patterns = [
            r'Statement\s+(?:Date|Period)[:\s]*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})',
            r'Statement\s+(?:Date|Period)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:Closing|Statement)\s+Date[:\s]*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})',
            r'(?:Opening|Closing)\s+Date\s+(\d{2}/\d{2}/\d{2})',  # Chase format
            r'Statement Date:\s*(\d{2}/\d{2}/\d{2})',  # Alternative Chase format
        ]

        for pattern in date_patterns:
            match = re.search(pattern, first_page_text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                metadata["statement_date"] = self._normalize_date(date_str)
                break

        # Detect account type (checking, savings, credit card)
        account_type = "credit_card"  # Default

        # Look for checking account indicators
        if re.search(r'checking|total\s+checking', first_page_text, re.IGNORECASE):
            account_type = "checking"
        # Look for savings account indicators
        elif re.search(r'savings|total\s+savings', first_page_text, re.IGNORECASE):
            account_type = "savings"
        # Credit card indicators (more explicit)
        elif re.search(r'credit\s+card|card\s+account|new\s+balance|credit\s+limit', first_page_text, re.IGNORECASE):
            account_type = "credit_card"

        metadata["account_type"] = account_type

        return metadata

    def _parse_table(self, table: List[List[str]]) -> List[Transaction]:
        """Parse transactions from a table structure"""
        transactions = []

        if not table or len(table) < 2:
            return transactions

        # Try to identify column indices
        header = table[0] if table else []
        date_col = None
        merchant_col = None
        amount_col = None

        for i, cell in enumerate(header):
            if not cell:
                continue
            cell_lower = cell.lower()
            if any(word in cell_lower for word in ["date", "trans", "post"]):
                date_col = i
            elif any(word in cell_lower for word in ["description", "merchant", "payee"]):
                merchant_col = i
            elif any(word in cell_lower for word in ["amount", "charge", "payment"]):
                amount_col = i

        # If we couldn't identify columns from header, guess based on data patterns
        if date_col is None or merchant_col is None or amount_col is None:
            date_col, merchant_col, amount_col = self._guess_columns(table)

        # Parse rows
        for row in table[1:]:  # Skip header
            if len(row) < 2:
                continue

            try:
                date = self._extract_date(row[date_col] if date_col is not None else row[0])
                merchant = row[merchant_col] if merchant_col is not None else row[1]
                amount = self._extract_amount(row[amount_col] if amount_col is not None else row[-1])

                if date and merchant and amount is not None:
                    merchant = self._clean_merchant_name(merchant)
                    # Determine transaction type
                    row_text = ' '.join(str(cell) for cell in row if cell)
                    transaction_type = self._determine_transaction_type(row_text, amount, merchant)

                    transaction = Transaction(
                        date=date,
                        merchant=merchant,
                        amount=abs(amount),
                        transaction_type=transaction_type,
                        description=merchant
                    )
                    transactions.append(transaction)
            except (IndexError, ValueError) as e:
                logger.debug(f"Skipping row due to parsing error: {e}")
                continue

        return transactions

    def _parse_text(self, text: str) -> List[Transaction]:
        """Parse transactions from raw text (fallback method)"""
        transactions = []
        lines = text.split('\n')

        for line in lines:
            # Look for lines with date + amount pattern
            date = self._extract_date(line)
            amount = self._extract_amount(line)

            if date and amount is not None:
                # Extract merchant (text between date and amount)
                merchant = self._extract_merchant_from_line(line, date)
                if merchant:
                    merchant = self._clean_merchant_name(merchant)
                    # Determine transaction type
                    transaction_type = self._determine_transaction_type(line, amount, merchant)

                    transaction = Transaction(
                        date=date,
                        merchant=merchant,
                        amount=abs(amount),
                        transaction_type=transaction_type,
                        description=merchant
                    )
                    transactions.append(transaction)

        return transactions

    def _guess_columns(self, table: List[List[str]]) -> Tuple[int, int, int]:
        """Guess column indices based on data patterns"""
        if not table or len(table) < 2:
            return 0, 1, -1

        # Sample first few data rows
        sample_rows = table[1:min(6, len(table))]

        date_col = None
        amount_col = None

        for i in range(len(sample_rows[0])):
            col_values = [row[i] if i < len(row) else "" for row in sample_rows]

            # Check if this column contains dates
            date_matches = sum(1 for val in col_values if self._extract_date(val))
            if date_matches >= len(col_values) // 2:
                date_col = i

            # Check if this column contains amounts
            amount_matches = sum(1 for val in col_values if self._extract_amount(val) is not None)
            if amount_matches >= len(col_values) // 2:
                amount_col = i

        # Merchant is likely in the middle
        date_col = date_col if date_col is not None else 0
        amount_col = amount_col if amount_col is not None else -1
        merchant_col = 1 if date_col == 0 else 0

        return date_col, merchant_col, amount_col

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract and normalize date from text"""
        if not text:
            return None

        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                return self._normalize_date(date_str)

        return None

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to YYYY-MM-DD format"""
        # Handle MM/DD format (Chase statements) - infer year from statement date
        if re.match(r'^\d{2}/\d{2}$', date_str.strip()):
            # Extract year from statement_date if available
            year = datetime.now().year
            if self.statement_date:
                try:
                    year = int(self.statement_date.split('-')[0])
                except (ValueError, IndexError):
                    pass

            # Add year to date_str
            date_str = f"{date_str}/{year}"

        # Try various formats
        formats = [
            "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y",
            "%Y-%m-%d", "%Y/%m/%d",
            "%b %d, %Y", "%b %d %Y", "%d %b %Y",
            "%B %d, %Y", "%B %d %Y", "%d %B %Y"
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # If all else fails, return original
        return date_str

    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract amount from text"""
        if not text:
            return None

        # Save the original text to check for leading negative sign
        original_text = text

        # Remove common non-amount characters
        text = text.replace('$', '').replace('(', '-').replace(')', '').strip()

        for pattern in self.AMOUNT_PATTERNS:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    # Check if there was a negative sign before the match
                    if '-' in original_text[:original_text.find(amount_str.replace(',', ''))]:
                        amount = -abs(amount)
                    return amount
                except ValueError:
                    continue

        return None

    def _extract_merchant_from_line(self, line: str, date: str) -> Optional[str]:
        """Extract merchant name from a transaction line"""
        # Remove the date from the line (handle both full date and MM/DD format)
        merchant = line.replace(date, '', 1)

        # Also remove MM/DD pattern if it's still there
        merchant = re.sub(r'^\d{2}/\d{2}\s*', '', merchant)

        # Remove amount patterns from the end
        for pattern in self.AMOUNT_PATTERNS:
            merchant = re.sub(pattern + r'\s*$', '', merchant)

        merchant = merchant.strip()
        return merchant if merchant else None

    def _determine_transaction_type(self, row_text: str, amount: float, merchant: str) -> str:
        """
        Determine if transaction is income or expense based on indicators

        Args:
            row_text: Raw text of the transaction row
            amount: Transaction amount (may be negative)
            merchant: Merchant name

        Returns:
            'income' or 'expense'
        """
        # Credit cards are always expenses
        if self.account_type == "credit_card":
            return "expense"

        # For bank accounts, look for indicators
        row_lower = row_text.lower()

        # Income indicators
        income_keywords = [
            'deposit', 'credit', 'payroll', 'salary', 'direct dep',
            'transfer from', 'interest', 'dividend', 'refund',
            'reimbursement', 'payment received', 'incoming'
        ]

        # Expense indicators
        expense_keywords = [
            'debit', 'withdrawal', 'purchase', 'payment to',
            'transfer to', 'fee', 'charge', 'atm'
        ]

        # Check for income keywords
        if any(keyword in row_lower for keyword in income_keywords):
            return "income"

        # Check for expense keywords
        if any(keyword in row_lower for keyword in expense_keywords):
            return "expense"

        # If amount is negative in a bank statement, it's likely an expense
        if amount < 0:
            return "expense"

        # If amount is positive and in bank account, likely income
        if self.account_type in ["checking", "savings"]:
            return "income" if amount > 0 else "expense"

        # Default to expense
        return "expense"

    def _clean_merchant_name(self, merchant: str) -> str:
        """Clean and normalize merchant name"""
        # Remove extra whitespace
        merchant = ' '.join(merchant.split())

        # Remove common suffixes
        suffixes_to_remove = [
            r'\s+#\d+$',  # Store numbers like "#1234"
            r'\s+\d{10,}$',  # Long numbers
            r'\s+\*+\d+$',  # Masked numbers
        ]

        for suffix in suffixes_to_remove:
            merchant = re.sub(suffix, '', merchant)

        return merchant.strip()


def parse_statement(pdf_path: Path) -> Tuple[Dict, List[Dict]]:
    """
    Convenience function to parse a statement and return dicts

    Args:
        pdf_path: Path to PDF file

    Returns:
        Tuple of (metadata dict, list of transaction dicts)
    """
    parser = PDFParser()
    metadata, transactions = parser.parse_pdf(pdf_path)

    # Add parser's extracted metadata
    metadata.update({
        "bank_name": parser.bank_name,
        "account_last4": parser.account_last4,
        "account_type": parser.account_type,
        "statement_date": parser.statement_date,
    })

    transaction_dicts = [t.to_dict() for t in transactions]

    return metadata, transaction_dicts
