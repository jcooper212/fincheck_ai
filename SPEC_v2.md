# FinCheck AI - Comprehensive Spec v2.0

## Project Overview
An AI-powered financial statement analyzer that detects grift, identifies wasteful spending, tracks income vs expenses, and provides actionable insights to save money.

## Phase 1: Manual PDF Upload (Day 1 MVP + Extensions)

### Day 1 Part 1: Core Features (✅ Complete)
- PDF statement parser for credit cards
- Grift detection (recurring, duplicates, price increases, suspicious merchants)
- Auto-categorization with LLM fallback
- AI chat agent with 8 tools
- CLI interface

### Day 1 Part 2: Enhanced Features (In Progress)

#### Feature 1: Income & Expense Tracking
**Problem:** Currently only tracking credit card charges (expenses). Need full financial picture including bank accounts with incoming money.

**Solution:**
- Extend parser to handle **bank statements** (checking/savings)
- Distinguish transaction types:
  - **Income**: Deposits, payroll, transfers in, interest
  - **Expenses**: Withdrawals, purchases, transfers out, fees
- Update database schema with `transaction_type` field
- Analytics showing:
  - Total income vs total expenses
  - Net cash flow per month
  - Income sources breakdown
  - Burn rate analysis

**Implementation:**
- Add `transaction_type ENUM('income', 'expense')` to transactions table
- Parser detects debit/credit indicators in bank statements
- New analytics functions:
  - `get_income_vs_expenses(date_from, date_to)`
  - `get_cash_flow_summary()`
  - `get_income_sources()`
- Agent gets new tools:
  - `analyze_cash_flow()`
  - `get_income_breakdown()`
  - `calculate_burn_rate()`

#### Feature 2: Per-Card/Bank Monthly Breakdowns
**Problem:** Hard to see which card/account is most used, or compare spending across banks.

**Solution:**
- Auto-detect bank name and account from PDF (already extracting)
- Provide monthly breakdowns **per account**:
  - Per-card spending trends
  - Which card gets used most
  - Monthly comparison across banks
  - Card utilization patterns

**Implementation:**
- Already have `bank_name` and `account_last4` in database
- New analytics functions:
  - `get_spending_by_account(month)`
  - `get_account_utilization()`
  - `compare_accounts_monthly()`
- New CLI command: `fincheck accounts` - show all accounts with summary
- Agent tool: `compare_cards()` - compare card usage

**Display:**
```
November 2025 - Spending by Account

Chase (...1234)         $2,450.32  (45 transactions)
Amex (...5678)          $1,823.45  (32 transactions)
Citi (...9012)            $892.10  (18 transactions)
Wells Fargo (...3456)     $245.67  (12 transactions)

Most Used: Chase (...1234)
Highest Avg Transaction: Amex (...5678) - $56.98
```

#### Feature 3: Kimi K2 Max Thinking Model Integration
**Problem:** Current OpenAI GPT-4o is good, but Kimi K2 Max has advanced reasoning capabilities for complex financial analysis.

**Solution:**
- Integrate **Kimi K2 Max** (Moonshot AI's latest thinking model)
- Use for complex reasoning tasks:
  - Deep grift analysis with multi-step reasoning
  - Complex pattern detection across months
  - Sophisticated savings recommendations
  - Budget optimization strategies
- Keep OpenAI for:
  - Fast categorization
  - Simple queries
  - Real-time chat responses

**Implementation:**
- Add Kimi API support alongside OpenAI
- Dual-model architecture:
  - **OpenAI GPT-4o**: Fast chat, categorization, simple queries
  - **Kimi K2 Max**: Deep analysis, reasoning, complex insights
- New commands:
  - `fincheck analyze --deep` - Use Kimi for thorough analysis
  - `fincheck insights` - Kimi-powered financial insights
- Agent routing logic:
  - Simple queries → OpenAI
  - "Analyze", "Why", "How to save" → Kimi
  - User can specify: "Use deep thinking to analyze my spending"

**Kimi K2 Max Use Cases:**
1. **Advanced Grift Detection:**
   - Multi-month pattern analysis
   - Correlation between merchants (same company, different names)
   - Seasonal spending anomalies
   - Hidden subscription families (e.g., Adobe suite = 3 subscriptions)

2. **Budget Optimization:**
   - Given spending patterns, suggest optimal budget allocation
   - Identify which subscriptions provide most value
   - Recommend payment method optimization (cashback, points)

3. **Predictive Analysis:**
   - Forecast next month's spending
   - Predict which subscriptions might increase price
   - Anticipate cashflow issues

---

## Updated Technical Architecture

### Tech Stack (Updated)
- **Language:** Python 3.11+
- **LLMs:**
  - OpenAI GPT-4o (fast chat, categorization)
  - Kimi K2 Max (deep reasoning, analysis)
- **Package Manager:** uv
- **PDF Parsing:** pdfplumber
- **Database:** SQLite3
- **CLI Framework:** Click + Rich
- **Vector Store (Optional):** ChromaDB

### Updated Database Schema

```sql
-- transactions table (UPDATED)
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    statement_id INTEGER,
    date TEXT,
    merchant TEXT,
    amount REAL,
    transaction_type TEXT CHECK(transaction_type IN ('income', 'expense')),  -- NEW
    category TEXT,
    description TEXT,
    metadata TEXT,
    FOREIGN KEY (statement_id) REFERENCES statements(id)
);

-- statements table (UPDATED)
CREATE TABLE statements (
    id INTEGER PRIMARY KEY,
    bank_name TEXT,
    account_last4 TEXT,
    account_type TEXT,  -- NEW: 'credit_card', 'checking', 'savings'
    statement_date TEXT,
    pdf_path TEXT,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bank_name, statement_date, account_last4)
);

-- monthly_summaries table (NEW - for per-account breakdowns)
CREATE TABLE monthly_summaries (
    id INTEGER PRIMARY KEY,
    statement_id INTEGER,
    month TEXT,  -- YYYY-MM
    total_income REAL,
    total_expenses REAL,
    net_cash_flow REAL,
    transaction_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (statement_id) REFERENCES statements(id)
);
```

### Updated Project Structure

```
fincheck_ai/
├── src/
│   ├── database.py         # SQLite with new schema
│   ├── pdf_parser.py       # Handles both CC + bank statements
│   ├── grift_detector.py   # Enhanced with Kimi reasoning
│   ├── categorizer.py      # Transaction categorization
│   ├── analytics.py        # NEW: Separated analytics module
│   ├── cash_flow.py        # NEW: Income/expense analysis
│   ├── account_analyzer.py # NEW: Per-card/bank analysis
│   ├── agent.py            # Multi-model agent (OpenAI + Kimi)
│   ├── kimi_client.py      # NEW: Kimi API integration
│   └── main.py             # CLI with new commands
├── data/
│   ├── pdfs/
│   └── fincheck.db
├── tests/
│   ├── test_basic.py
│   ├── test_income_expense.py  # NEW
│   └── test_kimi.py           # NEW
├── .env                    # OpenAI + Kimi API keys
├── SPEC_v2.md             # This file
├── QUICKSTART.md
└── README.md
```

---

## Updated CLI Commands

```bash
# Existing commands
fincheck upload <pdf>       # Upload any statement (CC or bank)
fincheck analyze            # Quick grift detection
fincheck chat               # Interactive AI chat
fincheck stats              # Overall statistics

# New commands
fincheck accounts           # List all accounts with summaries
fincheck cashflow [month]   # Show income vs expenses
fincheck compare-cards      # Compare card usage patterns
fincheck insights           # Kimi-powered deep analysis
fincheck analyze --deep     # Use Kimi for thorough grift detection
```

---

## Updated Agent Tools

### New Tools (Total: 13 tools)

1. **query_transactions** (existing, updated)
2. **detect_grift** (existing, enhanced with Kimi)
3. **get_recurring_charges** (existing)
4. **get_category_breakdown** (existing)
5. **get_top_merchants** (existing)
6. **get_spending_summary** (existing)
7. **find_savings_opportunities** (existing)
8. **get_monthly_trends** (existing)
9. **analyze_cash_flow** ⭐ NEW - Income vs expenses analysis
10. **get_income_breakdown** ⭐ NEW - Sources of income
11. **calculate_burn_rate** ⭐ NEW - Monthly spending velocity
12. **compare_accounts** ⭐ NEW - Compare cards/banks
13. **deep_analysis** ⭐ NEW - Kimi-powered reasoning

---

## Kimi K2 Max Integration Details

### API Setup
```python
from openai import OpenAI  # Kimi uses OpenAI-compatible API

kimi_client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1"
)

# Model: moonshot-v1-auto (latest thinking model)
```

### Model Selection Logic
```python
def route_to_model(query: str, task_type: str) -> str:
    """Decide which model to use"""

    # Use Kimi for complex reasoning
    if any(keyword in query.lower() for keyword in
           ['analyze', 'why', 'optimize', 'recommend', 'strategy', 'deep']):
        return "kimi"

    # Use Kimi for specific complex tasks
    if task_type in ['grift_analysis', 'budget_optimization', 'prediction']:
        return "kimi"

    # Use OpenAI for everything else (faster)
    return "openai"
```

### Example Kimi Prompt
```python
system_prompt = """You are a financial reasoning expert. Use deep analytical thinking to:
1. Identify hidden patterns across months
2. Detect subtle grift that simple rules miss
3. Provide multi-step reasoning for recommendations
4. Consider second-order effects of spending decisions

Analyze the transaction data and provide insights with your reasoning process visible."""
```

---

## Updated Success Criteria (Day 1 Part 2)

### Feature 1: Income & Expense Tracking
- [ ] Parser correctly identifies income vs expense in bank statements
- [ ] Database stores transaction_type accurately
- [ ] Cash flow analysis shows net income/expenses per month
- [ ] Agent can answer: "How much did I earn vs spend last month?"

### Feature 2: Per-Card/Bank Breakdowns
- [ ] `fincheck accounts` shows all accounts with totals
- [ ] Monthly breakdown shows spending per card
- [ ] Can compare: "Which card did I use most in November?"
- [ ] Agent tool `compare_accounts()` works correctly

### Feature 3: Kimi Integration
- [ ] Kimi API connected and responding
- [ ] `fincheck insights` uses Kimi for deep analysis
- [ ] Model routing works (simple → OpenAI, complex → Kimi)
- [ ] Kimi provides better grift detection than baseline

---

## Implementation Order (Day 1 Part 2)

### Step 1: Income/Expense Tracking (30 min)
1. Update database schema
2. Enhance PDF parser to detect transaction type
3. Add cash flow analytics functions
4. Add agent tools for income analysis
5. Test with bank statement PDFs

### Step 2: Per-Card Breakdowns (20 min)
1. Add account analytics functions
2. Create `fincheck accounts` command
3. Add account comparison to agent
4. Test with multiple cards

### Step 3: Kimi Integration (40 min)
1. Research Kimi K2 Max API
2. Create kimi_client.py
3. Add model routing logic to agent
4. Create `fincheck insights` command
5. Test deep analysis vs standard

### Step 4: End-to-End Testing (20 min)
1. Upload bank statements + credit cards
2. Verify income/expense split
3. Compare accounts
4. Run Kimi-powered insights
5. Validate all features work together

**Total Estimated Time: ~2 hours**

---

## Example Usage (After Day 1 Part 2)

```bash
# Upload mixed statements
fincheck upload chase_checking_nov.pdf    # Bank account
fincheck upload chase_card_nov.pdf        # Credit card
fincheck upload amex_nov.pdf              # Another card

# Check accounts
fincheck accounts
# Output:
# Your Accounts:
# 1. Chase Checking (...1234)    - 47 transactions  | $2,340.50 income, $1,823.10 expenses
# 2. Chase Credit (...5678)      - 32 transactions  | $1,450.30 expenses
# 3. Amex (...9012)              - 18 transactions  | $892.40 expenses

# Cash flow analysis
fincheck cashflow
# Output:
# November 2025 Cash Flow:
# Total Income:    $4,523.40
# Total Expenses:  $4,165.80
# Net Cash Flow:   +$357.60

# Deep analysis with Kimi
fincheck insights
# Output:
# [Kimi thinking process shown...]
#
# Deep Financial Analysis:
# 1. Hidden Grift Detected: You have 3 Adobe subscriptions under different names...
# 2. Optimization Opportunity: Consolidate streaming services...
# 3. Predictive Alert: Based on trends, November spending will exceed income...

# Chat with enhanced capabilities
fincheck chat
You: Compare my credit cards
AI: [Calls compare_accounts tool]
    Chase card is your most-used with $1,450 across 32 transactions.
    Amex has higher average per transaction ($49.58 vs $45.32).
    Consider using Amex for large purchases if it has better rewards.
```

---

## Future Enhancements (Phase 2)

- Operator mode for auto-retrieval
- Bill negotiation suggestions
- Budget goal tracking
- Alerts via email/SMS
- Export to spreadsheets
- Multi-user support
- Mobile app

---

This spec is ready for implementation. Let's build! 🚀
