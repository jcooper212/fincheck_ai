# FinCheck AI - Quick Start Guide

## What You've Got

A fully functional AI-powered financial grift detector that:
- Parses PDF bank/credit card statements
- Detects forgotten subscriptions and wasteful spending
- Categorizes all your transactions automatically
- Provides a chat interface to ask questions about your spending
- Finds savings opportunities

## Getting Started

### 1. Activate the environment
```bash
source .venv/bin/activate
```

### 2. Upload Your Bank Statements

Upload PDFs from your banks (works with Chase, Amex, Citi, Bank of America, etc.):

```bash
fincheck upload path/to/statement.pdf
```

Do this for all your statements (aim for 3 months across 4 banks as planned).

### 3. Run Analysis

Get an immediate analysis of your spending:

```bash
fincheck analyze
```

This will:
- Show you overall spending stats
- Run grift detection (recurring charges, duplicates, price increases)
- Display category breakdown
- Suggest savings opportunities

### 4. Chat with FinCheck AI

Start an interactive chat to dig deeper:

```bash
fincheck chat
```

Example questions you can ask:
- "Show me all recurring charges"
- "What subscriptions am I paying for?"
- "Where did I spend the most last month?"
- "Find duplicate charges"
- "What are my top merchants?"
- "How can I save money?"
- "Show me my food delivery spending"

### 5. Check Stats Anytime

```bash
fincheck stats
```

## Example Workflow

```bash
# Upload statements
fincheck upload ~/Downloads/chase_jan_2025.pdf
fincheck upload ~/Downloads/chase_feb_2025.pdf
fincheck upload ~/Downloads/amex_jan_2025.pdf
# ... upload all your PDFs

# Quick analysis
fincheck analyze

# Deep dive with AI
fincheck chat
```

## Tips

1. **Upload Multiple Months**: The more data, the better the grift detection works (recurring patterns need at least 2-3 months)

2. **Chat is Powerful**: The AI agent can:
   - Answer complex questions
   - Compare spending across time periods
   - Provide personalized recommendations
   - Ask YOU insightful questions to help you think about spending

3. **Review Recurring Charges**: Start with `fincheck analyze` to see recurring charges - these are often the biggest sources of grift

4. **Categorization**: The system auto-categorizes transactions. If you notice miscategorizations, the AI learns from your corrections over time.

## What Gets Detected

- **Recurring Subscriptions**: Monthly charges you might have forgotten
- **Duplicate Charges**: Same merchant, same amount, close dates
- **Price Increases**: When a service quietly raises their price
- **Suspicious Merchants**: Generic names like "WEB SERVICES" that are hard to identify
- **Small Recurring Charges**: The "$9.99 grift" that adds up over time

## Troubleshooting

### PDF Parser Issues
If a PDF doesn't parse well, the parser will do its best with text extraction. You may need to:
- Try a different PDF format from your bank
- Contact me to add specific parser rules for that bank

### Missing Transactions
Check that the PDF actually contains transaction details (not just a summary page).

### Chat Not Working
Make sure your OPENAI_API_KEY is set in the .env file.

## Next Steps (Phase 2)

- Operator mode to auto-retrieve statements from bank websites
- Scheduled automated analysis
- Email/SMS alerts for grift detection
- Budget tracking and goals
- Bill negotiation suggestions

---

Ready to find some grift! Start with `fincheck analyze` after uploading your PDFs.
