# DIVCALC

# Full NY Divorce Settlement Calculator 2025

Now includes:
- Spousal & Child Support (with custody & high-income deviation)
- Full Marital Property Division
- Equalization payment (who owes whom at closing)

## Sample Output (your current data)

You just edit `config.yaml` and run — instantly see the complete settlement.

## Run
```bash
pip install pyyaml python-dateutil
python main_divcalc.py


You just edit `config.yaml` and run — instantly see the complete settlement.


Run it today — you’ll see **exactly** how much you owe monthly + the lump-sum equalization payment based on your real bank and credit card statements.

Item,Is it used in the guideline support calculation?,Explanation
Gross salary / payroll income,"YES – 100% of it (up to the caps, then deviation)",This is the only income number the NY formulas look at.
Number of children & custody split,YES,Directly changes the % and shared-parenting reduction.
Monthly credit-card spending,NO,The statutory formulas do not care how much you put on Amex/Chase every month.
Credit-card balances (debt),NO (for support) – YES (for property division),"The $661 or $3,202 balances are marital debt → they reduce the net marital estate and affect the equalization payment, but they do not change the monthly support number."
"Mortgage, car lease, private loans",NO (for support) – only for possible deviation,"Courts can consider these as part of the marital standard of living when deciding whether to go above the income caps, but they are not automatically plugged into the math like salary is."

Key Inputs from Your Documents

- Your gross income: $758,000 (base ~$408k from $23k net/month payroll; bonus ~$350k gross to net $200k).
- Jasmine's gross income: $0 (no evidence in statements).
- Children: 2.
- Parenting time (your scenario): 10% (no shared reduction).
- Deviation multiplier: 1.65x (standard for Nassau high-income cases; based on ~$45k–$55k monthly marital spending from statements like Amex dining/shopping, Chase bills).

Step-by-Step Calculation

StepDescription             Exact Math      Result (Annual)     Result (Monthly)
- Combined parental income  $758,000 (you) + $0 (her) = $758,000        $758,000
— Statutory % for 2 children    25% (fixed for 2 kids)
- Basic obligation (uncapped)$758,000 × 25% = $189,500$189,500$15,792
- NY 2025 income cap$183,000 (combined cap)
- Capped basic obligation$183,000 × 25% = $45,750$45,750$3,812
- High-income deviation$45,750 × 1.65 (multiplier for lifestyle) = $75,488$75,488$6,291 (this is where I stopped before—intermediate!)
- Your pro-rata share$758,000 / $758,000 = 100% (since her income = $0)$75,488 × 100% = $75,488$6,291
- Shared parenting reduction10% time < 30% threshold → No reduction (multiplier = 1.0)$75,488 × 1.0 = $75,488$6,291
- Final child support(From Step 8)$75,488$6,291
Add Spousal Maintenance (Separate Formula)

Capped at 20% of $228,000 (NY maintenance cap) = $45,600/year → $3,800/month.
Grand total monthly support: $6,291 (child) + $3,800 (spousal) = $10,091.
#####################################################
# FinCheck AI


AI-powered financial statement analyzer that detects grift, identifies wasteful spending, and provides actionable insights to save money.

## Features

- **Grift Detection**: Find recurring subscriptions, duplicate charges, price increases, and suspicious transactions
- **Smart Categorization**: Automatically categorize spending into meaningful groups
- **AI Chat Interface**: Natural language queries about your spending habits
- **Proactive Insights**: AI suggests ways to reduce spending and find savings

## Setup

1. Install dependencies with uv:
```bash
uv sync
```

2. Create `.env` file with your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. Create data directory:
```bash
mkdir -p data/pdfs
```

## Usage

### Upload bank statements (PDF):
```bash
fincheck upload path/to/statement.pdf
```

### Start chat session:
```bash
fincheck chat
```

### Run analysis:
```bash
fincheck analyze
```

## Architecture

- **PDF Parser**: Extracts transactions from bank/credit card PDFs
- **SQLite Database**: Stores transactions, statements, and grift flags
- **Grift Detector**: Identifies recurring charges, duplicates, price increases
- **Categorizer**: Auto-categorizes spending with LLM fallback
- **AI Agent**: LangChain-powered chat agent with financial advisory tools
- **CLI**: Rich terminal interface for user interaction

## Project Structure

```
fincheck_ai/
├── src/
│   ├── main.py          # CLI entry point
│   ├── pdf_parser.py    # PDF parsing logic
│   ├── database.py      # SQLite schema and queries
│   ├── grift_detector.py # Grift detection algorithms
│   ├── categorizer.py   # Transaction categorization
│   ├── analytics.py     # Spending analysis and insights
│   └── agent.py         # AI chat agent
├── data/
│   ├── pdfs/           # Uploaded PDF statements
│   └── fincheck.db     # SQLite database
└── tests/              # Unit and integration tests
```

## License

MIT
