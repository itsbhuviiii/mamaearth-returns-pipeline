# Mamaearth Returns & Growth Intelligence Pipeline

Capstone Project, Data Analytics with AI & Gen AI, E&ICT Academy IIT Roorkee

This repo checks whether product returns are hurting Mamaearth's margins, using three connected layers:

1. **SQL (MySQL)**: loads the raw order data and runs report queries.
2. **Python / pandas**: cleans the data, finds the patterns, makes charts, and writes the key numbers to `narrator/findings.json`.
3. **GenAI narrator (Gemini)**: turns `findings.json` into a Situation–Complication–Resolution business summary, with an offline fallback that needs no API key.

No layer reports a number it did not compute itself or receive from the layer before it.

## Repository structure

```
├── README.md
├── sql/
│   ├── schema.sql          # creates the database and 3 tables
│   ├── seed_data.sql       # INSERT statements for all rows (blank cells become NULL)
│   ├── build_seed.py       # regenerates seed_data.sql from data/*.csv
│   └── reports.sql         # reports (a)-(i), with real output pasted above each
├── data/
│   ├── customers.csv       # 45 rows (raw, unedited)
│   ├── products.csv        # 16 rows (raw, unedited)
│   └── orders.csv          # 180 rows (raw, unedited)
├── analysis/
│   ├── clean_and_eda.py    # Part 2 Tasks 1-10; writes narrator/findings.json
│   └── visualize.py        # Part 2 Task 11; saves the two charts
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/
    ├── findings.json           # written by analysis/clean_and_eda.py (never hand-typed)
    ├── generate_narrative.py   # Gemini narrator + offline fallback + accuracy checker
    └── sample_output.txt       # one real Gemini output, verified by the checker
```

## Setup

Python 3.9+ and MySQL 8 (MySQL Workbench) are required.

```
pip install pandas matplotlib google-genai
```

Run all commands below from the project root folder.

## Step 1: SQL layer (Part 1)

In **MySQL Workbench**, open and run each file in order (File → Open SQL Script, then the ⚡ button):

1. `sql/schema.sql` creates the `mamaearth` database and the 3 tables
2. `sql/seed_data.sql` loads all rows
3. `sql/reports.sql` runs reports (a) to (i)

Expected after loading: customers = 45, products = 16, orders = 180.

Notes:
- `seed_data.sql` is generated from the CSVs by `python sql/build_seed.py`. Blank `discount_pct` and `rating` cells are written as SQL `NULL`, so `COUNT(rating)` = 165.
- Report (i) contains `SET SQL_SAFE_UPDATES = 0;` because Workbench's safe mode blocks an `UPDATE` without a `WHERE`.
- Report (i) adds a column, so to re-run `reports.sql`, run `schema.sql` and `seed_data.sql` first.

**Flow to Step 2:** the raw total revenue from Report (a), **Rs 99,860.20**, is the baseline that Part 2 reconciles against.

## Step 2: Python analysis (Part 2)

```
python analysis/clean_and_eda.py
python analysis/visualize.py
```

`clean_and_eda.py` reads the raw CSVs directly (not the database), so Parts 1 and 2 can run in either order. It prints every result:

| Task | Result |
|---|---|
| Load | orders.shape = (180, 9) |
| Payment casing | 7 raw spellings → 3: CARD 70, UPI 55, COD 55 |
| Duplicates | 5 dropped (O0176–O0180) → (175, 9) |
| Missing values | discount_pct 12 → 0; rating 15 → median 3.0 |
| Reconciliation | cleaned Rs 97,358.30 vs raw Rs 99,860.20; the gap of Rs 2,501.90 equals the value of the 5 duplicates |
| Outliers (IQR) | O0011 (qty 25), O0098 (qty 30), flagged not dropped |
| COD hypothesis | CARD 14.7%, COD 44.4%, UPI 18.9% → Confirmed |
| Segmentation | COD + Tier-2 = 54.5% (highest risk) |
| Correlation | all pairs negligible; "discounts reduce returns" → Busted |
| Monthly revenue | January's Rs 29,582.10 is inflated by 2 bulk orders; March (Rs 20,318.90) is the true peak |

**Flow to Step 3:** the last step of `clean_and_eda.py` writes **`narrator/findings.json`** from these computed values.

`visualize.py` recomputes from the raw CSVs and saves both charts to `visualizations/`.

## Step 3: GenAI narrator (Part 3)

`generate_narrative.py` reads `narrator/findings.json` and writes the SCR narrative.

### Option A: with a free Gemini API key

1. Get a **free** key at https://aistudio.google.com/apikey (the free tier is enough; no paid key needed).
2. Set it as an environment variable, never in code:

   Windows PowerShell:
```
   $env:GEMINI_API_KEY="your-key-here"
```
   Mac / Linux:
```
   export GEMINI_API_KEY="your-key-here"
```
3. Run:
```
   python narrator/generate_narrative.py
```

### Option B: no key at all (offline)

```
python narrator/generate_narrative.py
```
With no key set, it automatically uses the offline template. No internet and no setup are needed.

### Check the saved Gemini sample

```
python narrator/generate_narrative.py --check-sample
```

### How it works

- **System instruction** (kept separate from the prompt): the role of senior data analyst for Mamaearth's ops and finance heads, three labelled sections (Situation / Complication / Resolution), and a rule that every number must come from the findings.
- **Prompt** built from `findings.json`. No numbers are hard-coded.
- **Locked settings:** `temperature=0.0` (factual report, so deterministic), `max_output_tokens=8192`, a 30-second timeout.
- **Error handling:** the call is wrapped in `try/except` and always returns a dict. On any error or no key, it falls back to `generate_scr_narrative_offline()`.
- **Accuracy checker:** confirms these 5 figures appear in the text: 97,358.30 · 44.4 · 54.5 · 2,501.90 · March + 20,318.90.

## Key findings

1. Cleaned revenue is **Rs 97,358.30**. Raw data overstated it by Rs 2,501.90 because of 5 duplicate orders.
2. **COD orders are returned at 44.4%**, about 3x Card (14.7%).
3. The problem is concentrated in **COD + Tier-2 cities (54.5%)**.
4. Discounts don't reduce returns (correlation is negligible).
5. **March is the true peak month** (Rs 20,318.90). January only looked bigger because of two bulk orders.