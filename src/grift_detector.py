# ABOUTME: Grift detection engine for identifying suspicious transactions and wasteful spending
# ABOUTME: Finds recurring charges, duplicates, price increases, and suspicious merchants

from typing import List, Dict, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import difflib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GriftFlag:
    """Represents a grift detection flag"""

    def __init__(self, transaction_id: int, flag_type: str, description: str, severity: str = "medium"):
        self.transaction_id = transaction_id
        self.flag_type = flag_type
        self.description = description
        self.severity = severity

    def to_dict(self) -> Dict:
        return {
            "transaction_id": self.transaction_id,
            "flag_type": self.flag_type,
            "description": self.description,
            "severity": self.severity
        }


class GriftDetector:
    """Detects various types of grift and suspicious spending patterns"""

    def __init__(self, db):
        self.db = db

    def detect_all(self) -> List[GriftFlag]:
        """Run all grift detection algorithms"""
        logger.info("Running grift detection...")

        flags = []
        flags.extend(self.detect_recurring_charges())
        flags.extend(self.detect_duplicates())
        flags.extend(self.detect_price_increases())
        flags.extend(self.detect_suspicious_merchants())

        logger.info(f"Detected {len(flags)} potential grift items")
        return flags

    def detect_recurring_charges(self) -> List[GriftFlag]:
        """
        Detect recurring charges that appear monthly
        These could be forgotten subscriptions
        """
        flags = []
        transactions = self.db.get_transactions()

        # Group by merchant
        merchant_transactions = defaultdict(list)
        for txn in transactions:
            merchant_transactions[txn['merchant']].append(txn)

        # Look for monthly patterns
        for merchant, txns in merchant_transactions.items():
            if len(txns) < 2:
                continue

            # Sort by date
            txns_sorted = sorted(txns, key=lambda x: x['date'])

            # Check if transactions are roughly monthly
            is_recurring = True
            amounts = [txn['amount'] for txn in txns_sorted]
            avg_amount = sum(amounts) / len(amounts)

            # Check date intervals
            dates = [datetime.fromisoformat(txn['date']) for txn in txns_sorted]
            intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]

            # Monthly interval is ~28-35 days
            monthly_intervals = [25 <= interval <= 35 for interval in intervals]

            if sum(monthly_intervals) >= len(intervals) * 0.7:  # 70% of intervals are monthly
                # This is a recurring charge
                monthly_cost = avg_amount
                annual_cost = monthly_cost * 12

                severity = "low"
                if monthly_cost > 50:
                    severity = "medium"
                if monthly_cost > 100:
                    severity = "high"

                # Flag the most recent transaction
                latest_txn = txns_sorted[-1]

                description = (
                    f"Recurring charge: {merchant} appears {len(txns)} times. "
                    f"${monthly_cost:.2f}/month (${annual_cost:.2f}/year). "
                    f"Are you still using this service?"
                )

                flag = GriftFlag(
                    transaction_id=latest_txn['id'],
                    flag_type="recurring",
                    description=description,
                    severity=severity
                )
                flags.append(flag)

        return flags

    def detect_duplicates(self) -> List[GriftFlag]:
        """
        Detect duplicate charges (same merchant, same amount, within a short time window)
        Could indicate billing errors or fraud
        """
        flags = []
        transactions = self.db.get_transactions()

        # Sort by date
        transactions = sorted(transactions, key=lambda x: x['date'])

        # Check each transaction against recent transactions
        for i, txn in enumerate(transactions):
            txn_date = datetime.fromisoformat(txn['date'])

            # Look at transactions within 7 days
            for j in range(max(0, i-20), i):  # Look back up to 20 transactions
                other_txn = transactions[j]
                other_date = datetime.fromisoformat(other_txn['date'])

                days_apart = abs((txn_date - other_date).days)

                if days_apart > 7:
                    continue

                # Check if same merchant and similar amount
                if (txn['merchant'] == other_txn['merchant'] and
                    abs(txn['amount'] - other_txn['amount']) < 0.01):

                    description = (
                        f"Potential duplicate: {txn['merchant']} charged ${txn['amount']:.2f} "
                        f"on {txn['date']}, similar charge on {other_txn['date']} "
                        f"({days_apart} days apart). Verify this isn't a billing error."
                    )

                    flag = GriftFlag(
                        transaction_id=txn['id'],
                        flag_type="duplicate",
                        description=description,
                        severity="high"
                    )
                    flags.append(flag)

        return flags

    def detect_price_increases(self) -> List[GriftFlag]:
        """
        Detect when a recurring merchant increases their price
        This could be legitimate but worth reviewing
        """
        flags = []
        transactions = self.db.get_transactions()

        # Group by merchant
        merchant_transactions = defaultdict(list)
        for txn in transactions:
            merchant_transactions[txn['merchant']].append(txn)

        for merchant, txns in merchant_transactions.items():
            if len(txns) < 3:  # Need at least 3 transactions to detect a trend
                continue

            # Sort by date
            txns_sorted = sorted(txns, key=lambda x: x['date'])

            # Look for price increases
            for i in range(1, len(txns_sorted)):
                prev_amount = txns_sorted[i-1]['amount']
                curr_amount = txns_sorted[i]['amount']

                # If amount increased by more than $5 or 20%
                increase_amount = curr_amount - prev_amount
                increase_pct = (increase_amount / prev_amount * 100) if prev_amount > 0 else 0

                if increase_amount > 5 or increase_pct > 20:
                    description = (
                        f"Price increase detected: {merchant} increased from "
                        f"${prev_amount:.2f} to ${curr_amount:.2f} "
                        f"(+${increase_amount:.2f}, +{increase_pct:.1f}%). "
                        f"Were you notified?"
                    )

                    flag = GriftFlag(
                        transaction_id=txns_sorted[i]['id'],
                        flag_type="price_increase",
                        description=description,
                        severity="medium"
                    )
                    flags.append(flag)

        return flags

    def detect_suspicious_merchants(self) -> List[GriftFlag]:
        """
        Detect merchants with suspicious characteristics:
        - Generic/unclear names
        - Very small recurring charges (the $9.99 grift)
        - Unusual patterns
        """
        flags = []
        transactions = self.db.get_transactions()

        # Suspicious name patterns
        suspicious_patterns = [
            "WEB SERVICES",
            "ONLINE SERVICE",
            "SUBSCRIPTION",
            "MEMBERSHIP",
            "RECURRING",
            "AUTOPAY",
            "DIGITAL",
            "*TEMP",
        ]

        # Group by merchant
        merchant_transactions = defaultdict(list)
        for txn in transactions:
            merchant_transactions[txn['merchant']].append(txn)

        for merchant, txns in merchant_transactions.items():
            merchant_upper = merchant.upper()

            # Check for suspicious name patterns
            is_suspicious_name = any(pattern in merchant_upper for pattern in suspicious_patterns)

            # Check for small recurring charges
            if len(txns) >= 2:
                avg_amount = sum(t['amount'] for t in txns) / len(txns)
                is_small_recurring = 5 <= avg_amount <= 25

                if is_suspicious_name or is_small_recurring:
                    latest_txn = sorted(txns, key=lambda x: x['date'])[-1]

                    if is_suspicious_name:
                        description = (
                            f"Suspicious merchant name: '{merchant}' has a generic name. "
                            f"Charged {len(txns)} times, ${avg_amount:.2f} average. "
                            f"Can you identify this service?"
                        )
                        severity = "high" if is_small_recurring else "medium"
                    else:
                        description = (
                            f"Small recurring charge: {merchant} charges ~${avg_amount:.2f} "
                            f"regularly ({len(txns)} times). These small charges add up to "
                            f"${avg_amount * len(txns):.2f} total. Still needed?"
                        )
                        severity = "low"

                    flag = GriftFlag(
                        transaction_id=latest_txn['id'],
                        flag_type="suspicious",
                        description=description,
                        severity=severity
                    )
                    flags.append(flag)

        return flags

    def find_similar_merchants(self, threshold: float = 0.8) -> List[Tuple[str, str, float]]:
        """
        Find merchants with similar names (could be same vendor with different billing names)
        Returns list of (merchant1, merchant2, similarity_score) tuples
        """
        transactions = self.db.get_transactions()
        merchants = list(set(txn['merchant'] for txn in transactions))

        similar_pairs = []

        for i, merchant1 in enumerate(merchants):
            for merchant2 in merchants[i+1:]:
                # Use difflib to calculate similarity
                ratio = difflib.SequenceMatcher(None, merchant1.lower(), merchant2.lower()).ratio()

                if ratio >= threshold:
                    similar_pairs.append((merchant1, merchant2, ratio))

        return sorted(similar_pairs, key=lambda x: x[2], reverse=True)

    def analyze_spending_velocity(self) -> Dict:
        """
        Analyze spending patterns over time
        Helps identify if spending is increasing
        """
        transactions = self.db.get_transactions()

        if not transactions:
            return {}

        # Sort by date
        transactions = sorted(transactions, key=lambda x: x['date'])

        # Group by month
        monthly_spend = defaultdict(float)
        for txn in transactions:
            date = datetime.fromisoformat(txn['date'])
            month_key = date.strftime("%Y-%m")
            monthly_spend[month_key] += txn['amount']

        # Calculate trend
        months = sorted(monthly_spend.keys())
        if len(months) < 2:
            return {"months": months, "spending": [monthly_spend[m] for m in months]}

        amounts = [monthly_spend[m] for m in months]
        avg_spend = sum(amounts) / len(amounts)

        # Simple trend: compare first half to second half
        mid_point = len(amounts) // 2
        first_half_avg = sum(amounts[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = sum(amounts[mid_point:]) / (len(amounts) - mid_point)

        trend = "increasing" if second_half_avg > first_half_avg * 1.1 else \
                "decreasing" if second_half_avg < first_half_avg * 0.9 else "stable"

        return {
            "months": months,
            "spending": amounts,
            "average_monthly": avg_spend,
            "trend": trend,
            "first_half_avg": first_half_avg,
            "second_half_avg": second_half_avg
        }
