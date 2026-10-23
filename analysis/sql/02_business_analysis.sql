-- All dashboard KPIs use orders purchased Jan 2017-Aug 2018 inclusive.
-- Delivered merchandise value excludes freight and is NOT Olist revenue or profit.
SELECT COUNT(*) AS orders,
 SUM(CASE WHEN order_status='delivered' THEN gmv ELSE 0 END) AS delivered_gmv,
 SUM(CASE WHEN order_status='delivered' THEN gmv ELSE 0 END)
 / NULLIF(SUM(order_status='delivered'),0) AS delivered_aov,
 1.0*SUM(is_late)/NULLIF(SUM(delivery_eligible),0) AS late_rate
FROM fact_order WHERE purchase_month BETWEEN '2017-01' AND '2018-08';

-- Growth: compare matching months; never compare full 2017 with partial 2018.
SELECT substr(purchase_month,1,4) AS year, COUNT(*) AS delivered_orders,SUM(gmv) AS gmv
FROM fact_order WHERE order_status='delivered'
AND substr(purchase_month,6,2) BETWEEN '01' AND '08'
AND purchase_month BETWEEN '2017-01' AND '2018-08' GROUP BY 1;

-- Association, not causal impact: dissatisfaction among rated, eligible orders.
SELECT is_late, COUNT(*) AS rated_orders, AVG(review_score) AS avg_review,
 AVG(CASE WHEN review_score<=2 THEN 1.0 ELSE 0 END) AS low_rating_rate
FROM fact_order WHERE delivery_eligible=1 AND review_score IS NOT NULL
AND purchase_month BETWEEN '2017-01' AND '2018-08' GROUP BY is_late;

-- Seller accountability: order outcomes on SINGLE-SELLER orders only.
-- Multi-seller failures cannot be attributed reliably to a specific seller.
WITH seller_orders AS (
 SELECT DISTINCT f.order_id,i.seller_id, f.is_late, f.gmv
 FROM fact_order f JOIN fact_item i USING(order_id)
 WHERE f.seller_count=1 AND f.delivery_eligible=1
 AND f.purchase_month BETWEEN '2017-01' AND '2018-08'
), totals AS (
 SELECT seller_id,COUNT(*) AS orders,SUM(is_late) AS late_orders,
 AVG(is_late) AS late_rate,SUM(gmv) AS gmv FROM seller_orders GROUP BY 1
)
SELECT *, RANK() OVER(ORDER BY late_orders DESC) AS late_volume_rank
FROM totals WHERE orders>=100 ORDER BY late_orders DESC;

-- Customer identities must use customer_unique_id, not per-order customer_id.
SELECT customer_unique_id,COUNT(*) AS delivered_orders,SUM(gmv) AS observed_value
FROM fact_order WHERE order_status='delivered' GROUP BY 1 HAVING COUNT(*)>1;
