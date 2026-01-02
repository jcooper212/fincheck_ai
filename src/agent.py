##### ABOUTME: AI chat agent for conversational financial analysis with function calling
# ABOUTME: Provides tools for querying transactions, detecting grift, and generating insights

from typing import List, Dict, Any, Optional
import json
from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinCheckAgent:
    """AI agent for financial analysis and grift detection"""

    def __init__(self, db, grift_detector, analytics, openai_api_key: str):
        self.db = db
        self.grift_detector = grift_detector
        self.analytics = analytics
        self.client = OpenAI(api_key=openai_api_key)
        self.history = []

        # Define available tools
        self.tools_definition = self._create_tools_definition()
        self.tool_functions = self._create_tool_functions()

    def _create_tools_definition(self) -> List[Dict]:
        """Create OpenAI function calling definitions"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_transactions",
                    "description": "Query and search transactions with optional filters",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "merchant": {"type": "string", "description": "Merchant name to search for"},
                            "category": {"type": "string", "description": "Exact category name"},
                            "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                            "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                            "limit": {"type": "integer", "description": "Maximum number of results"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_grift",
                    "description": "Detect potential grift, fraud, forgotten subscriptions, and suspicious charges",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recurring_charges",
                    "description": "List all recurring monthly charges and subscriptions",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_category_breakdown",
                    "description": "Get spending breakdown by category with percentages",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                            "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_top_merchants",
                    "description": "Get top N merchants by total spending amount",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "n": {"type": "integer", "description": "Number of top merchants to return"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_spending_summary",
                    "description": "Get overall spending statistics and summary",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_savings_opportunities",
                    "description": "Identify potential savings opportunities and recommendations",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_monthly_trends",
                    "description": "Analyze month-over-month spending trends and patterns",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def _create_tool_functions(self) -> Dict:
        """Create mapping of function names to actual functions"""

        def query_transactions(merchant=None, category=None, date_from=None, date_to=None, limit=20):
            try:
                filters = {}
                if merchant:
                    filters['merchant'] = merchant
                if category:
                    filters['category'] = category
                if date_from:
                    filters['date_from'] = date_from
                if date_to:
                    filters['date_to'] = date_to

                transactions = self.db.get_transactions(filters, limit=limit)

                if not transactions:
                    return "No transactions found matching those criteria."

                result = f"Found {len(transactions)} transactions:\n\n"
                for txn in transactions[:10]:
                    result += f"- {txn['date']}: {txn['merchant']} - ${txn['amount']:.2f}"
                    if txn.get('category'):
                        result += f" ({txn['category']})"
                    result += "\n"

                if len(transactions) > 10:
                    total = sum(t['amount'] for t in transactions)
                    result += f"\n... and {len(transactions)-10} more. Total: ${total:.2f}"

                return result
            except Exception as e:
                return f"Error querying transactions: {str(e)}"

        def detect_grift():
            try:
                flags = self.grift_detector.detect_all()

                if not flags:
                    return "Great news! No obvious grift detected in your transactions."

                high = [f for f in flags if f.severity == "high"]
                medium = [f for f in flags if f.severity == "medium"]
                low = [f for f in flags if f.severity == "low"]

                result = f"Found {len(flags)} potential issues:\n\n"

                if high:
                    result += f"HIGH PRIORITY ({len(high)}):\n"
                    for flag in high[:3]:
                        result += f"- {flag.description}\n\n"

                if medium:
                    result += f"MEDIUM PRIORITY ({len(medium)}):\n"
                    for flag in medium[:3]:
                        result += f"- {flag.description}\n\n"

                if low:
                    result += f"LOW PRIORITY ({len(low)}):\n"
                    for flag in low[:2]:
                        result += f"- {flag.description}\n\n"

                return result
            except Exception as e:
                return f"Error detecting grift: {str(e)}"

        def get_recurring_charges():
            try:
                recurring = self.db.get_recurring_transactions(min_occurrences=2)

                if not recurring:
                    return "No recurring charges found."

                result = "Your recurring charges:\n\n"
                total_monthly = 0

                for item in recurring:
                    merchant = item['merchant']
                    avg_amount = item['avg_amount']
                    count = item['occurrence_count']

                    result += f"- {merchant}: ~${avg_amount:.2f} ({count} times)\n"
                    total_monthly += avg_amount

                result += f"\nEstimated total recurring monthly spend: ${total_monthly:.2f}"
                result += f"\nAnnual recurring cost: ${total_monthly * 12:.2f}"

                return result
            except Exception as e:
                return f"Error getting recurring charges: {str(e)}"

        def get_category_breakdown(date_from=None, date_to=None):
            try:
                categories = self.analytics.get_category_breakdown(date_from, date_to)

                if not categories:
                    return "No spending data found."

                total = sum(cat['total_amount'] for cat in categories)
                result = "Spending by category:\n\n"

                for cat in categories:
                    amount = cat['total_amount']
                    count = cat['transaction_count']
                    percentage = (amount / total * 100) if total > 0 else 0
                    category_name = cat['category'] or 'Uncategorized'

                    result += f"- {category_name}: ${amount:.2f} ({percentage:.1f}%) - {count} transactions\n"

                result += f"\nTotal: ${total:.2f}"
                return result
            except Exception as e:
                return f"Error getting category breakdown: {str(e)}"

        def get_top_merchants(n=10):
            try:
                merchants = self.analytics.get_top_merchants(n)

                if not merchants:
                    return "No merchant data found."

                result = f"Your top {n} merchants by spending:\n\n"
                for i, merchant in enumerate(merchants, 1):
                    name = merchant['merchant']
                    total = merchant['total_amount']
                    count = merchant['transaction_count']
                    avg = total / count if count > 0 else 0

                    result += f"{i}. {name}: ${total:.2f} ({count} transactions, ${avg:.2f} avg)\n"

                return result
            except Exception as e:
                return f"Error getting top merchants: {str(e)}"

        def get_spending_summary():
            try:
                stats = self.db.get_stats()
                summary = self.analytics.get_spending_summary()

                result = "Financial Overview:\n\n"
                result += f"Total statements: {stats['statements']}\n"
                result += f"Total transactions: {stats['total_transactions']}\n"
                result += f"Total spending: ${stats['total_spend']:.2f}\n"
                result += f"Average transaction: ${summary['average_transaction']:.2f}\n"

                if stats['date_range']['start']:
                    result += f"Date range: {stats['date_range']['start']} to {stats['date_range']['end']}\n"

                if stats['grift_flags'] > 0:
                    result += f"\n{stats['grift_flags']} potential grift items flagged!\n"

                result += f"\nLargest transaction: {summary['largest_transaction']['merchant']} "
                result += f"(${summary['largest_transaction']['amount']:.2f} on {summary['largest_transaction']['date']})"

                return result
            except Exception as e:
                return f"Error getting summary: {str(e)}"

        def find_savings_opportunities():
            try:
                opportunities = self.analytics.find_savings_opportunities()

                if not opportunities:
                    return "No obvious savings opportunities found. Your spending looks optimized!"

                result = "Savings Opportunities:\n\n"
                for i, opp in enumerate(opportunities, 1):
                    result += f"{i}. {opp['recommendation']}\n\n"

                return result
            except Exception as e:
                return f"Error finding savings: {str(e)}"

        def get_monthly_trends():
            try:
                trends = self.analytics.get_monthly_trends()

                if not trends.get('months'):
                    return "Not enough data for trend analysis."

                result = "Monthly Spending Trends:\n\n"
                months = trends['months']
                totals = trends['monthly_totals']

                for month in months[-6:]:
                    total = totals[month]
                    result += f"{month}: ${total:.2f}"

                    if month in trends['mom_growth']:
                        growth = trends['mom_growth'][month]
                        result += f" ({growth:+.1f}% vs prev month)"

                    result += "\n"

                return result
            except Exception as e:
                return f"Error analyzing trends: {str(e)}"

        return {
            "query_transactions": query_transactions,
            "detect_grift": detect_grift,
            "get_recurring_charges": get_recurring_charges,
            "get_category_breakdown": get_category_breakdown,
            "get_top_merchants": get_top_merchants,
            "get_spending_summary": get_spending_summary,
            "find_savings_opportunities": find_savings_opportunities,
            "get_monthly_trends": get_monthly_trends
        }

    def chat(self, message: str) -> str:
        """Send a message to the agent and get a response"""
        try:
            # Add user message to history
            self.history.append({"role": "user", "content": message})

            # Prepare messages with system prompt
            messages = [
                {
                    "role": "system",
                    "content": """You are FinCheck AI, a proactive financial advisor that helps users find grift,
reduce wasteful spending, and optimize their finances.

Your role:
- Analyze bank and credit card statements
- Detect forgotten subscriptions, duplicate charges, and suspicious transactions
- Provide actionable insights to save money
- Answer questions about spending patterns
- Proactively suggest ways to reduce costs

Be direct, helpful, and use data to back up recommendations. Ask insightful questions to help users think about their spending."""
                }
            ] + self.history[-20:]  # Keep last 20 messages

            # Call OpenAI with function calling
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.tools_definition,
                tool_choice="auto"
            )

            response_message = response.choices[0].message

            # Check if the model wants to call a function
            if response_message.tool_calls:
                # Execute function calls
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    logger.info(f"Calling function: {function_name} with args: {function_args}")

                    # Call the function
                    function_result = self.tool_functions[function_name](**function_args)

                    # Add function call to history
                    self.history.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": tool_call.function.arguments
                            }
                        }]
                    })

                    # Add function result to history
                    self.history.append({
                        "role": "tool",
                        "content": str(function_result),
                        "tool_call_id": tool_call.id
                    })

                # Get final response with function results
                final_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": messages[0]["content"]}
                    ] + self.history[-20:]
                )

                output = final_response.choices[0].message.content

            else:
                # No function call, use direct response
                output = response_message.content

            # Add assistant response to history
            if output:
                self.history.append({"role": "assistant", "content": output})

            return output or "I'm not sure how to help with that."

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            import traceback
            traceback.print_exc()
            return f"Sorry, I encountered an error: {str(e)}"

    def reset_conversation(self):
        """Clear conversation history"""
        self.history = []
