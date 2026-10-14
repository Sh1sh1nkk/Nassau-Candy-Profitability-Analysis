# Nassau Candy — Product Line Profitability & Margin Performance Analysis

A Streamlit dashboard for product and division profitability, gross margin, cost diagnostics, Pareto concentration, and data-quality checks.

## Features
- Executive KPI overview: sales, gross profit, gross margin, cost, products/orders
- Product-level profitability leaderboard and CSV export
- Division revenue/profit and margin comparisons
- Cost vs sales diagnostics with margin-risk flags
- Pareto analysis for revenue or gross-profit concentration
- Date, division, margin-threshold, and product-search filters
- Upload CSV or XLSX files from the dashboard sidebar
- Bundled dataset at `data/Nassau Candy Distributor.csv`

## Run locally (Windows)
```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Push this folder to a GitHub repository.
2. In Streamlit Community Cloud, choose the repository and branch `main`.
3. Set the main file path to `app.py`.
4. Deploy.

The bundled CSV is used by default. The app also supports uploading a CSV or Excel workbook.

## Dataset and interpretation notes
- Gross margin = Gross Profit / Sales × 100.
- Profit per unit = Gross Profit / Units.
- Cost ratio and margin thresholds are screening indicators, not definitive business decisions.
- Date parsing uses day-first interpretation to accommodate the source file's `DD-MM-YYYY` style.
- The factory coordinate/product mapping in the project brief is not plotted because the transaction CSV does not include factory assignment fields. It can be added later by joining a verified product-to-factory mapping table.
- “Margin volatility” is not a standalone KPI in this version; the monthly trend is provided and volatility can be added when there are sufficient observations per product over time.
