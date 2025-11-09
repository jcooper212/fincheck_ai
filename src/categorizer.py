# ABOUTME: Transaction categorization engine using rule-based and LLM-based approaches
# ABOUTME: Automatically assigns spending categories and provides analytics

from typing import List, Dict, Optional
import re
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Categorizer:
    """Categorizes transactions into spending categories"""

    # Category mapping with keywords
    CATEGORY_RULES = {
        "Food & Dining": [
            "restaurant", "cafe", "coffee", "starbucks", "chipotle", "mcdonalds",
            "burger", "pizza", "sushi", "diner", "grill", "kitchen", "bistro",
            "food", "grocery", "whole foods", "trader joe", "safeway", "kroger",
            "walmart", "target", "costco", "publix", "wegmans", "albertsons",
            "uber eats", "doordash", "grubhub", "postmates", "delivery"
        ],
        "Transportation": [
            "uber", "lyft", "taxi", "gas", "fuel", "shell", "chevron", "exxon",
            "bp", "mobil", "parking", "metro", "transit", "train", "bus",
            "airline", "flight", "car rental", "hertz", "enterprise", "avis"
        ],
        "Entertainment": [
            "netflix", "spotify", "hulu", "disney", "hbo", "amazon prime",
            "apple music", "youtube", "twitch", "movie", "theater", "cinema",
            "concert", "ticket", "event", "game", "playstation", "xbox", "steam",
            "bar", "club", "lounge"
        ],
        "Shopping": [
            "amazon", "ebay", "etsy", "shop", "store", "mall", "boutique",
            "clothing", "apparel", "fashion", "shoes", "nike", "adidas",
            "electronics", "best buy", "apple store", "furniture", "home depot",
            "lowes", "ikea", "department"
        ],
        "Subscriptions & Memberships": [
            "subscription", "membership", "gym", "fitness", "planet fitness",
            "la fitness", "24 hour", "gold's gym", "crossfit", "yoga",
            "monthly", "annual fee", "renewal"
        ],
        "Utilities & Bills": [
            "electric", "power", "gas", "water", "internet", "cable", "phone",
            "wireless", "verizon", "at&t", "t-mobile", "comcast", "spectrum",
            "utility", "bill payment"
        ],
        "Healthcare": [
            "pharmacy", "cvs", "walgreens", "rite aid", "medical", "doctor",
            "hospital", "clinic", "dental", "dentist", "health", "urgent care"
        ],
        "Travel": [
            "hotel", "motel", "resort", "airbnb", "vrbo", "booking", "expedia",
            "airline", "airport", "tsa", "tourism"
        ],
        "Finance & Insurance": [
            "insurance", "bank fee", "atm", "interest", "payment", "loan",
            "credit card", "finance charge", "late fee"
        ],
        "Personal Care": [
            "salon", "spa", "barber", "hair", "nail", "beauty", "cosmetic"
        ],
    }

    def __init__(self, llm_client=None):
        """
        Initialize categorizer

        Args:
            llm_client: Optional OpenAI client for LLM-based categorization fallback
        """
        self.llm_client = llm_client
        self._build_keyword_index()

    def _build_keyword_index(self):
        """Build reverse index of keywords to categories for faster lookup"""
        self.keyword_to_category = {}
        for category, keywords in self.CATEGORY_RULES.items():
            for keyword in keywords:
                self.keyword_to_category[keyword.lower()] = category

    def categorize_transaction(self, merchant: str, description: str = "") -> str:
        """
        Categorize a single transaction

        Args:
            merchant: Merchant name
            description: Optional transaction description

        Returns:
            Category name
        """
        # Combine merchant and description for matching
        text = f"{merchant} {description}".lower()

        # Try rule-based matching first
        for keyword, category in self.keyword_to_category.items():
            if keyword in text:
                return category

        # If no rule matches and we have an LLM client, use it
        if self.llm_client:
            return self._categorize_with_llm(merchant, description)

        # Default category
        return "Other"

    def _categorize_with_llm(self, merchant: str, description: str) -> str:
        """
        Use LLM to categorize when rules don't match

        Args:
            merchant: Merchant name
            description: Transaction description

        Returns:
            Category name
        """
        if not self.llm_client:
            return "Other"

        try:
            categories_list = ", ".join(self.CATEGORY_RULES.keys())

            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a financial transaction categorizer. "
                                 f"Categorize transactions into one of these categories: {categories_list}, or 'Other'. "
                                 f"Respond with ONLY the category name, nothing else."
                    },
                    {
                        "role": "user",
                        "content": f"Categorize this transaction:\nMerchant: {merchant}\nDescription: {description}"
                    }
                ],
                temperature=0.3,
                max_tokens=20
            )

            category = response.choices[0].message.content.strip()

            # Validate that it's a real category
            if category in self.CATEGORY_RULES or category == "Other":
                return category
            else:
                logger.warning(f"LLM returned invalid category '{category}', using 'Other'")
                return "Other"

        except Exception as e:
            logger.error(f"Error categorizing with LLM: {e}")
            return "Other"

    def categorize_batch(self, transactions: List[Dict]) -> List[Dict]:
        """
        Categorize a batch of transactions

        Args:
            transactions: List of transaction dicts

        Returns:
            Same list with 'category' field added/updated
        """
        for txn in transactions:
            if not txn.get('category') or txn['category'] == 'Other':
                merchant = txn.get('merchant', '')
                description = txn.get('description', '')
                txn['category'] = self.categorize_transaction(merchant, description)

        return transactions


class Analytics:
    """Provides spending analytics and insights"""

    def __init__(self, db):
        self.db = db

    def get_category_breakdown(self, date_from: Optional[str] = None,
                               date_to: Optional[str] = None) -> List[Dict]:
        """Get spending breakdown by category"""
        return self.db.get_category_breakdown(date_from, date_to)

    def get_top_merchants(self, n: int = 10, date_from: Optional[str] = None,
                         date_to: Optional[str] = None) -> List[Dict]:
        """Get top N merchants by spending"""
        return self.db.get_top_merchants(n, date_from, date_to)

    def get_monthly_trends(self) -> Dict:
        """Analyze month-over-month spending trends"""
        transactions = self.db.get_transactions()

        if not transactions:
            return {}

        # Group by month and category
        monthly_data = defaultdict(lambda: defaultdict(float))

        for txn in transactions:
            date_parts = txn['date'].split('-')
            if len(date_parts) >= 2:
                month_key = f"{date_parts[0]}-{date_parts[1]}"
                category = txn.get('category', 'Other')
                monthly_data[month_key][category] += txn['amount']

        # Calculate totals and growth
        months = sorted(monthly_data.keys())
        monthly_totals = {month: sum(monthly_data[month].values()) for month in months}

        # Calculate month-over-month growth
        mom_growth = {}
        for i in range(1, len(months)):
            prev_month = months[i-1]
            curr_month = months[i]
            prev_total = monthly_totals[prev_month]
            curr_total = monthly_totals[curr_month]

            if prev_total > 0:
                growth = ((curr_total - prev_total) / prev_total) * 100
                mom_growth[curr_month] = growth

        return {
            "months": months,
            "monthly_totals": monthly_totals,
            "monthly_by_category": dict(monthly_data),
            "mom_growth": mom_growth
        }

    def get_spending_summary(self, date_from: Optional[str] = None,
                            date_to: Optional[str] = None) -> Dict:
        """Get comprehensive spending summary"""
        filters = {}
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to

        transactions = self.db.get_transactions(filters)

        if not transactions:
            return {
                "total_transactions": 0,
                "total_spend": 0,
                "average_transaction": 0,
                "categories": [],
                "top_merchants": []
            }

        total_spend = sum(txn['amount'] for txn in transactions)
        avg_transaction = total_spend / len(transactions)

        # Get largest transaction
        largest = max(transactions, key=lambda x: x['amount'])

        # Category breakdown
        category_breakdown = self.get_category_breakdown(date_from, date_to)

        # Top merchants
        top_merchants = self.get_top_merchants(5, date_from, date_to)

        return {
            "total_transactions": len(transactions),
            "total_spend": total_spend,
            "average_transaction": avg_transaction,
            "largest_transaction": {
                "merchant": largest['merchant'],
                "amount": largest['amount'],
                "date": largest['date']
            },
            "categories": category_breakdown,
            "top_merchants": top_merchants
        }

    def find_savings_opportunities(self) -> List[Dict]:
        """
        Identify potential savings opportunities

        Returns:
            List of savings opportunity dicts with recommendations
        """
        opportunities = []

        # Get recurring transactions
        recurring = self.db.get_recurring_transactions(min_occurrences=3)

        for merchant_data in recurring:
            merchant = merchant_data['merchant']
            avg_amount = merchant_data['avg_amount']
            count = merchant_data['occurrence_count']
            annual_cost = avg_amount * 12  # Rough estimate

            # High-cost recurring charges
            if avg_amount > 50:
                opportunities.append({
                    "type": "high_recurring",
                    "merchant": merchant,
                    "monthly_cost": avg_amount,
                    "annual_cost": annual_cost,
                    "recommendation": f"Review {merchant} subscription (${avg_amount:.2f}/mo). "
                                    f"Can you downgrade or cancel? Potential savings: ${annual_cost:.2f}/year"
                })

        # Analyze food spending
        food_txns = self.db.get_transactions({"category": "Food & Dining"})
        if food_txns:
            total_food = sum(t['amount'] for t in food_txns)
            delivery_keywords = ['uber eats', 'doordash', 'grubhub', 'postmates', 'delivery']
            delivery_txns = [t for t in food_txns
                           if any(kw in t['merchant'].lower() for kw in delivery_keywords)]
            delivery_spend = sum(t['amount'] for t in delivery_txns)

            if delivery_spend > 200:  # Threshold
                opportunities.append({
                    "type": "delivery_food",
                    "category": "Food & Dining",
                    "current_spend": delivery_spend,
                    "recommendation": f"You spent ${delivery_spend:.2f} on food delivery. "
                                    f"Cooking at home or picking up orders could save ~${delivery_spend * 0.3:.2f}"
                })

        # Analyze transportation
        transport_txns = self.db.get_transactions({"category": "Transportation"})
        if transport_txns:
            rideshare_keywords = ['uber', 'lyft', 'taxi']
            rideshare_txns = [t for t in transport_txns
                            if any(kw in t['merchant'].lower() for kw in rideshare_keywords)]
            rideshare_spend = sum(t['amount'] for t in rideshare_txns)

            if rideshare_spend > 300:
                opportunities.append({
                    "type": "rideshare",
                    "category": "Transportation",
                    "current_spend": rideshare_spend,
                    "recommendation": f"You spent ${rideshare_spend:.2f} on rideshares. "
                                    f"Could public transit or bike save ~${rideshare_spend * 0.5:.2f}?"
                })

        return opportunities
