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
