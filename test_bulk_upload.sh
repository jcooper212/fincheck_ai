#!/bin/bash
# ABOUTME: Test script for bulk uploading all PDFs and reporting results
# ABOUTME: Run this to test the fincheck bulk upload feature

cd /Users/jcooper/py/genAi/fincheck_ai

echo "================================"
echo "FinCheck Bulk Upload Test"
echo "================================"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Check how many PDFs exist
pdf_count=$(find data/pdfs -name "*.pdf" -o -name "*.PDF" 2>/dev/null | wc -l)
echo "📁 Found $pdf_count PDF files in data/pdfs"
echo ""

# Run bulk upload
echo "🚀 Starting bulk upload..."
echo ""

fincheck upload

echo ""
echo "================================"
echo "Upload Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Check results: fincheck stats"
echo "2. View accounts: fincheck accounts"
echo "3. Check cash flow: fincheck cashflow"
echo "4. Analyze for grift: fincheck analyze"
echo ""
