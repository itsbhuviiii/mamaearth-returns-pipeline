#!/usr/bin/env python
# coding: utf-8

# In[12]:


# Task 1 — Load and inspect
print("\n" + "=" * 60)
print("TASK 1 — Load and inspect")
print("=" * 60)

import pandas as pd

customers = pd.read_csv("data/customers.csv")
orders    = pd.read_csv("data/orders.csv")
products  = pd.read_csv("data/products.csv")

print("orders.shape (before cleaning):", orders.shape)      # (180, 9)
print("\nFirst 5 rows:")
print(orders.head())
print("\nMissing values per column:")
print(orders.isnull().sum())                                 # discount_pct 12, rating 15


# In[13]:


# Task 2 — Standardize payment_method casing

print("\n" + "=" * 60)
print("Task 2 — Standardize payment_method casing")
print("=" * 60)

# BEFORE the fix
print("Before:", list(orders['payment_method'].unique()))
print("Distinct raw values:", orders['payment_method'].nunique())        # 7

# The fix
orders['payment_method'] = orders['payment_method'].str.strip().str.upper()

# AFTER the fix
print("After:", list(orders['payment_method'].unique()))
print("Distinct values now:", orders['payment_method'].nunique())        # 3
print(orders['payment_method'].value_counts())                          # CARD 70, UPI 55, COD 55


# In[14]:


# Task 3 — Remove duplicate orders

print("\n" + "=" * 60)
print("Task 3 — Remove duplicate orders")
print("=" * 60)

key = ['customer_id', 'product_id', 'order_date', 'quantity',
       'discount_pct', 'payment_method', 'rating', 'returned']

mask = orders.duplicated(subset=key, keep='first')
dropped = orders[mask]
orders_clean = orders[~mask].copy()

print("Duplicates found:", mask.sum())                          # 5
print("Dropped order_ids:", dropped['order_id'].tolist())       # O0176 ... O0180
print("orders_clean shape:", orders_clean.shape)                # (175, 9)


# In[15]:


# Task 4: impute missing values

print("\n" + "=" * 60)
print("Task 4: impute missing values")
print("=" * 60)

print("Missing discount_pct:", orders_clean['discount_pct'].isna().sum())     # 12
print("Missing rating:", orders_clean['rating'].isna().sum())                 # 15


orders_clean['discount_pct'] = orders_clean['discount_pct'].fillna(0)


rating_median = orders_clean['rating'].median()
print("Rating median (before imputing):", rating_median)                     # 3.0


orders_clean['rating'] = orders_clean['rating'].fillna(rating_median)


print("Missing after imputing:")
print(orders_clean[['discount_pct', 'rating']].isnull().sum())               # 0 and 0


# In[16]:


# Task 5 — Merge and reconcile against Part 1

print("\n" + "=" * 60)
print("Task 5 — Merge and reconcile against Part 1")
print("=" * 60)

merged = orders_clean.merge(products, on='product_id').merge(customers, on='customer_id')
print("Merged shape:", merged.shape)                                    # (175, 17)

merged['order_value'] = merged['quantity'] * merged['price'] * (1 - merged['discount_pct'] / 100)
cleaned_total = round(merged['order_value'].sum(), 2)
print("Cleaned total (175 rows):", cleaned_total)                       # 97358.3


dropped_merged = dropped.merge(products, on='product_id')
dropped_merged['order_value'] = (dropped_merged['quantity'] * dropped_merged['price']
                                 * (1 - dropped_merged['discount_pct'] / 100))
dup_value = round(dropped_merged['order_value'].sum(), 2)
print(dropped_merged[['order_id', 'quantity', 'price', 'discount_pct', 'order_value']])
print("Sum of 5 dropped duplicates:", dup_value)                        # 2501.9


raw = orders.merge(products, on='product_id')
raw_total = round((raw['quantity'] * raw['price'] * (1 - raw['discount_pct'].fillna(0) / 100)).sum(), 2)
delta = round(raw_total - cleaned_total, 2)
print("Raw total (180 rows):", raw_total)                               # 99860.2
print("Delta (raw - cleaned):", delta)                                  # 2501.9
print("Delta equals duplicate value:", delta == dup_value)              # True

# D) Reconciliation note
print(f"""
RECONCILIATION NOTE:
The cleaned revenue is Rs {cleaned_total:,.2f}, which is Rs {delta:,.2f} less than
the raw SQL total of Rs {raw_total:,.2f} from Part 1 Report (a).
This entire difference comes from the 5 duplicate orders removed in Task 3
({', '.join(dropped['order_id'])}), whose combined order_value, summed
separately, is exactly Rs {dup_value:,.2f}.
The imputation in Task 4 did not change revenue: SQL already treated a missing
discount as 0 using COALESCE, and rating is not part of the order_value formula.
""")


# In[17]:


# Task 6 — IQR outlier detection on quantity

print("\n" + "=" * 60)
print("Task 6 — IQR outlier detection on quantity")
print("=" * 60)

q1 = merged['quantity'].quantile(0.25)
q3 = merged['quantity'].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
print(f"Q1 = {q1}, Q3 = {q3}, IQR = {iqr}, lower = {lower}, upper = {upper}")

merged['is_outlier'] = (merged['quantity'] < lower) | (merged['quantity'] > upper)
outliers = merged[merged['is_outlier']]
print(f"Outlier rows outside [{lower}, {upper}]: {len(outliers)} (flagged, not dropped)")
print(outliers[['order_id', 'order_date', 'quantity']])


# In[18]:


# Task 7 — Hypothesis: does COD have a higher return rate?

print("\n" + "=" * 60)
print("Task 7 — Hypothesis: does COD have a higher return rate?")
print("=" * 60)

print("Hypothesis: COD orders have a higher return rate than CARD or UPI orders.")

pay = merged.groupby('payment_method')['returned'].agg(['count', 'mean'])
pay['return_rate_pct'] = (pay['mean'] * 100).round(1)
print(pay)

rr = pay['return_rate_pct']
verdict = "CONFIRMED" if rr['COD'] > rr['CARD'] and rr['COD'] > rr['UPI'] else "BUSTED"
print(f"Verdict: {verdict}. COD returns at {rr['COD']}%, about {rr['COD'] / rr['CARD']:.0f}x Card ({rr['CARD']}%), vs UPI {rr['UPI']}%.")


# In[19]:


# Task 8 — Multi-level segmentation

print("\n" + "=" * 60)
print("Task 8 — Multi-level segmentation")
print("=" * 60)

seg = merged.groupby(['payment_method', 'city_tier'])['returned'].agg(['count', 'mean'])
seg['return_rate_pct'] = (seg['mean'] * 100).round(1)
print(seg)


method, tier = seg['return_rate_pct'].idxmax()
top_rate = seg.loc[(method, tier), 'return_rate_pct']
print(f"\nHighest-risk segment: {method} + Tier-{int(tier)} cities at {top_rate}%")


cod1 = seg.loc[('COD', 1)]
cod2 = seg.loc[('COD', 2)]
cod_overall = pay.loc['COD', 'return_rate_pct']      # 44.4, from Task 7

print(f"Tier-1 COD: {int(cod1['count'])} orders at {cod1['return_rate_pct']}%")
print(f"Tier-2 COD: {int(cod2['count'])} orders at {cod2['return_rate_pct']}%")

print(f"COD risk is not uniform across tiers: the blended COD rate of {cod_overall}% "
      f"hides that the problem is concentrated in Tier-2 cities ({cod2['return_rate_pct']}%).")


# In[20]:


# Task 9 — Correlation analysis

print("\n" + "=" * 60)
print("Task 9 — Correlation analysis")
print("=" * 60)

cols = ['rating', 'returned', 'discount_pct', 'quantity']
corr = merged[cols].corr()
print(corr.round(3))

def band(r):
    a = abs(r)
    if a < 0.2:
        return "negligible"
    elif a < 0.4:
        return "weak"
    elif a < 0.7:
        return "moderate"
    else:
        return "strong"



pairs = [
    ('rating', 'returned'),
    ('rating', 'discount_pct'),
    ('rating', 'quantity'),
    ('returned', 'discount_pct'),
    ('returned', 'quantity'),
    ('discount_pct', 'quantity'),
]

print("Bands: negligible 0-0.19 | weak 0.2-0.39 | moderate 0.4-0.69 | strong 0.7-1.0")
for a, b in pairs:
    r = corr.loc[a, b]
    print(f"{a} vs {b}: r = {r:.3f} -> {band(r)}")

r_disc = corr.loc['discount_pct', 'returned']
verdict = "CONFIRMED" if r_disc <= -0.2 else "BUSTED"
print(f"Hypothesis 'higher discounts reduce returns': r = {r_disc:.2f} ({band(r_disc)}) -> {verdict}")


# In[21]:


# Task 10 — Outlier-corrected time series

print("\n" + "=" * 60)
print("Task 10 — Outlier-corrected time series")
print("=" * 60)

# Convert dates and extract year-month
merged['order_date'] = pd.to_datetime(merged['order_date'])
merged['year_month'] = merged['order_date'].dt.strftime('%Y-%m')

# (1) Monthly revenue INCLUDING the two outlier orders
monthly_all = merged.groupby('year_month')['order_value'].sum().round(2)
print("(1) Monthly revenue including outliers:")
print(monthly_all.map('{:.2f}'.format))

# (2) Monthly revenue EXCLUDING the two outlier orders
monthly_clean = merged[~merged['is_outlier']].groupby('year_month')['order_value'].sum().round(2)
print("\n(2) Monthly revenue outlier-corrected:")
print(monthly_clean.map('{:.2f}'.format))

# Find the peak month in each version
peak_all = monthly_all.idxmax()
peak_clean = monthly_clean.idxmax()
print("\nPeak month incl. outliers:", peak_all, "| Peak month outlier-corrected:", peak_clean)

# Build the explanation from the data
out_desc = " and ".join(
    f"{r.order_id} on {r.order_date:%Y-%m-%d} (qty {r.quantity})"
    for r in merged[merged['is_outlier']].itertuples()
)
infl_name = pd.to_datetime(peak_all).strftime('%B')      # "January"
peak_name = pd.to_datetime(peak_clean).strftime('%B')    # "March"

print(f"""
{infl_name}'s apparent lead (Rs {monthly_all[peak_all]:,.2f}) is an artifact of the two
bulk orders that both landed in {infl_name}: {out_desc}.
Excluding them, {infl_name} drops to Rs {monthly_clean[peak_all]:,.2f}, and
{peak_name} (Rs {monthly_clean[peak_clean]:,.2f}) is the genuine peak month.
""")


# In[23]:


print("\n" + "=" * 60)
print("EXPORT — narrator/findings.json")
print("=" * 60)

import json

findings = {
    "cleaned_total_revenue_inr": float(cleaned_total),
    "raw_total_revenue_inr": float(raw_total),
    "duplicate_reconciliation_delta_inr": float(delta),
    "return_rate_by_payment": {
        "COD":  float(pay.loc['COD', 'return_rate_pct']),
        "CARD": float(pay.loc['CARD', 'return_rate_pct']),
        "UPI":  float(pay.loc['UPI', 'return_rate_pct']),
    },
    "highest_risk_segment": {
        "payment_method": method,
        "city_tier": int(tier),
        "return_rate_pct": float(top_rate),
    },
    "true_peak_month": {
        "month": peak_clean,
        "revenue_inr": float(monthly_clean[peak_clean]),
    },
    "outlier_inflated_month": {
        "month": peak_all,
        "apparent_revenue_inr": float(monthly_all[peak_all]),
        "corrected_revenue_inr": float(monthly_clean[peak_all]),
    },
}

with open("narrator/findings.json", "w") as f:
    json.dump(findings, f, indent=2)

print(json.dumps(findings, indent=2))
print("Wrote narrator/findings.json")


# In[ ]:




