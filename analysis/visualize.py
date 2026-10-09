#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import matplotlib.pyplot as plt

customers = pd.read_csv("data/customers.csv")
products  = pd.read_csv("data/products.csv")
orders    = pd.read_csv("data/orders.csv")

# Task 2: fix casing
orders['payment_method'] = orders['payment_method'].str.strip().str.upper()

# Task 3: remove duplicates
key = ['customer_id', 'product_id', 'order_date', 'quantity',
       'discount_pct', 'payment_method', 'rating', 'returned']
orders_clean = orders[~orders.duplicated(subset=key, keep='first')].copy()

# Task 4: fill missing values
orders_clean['discount_pct'] = orders_clean['discount_pct'].fillna(0)
orders_clean['rating'] = orders_clean['rating'].fillna(orders_clean['rating'].median())

# Task 5: merge and compute order value
merged = orders_clean.merge(products, on='product_id').merge(customers, on='customer_id')
merged['order_value'] = merged['quantity'] * merged['price'] * (1 - merged['discount_pct'] / 100)

# Task 6: flag outliers
q1, q3 = merged['quantity'].quantile(0.25), merged['quantity'].quantile(0.75)
iqr = q3 - q1
merged['is_outlier'] = (merged['quantity'] < q1 - 1.5*iqr) | (merged['quantity'] > q3 + 1.5*iqr)


# In[2]:


# Return rate per payment method, highest first
rates = (merged.groupby('payment_method')['returned'].mean() * 100).round(1)
rates = rates.sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(rates.index, rates.values, color=['#eb6834', '#2a78d6', '#2a78d6'])

# Put the exact % on top of each bar
for bar, value in zip(bars, rates.values):
    ax.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value}%",
            ha='center', fontsize=12, fontweight='bold')

ratio = rates['COD'] / rates['CARD']
ax.set_title(f"COD Returns at {rates['COD']}% — {ratio:.0f}x Card")
ax.set_xlabel("Payment method")
ax.set_ylabel("Return rate (%)")
ax.set_ylim(0, rates.max() * 1.2)

plt.tight_layout()
plt.savefig("visualizations/return_rate_by_payment.png", dpi=150)
plt.close()


# In[3]:


merged['year_month'] = pd.to_datetime(merged['order_date']).dt.strftime('%Y-%m')
monthly_clean = merged[~merged['is_outlier']].groupby('year_month')['order_value'].sum().round(2)

peak = monthly_clean.idxmax()
peak_name = pd.to_datetime(peak).strftime('%B %Y')     # "2026-03" becomes "March 2026"

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(monthly_clean.index, monthly_clean.values, marker='o', linewidth=2, color='#2a78d6')

# Highlight the peak point
ax.plot(peak, monthly_clean[peak], marker='o', markersize=12, color='#eb6834')
ax.annotate(f"Peak: Rs {monthly_clean[peak]:,.2f}", (peak, monthly_clean[peak]),
            textcoords="offset points", xytext=(10, 8), fontweight='bold')

ax.set_title(f"{peak_name} Is the True Revenue Peak (Outlier-Corrected)")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (Rs)")
ax.set_ylim(0, monthly_clean.max() * 1.2)

plt.tight_layout()
plt.savefig("visualizations/monthly_revenue_trend.png", dpi=150)
plt.close()


# In[ ]:




