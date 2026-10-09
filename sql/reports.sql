USE mamaearth;

-- (a) Order totals

-- Output:
--   total_orders | total_revenue | avg_order_value
--   180          | 99860.20      | 554.78

SELECT COUNT(*) AS total_orders,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100)), 2) AS total_revenue,
       ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100)), 2) AS avg_order_value
FROM orders o
JOIN products p ON p.product_id = o.product_id;


-- (b) COUNT(*) vs COUNT(column)

-- Output:
--   total_rows | rated_rows | unrated_rows
--   180        | 165        | 15

SELECT COUNT(*) AS total_rows,
       COUNT(rating) AS rated_rows,
       COUNT(*) - COUNT(rating) AS unrated_rows
FROM orders;

-- c) LEFT JOIN with a genuine zero-match row 

-- c1)
-- Output:
--   customer_id | name 
--   C045        | Vihaan

SELECT c.customer_id, c.name from customers c LEFT JOIN orders o on c.customer_id= o.customer_id 
GROUP BY c.customer_id, c.name HAVING COUNT(o.order_id) = 0;

-- c2)
-- Output:
--   customer_id | name 
--   C045        | Vihaan

SELECT customer_id, name from customers WHERE
customer_id NOT IN (SELECT DISTINCT customer_id FROM orders);

-- d) GROUP BY + HAVING

-- Output:
--  city      | total_orders | returned_orders | return_rte_pct 
--  Jaipur	  | 19           |  8	           | 42.1
--  Lucknow	  | 49           |  15             | 30.6
--  Bangalore | 33       	 |  8	           | 24.2

SELECT c.city, COUNT(*) as total_orders, SUM(o.returned) as returned_orders, ROUND(100*SUM(o.returned)/COUNT(*),1) as return_rate_pct from customers c JOIN orders o on c.customer_id = o.customer_id 
GROUP BY c.city HAVING return_rate_pct > 20 ORDER BY return_rate_pct DESC;

-- e) Ranking with ORDER BY + LIMIT/OFFSET

-- e1)
-- Output:
-- customer_id | name    | total_spend
--  C043	   | Reyansh | 12920.00
--  C026       | Isha    |	8371.60
--  C008	   | Meera	 | 4564.60
--  C011	   | Arjun	 | 4111.00
--  C042	   | Sanya   |	3785.00

-- -- customer_id ASC tie-break makes the ranking deterministic so LIMIT/OFFSET pages never shuffle tied rows.
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100)), 2) AS total_spend
FROM orders o
JOIN products p  ON p.product_id = o.product_id
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name 
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 5;

-- e2)
-- Output:
-- customer_id | name    | total_spend
--  C008	   | Meera	 | 4564.60
--  C011	   | Arjun	 | 4111.00
--  C042	   | Sanya   |	3785.00

SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100)), 2) AS total_spend
FROM orders o
JOIN products p  ON p.product_id = o.product_id
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name 
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 3 OFFSET 2;

-- f) Three-table JOIN with GROUP BY

-- Output:
-- category     | order_count | category_revenue
-- Haircare     | 54	      | 44956.10
-- Skincare	    | 60	      | 27346.00
-- Babycare	    | 30          |	16805.00
-- PersonalCare	| 36	      | 10753.10

SELECT category, COUNT(o.order_id) as order_count, ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100)),2) as category_revenue 
FROM orders o JOIN products p ON o.product_id=p.product_id
JOIN customers c ON c.customer_id = o.customer_id 
GROUP BY p.category ORDER BY category_revenue DESC;

-- g) LIKE pattern match 

-- Output:
-- customer_id | name
-- C001	       | Aarav
-- C003        | Aditi
-- C004	       | Ananya
-- C011	       | Arjun
-- C021	       | Aryan
-- C030	       | Anika
-- C031	       | Aditya
-- C036	       | Aisha
-- C041        | Ayaan
-- C044	       | Aria
	
SELECT customer_id, name from customers where name LIKE 'A%' LIMIT 10;

-- h) DISTINCT

-- Output:
-- acquisition_source
-- Organic
-- Referral
-- Ad
-- Social

SELECT DISTINCT acquisition_source from customers;

-- i) ALTER TABLE + UPDATE with CASE

ALTER TABLE customers ADD COLUMN loyalty_tier VARCHAR(10);

SET SQL_SAFE_UPDATES = 0;
UPDATE customers
SET loyalty_tier = CASE WHEN city_tier = 1 THEN 'Gold' ELSE 'Silver' END;

-- Output:
-- loyalty_tier | COUNT(*)
-- Gold	        | 28
-- Silver	    | 17

SELECT loyalty_tier, COUNT(*) FROM customers GROUP BY loyalty_tier;