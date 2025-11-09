# ABOUTME: Main CLI entry point for FinCheck AI
# ABOUTME: Provides commands for uploading statements, analyzing transactions, and chatting with the AI agent

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI

from src.database import Database
from src.pdf_parser import parse_statement
from src.categorizer import Categorizer, Analytics
from src.grift_detector import GriftDetector
from src.agent import FinCheckAgent

# Load environment variables
load_dotenv()

console = Console()


@click.group()
def cli():
    """FinCheck AI - Your personal financial grift detector"""
    pass


def _upload_single_pdf(pdf_path: Path, db: Database, categorizer: Categorizer) -> bool:
    """
    Upload a single PDF file. Returns True if successful, False otherwise.
    """
    try:
        # Parse PDF
        metadata, transactions = parse_statement(pdf_path)

        if len(transactions) == 0:
            console.print(f"[yellow]⚠[/yellow] {pdf_path.name}: No transactions found, skipping")
            return False

        # Copy PDF to data folder if not already there
        pdf_dest = Path("data/pdfs") / pdf_path.name
        pdf_dest.parent.mkdir(parents=True, exist_ok=True)

        import shutil
        if pdf_path != pdf_dest:
            shutil.copy(pdf_path, pdf_dest)

        # Check if already uploaded
        if db.is_pdf_already_uploaded(str(pdf_dest)):
            console.print(f"[dim]⊘[/dim] {pdf_path.name}: Already uploaded, skipping")
            return False

        # Add statement
        statement_id = db.add_statement(
            bank_name=metadata.get('bank_name', 'Unknown'),
            statement_date=metadata.get('statement_date', ''),
            pdf_path=str(pdf_dest),
            account_last4=metadata.get('account_last4'),
            account_type=metadata.get('account_type', 'credit_card')
        )

        # Categorize transactions
        transactions = categorizer.categorize_batch(transactions)

        # Store transactions
        for txn in transactions:
            db.add_transaction(
                statement_id=statement_id,
                date=txn['date'],
                merchant=txn['merchant'],
                amount=txn['amount'],
                transaction_type=txn.get('transaction_type', 'expense'),
                category=txn.get('category'),
                description=txn.get('description')
            )

        console.print(f"[green]✓[/green] {pdf_path.name}: {len(transactions)} transactions ({metadata.get('bank_name', 'Unknown')})")
        return True

    except Exception as e:
        console.print(f"[red]✗[/red] {pdf_path.name}: Error - {str(e)}")
        return False


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True), required=False)
def upload(pdf_path: str = None):
    """Upload and parse bank statement PDF(s). If no path provided, uploads all PDFs from data/pdfs"""

    try:
        # Initialize database
        db = Database()

        # Set up categorizer
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            openai_client = OpenAI(api_key=openai_api_key)
            categorizer = Categorizer(llm_client=openai_client)
        else:
            console.print("[yellow]⚠ OPENAI_API_KEY not found, using rule-based categorization only[/yellow]")
            categorizer = Categorizer()

        if pdf_path:
            # Single file upload
            console.print(f"\n[cyan]Uploading statement: {pdf_path}[/cyan]\n")
            pdf_file = Path(pdf_path)
            success = _upload_single_pdf(pdf_file, db, categorizer)

            if success:
                console.print("\n[green]Upload complete! Use 'fincheck chat' to analyze your spending.[/green]\n")
            else:
                console.print("\n[yellow]Upload skipped or failed.[/yellow]\n")

        else:
            # Bulk upload from data/pdfs
            pdfs_dir = Path("data/pdfs")
            if not pdfs_dir.exists():
                console.print(f"\n[yellow]Directory {pdfs_dir} does not exist. Create it and add PDF files.[/yellow]\n")
                return

            pdf_files = list(pdfs_dir.glob("*.pdf")) + list(pdfs_dir.glob("*.PDF"))

            if not pdf_files:
                console.print(f"\n[yellow]No PDF files found in {pdfs_dir}[/yellow]\n")
                return

            console.print(f"\n[cyan]Found {len(pdf_files)} PDF files in {pdfs_dir}[/cyan]\n")

            uploaded = 0
            skipped = 0
            failed = 0

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Processing {len(pdf_files)} PDFs...", total=len(pdf_files))

                for pdf_file in pdf_files:
                    result = _upload_single_pdf(pdf_file, db, categorizer)
                    if result:
                        uploaded += 1
                    elif result is False:
                        skipped += 1
                    else:
                        failed += 1

                    progress.advance(task)

            # Summary
            console.print()
            summary_panel = Panel(
                f"[b green]Uploaded:[/b green] {uploaded}\n"
                f"[b yellow]Skipped:[/b yellow] {skipped} (already in database)\n"
                f"[b red]Failed:[/b red] {failed}",
                title="Upload Summary",
                border_style="cyan"
            )
            console.print(summary_panel)
            console.print("\n[green]Bulk upload complete! Use 'fincheck analyze' to review.[/green]\n")

    except Exception as e:
        console.print(f"\n[red]Error during upload: {str(e)}[/red]\n")
        raise


@cli.command()
def analyze():
    """Run grift detection and show analysis"""
    console.print("\n[cyan]🔍 Analyzing your spending...[/cyan]\n")

    try:
        db = Database()
        stats = db.get_stats()

        if stats['transactions'] == 0:
            console.print("[yellow]No transactions found. Upload statements first with 'fincheck upload <pdf>'[/yellow]\n")
            return

        # Show overview
        panel = Panel(
            f"[b]Statements:[/b] {stats['statements']}\n"
            f"[b]Transactions:[/b] {stats['transactions']}\n"
            f"[b]Total Spend:[/b] ${stats['total_spend']:.2f}\n"
            f"[b]Date Range:[/b] {stats['date_range']['start']} to {stats['date_range']['end']}",
            title="📊 Overview",
            border_style="cyan"
        )
        console.print(panel)

        # Run grift detection
        console.print("\n[cyan]Running grift detection...[/cyan]\n")
        grift_detector = GriftDetector(db)
        flags = grift_detector.detect_all()

        if not flags:
            console.print("[green]✓ No obvious grift detected! Your spending looks clean.[/green]\n")
        else:
            # Group by severity
            high = [f for f in flags if f.severity == "high"]
            medium = [f for f in flags if f.severity == "medium"]
            low = [f for f in flags if f.severity == "low"]

            if high:
                console.print(f"[red]🚨 {len(high)} HIGH PRIORITY ISSUES:[/red]\n")
                for flag in high[:5]:
                    console.print(f"  • {flag.description}\n")

            if medium:
                console.print(f"[yellow]⚠️  {len(medium)} MEDIUM PRIORITY ISSUES:[/yellow]\n")
                for flag in medium[:5]:
                    console.print(f"  • {flag.description}\n")

            if low:
                console.print(f"[dim]ℹ️  {len(low)} LOW PRIORITY ITEMS:[/dim]\n")
                for flag in low[:3]:
                    console.print(f"  • {flag.description}\n")

        # Show top spending categories
        analytics = Analytics(db)
        categories = analytics.get_category_breakdown()

        if categories:
            console.print("\n")
            table = Table(title="💰 Spending by Category")
            table.add_column("Category", style="cyan")
            table.add_column("Transactions", justify="right")
            table.add_column("Amount", style="green", justify="right")
            table.add_column("%", justify="right")

            total = sum(c['total_amount'] for c in categories)

            for cat in categories[:8]:
                pct = (cat['total_amount'] / total * 100) if total > 0 else 0
                table.add_row(
                    cat['category'] or 'Uncategorized',
                    str(cat['transaction_count']),
                    f"${cat['total_amount']:.2f}",
                    f"{pct:.1f}%"
                )

            console.print(table)

        # Show savings opportunities
        opportunities = analytics.find_savings_opportunities()
        if opportunities:
            console.print("\n")
            panel = Panel(
                "\n".join(f"{i}. {opp['recommendation']}" for i, opp in enumerate(opportunities[:3], 1)),
                title="💡 Savings Opportunities",
                border_style="green"
            )
            console.print(panel)

        console.print("\n[green]Analysis complete! Use 'fincheck chat' to dive deeper.[/green]\n")

    except Exception as e:
        console.print(f"\n[red]Error analyzing: {str(e)}[/red]\n")
        raise


@cli.command()
def chat():
    """Start an interactive chat session with FinCheck AI"""
    console.print("\n[bold cyan]💬 FinCheck AI Chat[/bold cyan]")
    console.print("[dim]Ask me anything about your spending. Type 'exit' or 'quit' to end.\n[/dim]")

    try:
        # Initialize components
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            console.print("[red]Error: OPENAI_API_KEY not found in .env file[/red]\n")
            console.print("Please create a .env file with your OpenAI API key:\n")
            console.print("  OPENAI_API_KEY=your_key_here\n")
            return

        db = Database()
        stats = db.get_stats()

        if stats['transactions'] == 0:
            console.print("[yellow]No transactions found. Upload statements first with 'fincheck upload <pdf>'[/yellow]\n")
            return

        grift_detector = GriftDetector(db)
        analytics = Analytics(db)

        # Create agent
        agent = FinCheckAgent(
            db=db,
            grift_detector=grift_detector,
            analytics=analytics,
            openai_api_key=openai_api_key
        )

        # Initial greeting
        greeting = (
            f"I've loaded {stats['transactions']} transactions from {stats['statements']} statements. "
            f"Total spending: ${stats['total_spend']:.2f}.\n\n"
            f"I can help you find grift, analyze spending, and discover savings opportunities. "
            f"What would you like to know?"
        )

        console.print(f"[green]🤖 FinCheck AI:[/green] {greeting}\n")

        # Chat loop
        while True:
            try:
                # Get user input
                user_input = console.input("[cyan]You:[/cyan] ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit', 'bye']:
                    console.print("\n[green]👋 Thanks for using FinCheck AI! Keep saving money![/green]\n")
                    break

                # Get response from agent
                console.print()
                with console.status("[cyan]Thinking...[/cyan]"):
                    response = agent.chat(user_input)

                console.print(f"[green]🤖 FinCheck AI:[/green] {response}\n")

            except KeyboardInterrupt:
                console.print("\n\n[yellow]Chat interrupted. Type 'exit' to quit properly.[/yellow]\n")
                continue
            except EOFError:
                break

    except Exception as e:
        console.print(f"\n[red]Error in chat: {str(e)}[/red]\n")
        raise


@cli.command()
def stats():
    """Show database statistics"""
    try:
        db = Database()
        stats = db.get_stats()

        if stats['transactions'] == 0:
            console.print("\n[yellow]No data yet. Upload statements with 'fincheck upload <pdf>'[/yellow]\n")
            return

        console.print()
        panel = Panel(
            f"[b]Total Statements:[/b] {stats['statements']}\n"
            f"[b]Total Transactions:[/b] {stats['transactions']}\n"
            f"[b]Total Spending:[/b] ${stats['total_spend']:.2f}\n"
            f"[b]Date Range:[/b] {stats['date_range']['start']} to {stats['date_range']['end']}\n"
            f"[b]Grift Flags:[/b] {stats['grift_flags']}",
            title="📊 FinCheck Statistics",
            border_style="cyan"
        )
        console.print(panel)
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error getting stats: {str(e)}[/red]\n")
        raise


@cli.command()
@click.option('--month', default=None, help='Month in YYYY-MM format (default: all time)')
def cashflow(month):
    """Show income vs expenses breakdown"""
    try:
        db = Database()

        if month:
            # Specific month
            cashflow_data = db.get_income_vs_expenses(date_from=f"{month}-01", date_to=f"{month}-31")
            title = f"💰 Cash Flow - {month}"
        else:
            # All time
            cashflow_data = db.get_income_vs_expenses()
            monthly_data = db.get_cash_flow_by_month()
            title = "💰 Cash Flow - All Time"

        console.print()

        # Overall summary
        panel = Panel(
            f"[b green]Income:[/b green]    ${cashflow_data['income']:.2f}\n"
            f"[b red]Expenses:[/b red]   ${cashflow_data['expense']:.2f}\n"
            f"[b cyan]Net:[/b cyan]        ${cashflow_data['net']:+.2f}",
            title=title,
            border_style="cyan" if cashflow_data['net'] >= 0 else "red"
        )
        console.print(panel)

        # Monthly breakdown if showing all time
        if not month and monthly_data:
            console.print("\n[cyan]Monthly Breakdown:[/cyan]\n")
            table = Table()
            table.add_column("Month", style="cyan")
            table.add_column("Income", style="green", justify="right")
            table.add_column("Expenses", style="red", justify="right")
            table.add_column("Net", justify="right")

            for month_data in monthly_data[:6]:  # Last 6 months
                net_color = "green" if month_data['net'] >= 0 else "red"
                table.add_row(
                    month_data['month'],
                    f"${month_data['income']:.2f}",
                    f"${month_data['expense']:.2f}",
                    f"[{net_color}]${month_data['net']:+.2f}[/{net_color}]"
                )

            console.print(table)

        console.print()

    except Exception as e:
        console.print(f"\n[red]Error analyzing cash flow: {str(e)}[/red]\n")
        raise


@cli.command()
@click.option('--month', default=None, help='Month in YYYY-MM format (default: all time)')
def accounts(month):
    """List all accounts with spending summaries"""
    try:
        db = Database()

        if month:
            accounts_data = db.get_spending_by_account(month=month)
            title = f"💳 Accounts - {month}"
        else:
            accounts_data = db.get_all_accounts()
            title = "💳 Your Accounts"

        if not accounts_data:
            console.print("\n[yellow]No accounts found. Upload statements first.[/yellow]\n")
            return

        console.print()
        table = Table(title=title)
        table.add_column("Bank", style="cyan")
        table.add_column("Account", style="dim")
        table.add_column("Type", style="magenta")
        table.add_column("Transactions", justify="right")
        table.add_column("Income", style="green", justify="right")
        table.add_column("Expenses", style="red", justify="right")

        total_income = 0
        total_expense = 0

        for account in accounts_data:
            bank = account['bank_name']
            acct = f"...{account['account_last4']}" if account.get('account_last4') else "N/A"
            acct_type = account.get('account_type', 'unknown').replace('_', ' ').title()
            count = account.get('transaction_count', 0)
            income = account.get('total_income', 0)
            expense = account.get('total_expense', 0)

            total_income += income
            total_expense += expense

            table.add_row(
                bank,
                acct,
                acct_type,
                str(count),
                f"${income:.2f}" if income > 0 else "-",
                f"${expense:.2f}" if expense > 0 else "-"
            )

        console.print(table)

        # Summary
        console.print()
        panel = Panel(
            f"[b]Total Accounts:[/b] {len(accounts_data)}\n"
            f"[b green]Total Income:[/b green] ${total_income:.2f}\n"
            f"[b red]Total Expenses:[/b red] ${total_expense:.2f}\n"
            f"[b cyan]Net:[/b cyan] ${total_income - total_expense:+.2f}",
            title="Summary",
            border_style="cyan"
        )
        console.print(panel)
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error listing accounts: {str(e)}[/red]\n")
        raise


@cli.command()
@click.option('--month', default=None, help='Filter by specific month (YYYY-MM)')
@click.option('--bank', default=None, help='Filter by bank name')
def list(month, bank):
    """List transactions grouped by statement, month, and merchant"""
    try:
        db = Database()
        data = db.get_transactions_by_statement_month_merchant(
            month_filter=month,
            bank_filter=bank
        )

        if not data:
            console.print("\n[yellow]No transactions found. Upload statements first.[/yellow]\n")
            return

        console.print()

        # Overall stats
        total_statements = len(data)
        total_transactions = sum(s['transaction_count'] for s in data)
        total_amount = sum(s['total'] for s in data)

        # Get unique merchant count across all data
        all_merchants = set()
        for statement in data:
            for month_data in statement['months']:
                for merchant in month_data['merchants']:
                    all_merchants.add(merchant['merchant'])

        # Display each statement
        for statement in data:
            # Statement header panel
            bank = statement['bank_name']
            account = f"...{statement['account_last4']}" if statement.get('account_last4') else "N/A"
            acct_type = statement.get('account_type', 'unknown').replace('_', ' ').title()

            header = (
                f"[b cyan]Statement:[/b cyan] {bank} {account} ({acct_type})\n"
                f"[b]Period:[/b] {statement['statement_date']}\n"
                f"[b]Total:[/b] ${statement['total']:.2f} | {statement['transaction_count']} transactions"
            )

            panel = Panel(header, border_style="cyan", expand=False)
            console.print(panel)
            console.print()

            # Display months
            for month_data in statement['months']:
                month_name = month_data['month']
                month_total = month_data['total']
                month_count = month_data['transaction_count']

                console.print(f"  [bold cyan]📅 {month_name}[/bold cyan] [dim](${month_total:.2f} | {month_count} transactions)[/dim]\n")

                # Display merchants
                for merchant in month_data['merchants']:
                    merchant_name = merchant['merchant']
                    merchant_total = merchant['total_amount']
                    merchant_count = merchant['transaction_count']
                    category = merchant.get('category', 'Uncategorized')

                    # Merchant header
                    console.print(f"    [bold]🏪 {merchant_name}[/bold] [dim]- {category}[/dim]")

                    # Individual transactions
                    for txn in merchant['transactions']:
                        date = txn['date']
                        amount = txn['amount']
                        txn_type = txn.get('transaction_type', 'expense')

                        # Color based on transaction type
                        if amount < 0 or txn_type == 'income':
                            amount_color = "green"
                            amount_str = f"-${abs(amount):.2f}"
                        else:
                            amount_color = "red"
                            amount_str = f"${amount:.2f}"

                        console.print(f"       {date}  [{amount_color}]{amount_str:>10}[/{amount_color}]")

                    # Merchant total
                    console.print(f"       [dim]{'─' * 40}[/dim]")
                    console.print(f"       [b]Total: ${merchant_total:.2f}[/b] ({merchant_count} transaction{'s' if merchant_count > 1 else ''})\n")

                console.print()  # Space between months

            console.print()  # Space between statements

        # Summary at the end
        console.print(f"[dim]{'─' * 80}[/dim]\n")

        summary_panel = Panel(
            f"[b]Total Statements:[/b] {total_statements}\n"
            f"[b]Total Merchants:[/b] {len(all_merchants)} (unique)\n"
            f"[b]Total Transactions:[/b] {total_transactions}\n"
            f"[b]Total Amount:[/b] ${total_amount:.2f}",
            title="📊 Summary",
            border_style="green"
        )
        console.print(summary_panel)
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error listing transactions: {str(e)}[/red]\n")
        raise


if __name__ == "__main__":
    cli()
