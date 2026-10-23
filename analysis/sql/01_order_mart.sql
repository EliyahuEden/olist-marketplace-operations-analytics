-- SQLite 3.25+. Grain: exactly one row per source order.
-- Aggregate each child BEFORE joining to prevent items x payments x reviews fan-out.
DROP TABLE IF EXISTS fact_order;
CREATE TABLE fact_order AS
WITH items AS (
 SELECT order_id, SUM(price) AS gmv, SUM(freight_value) AS freight,
        COUNT(*) AS units, COUNT(DISTINCT seller_id) AS seller_count
 FROM order_items GROUP BY order_id
), payments_agg AS (
 SELECT order_id, SUM(payment_value) AS payment_value FROM payments GROUP BY order_id
), review_rank AS (
 SELECT *, ROW_NUMBER() OVER (
 PARTITION BY order_id ORDER BY review_answer_timestamp DESC, review_creation_date DESC, review_id DESC
 ) AS rn FROM reviews
), category_values AS (
 SELECT i.order_id, COALESCE(t.product_category_name_english,'unclassified') AS category,
 SUM(i.price) AS category_gmv
 FROM order_items i LEFT JOIN products p USING(product_id)
 LEFT JOIN category_translation t USING(product_category_name)
 GROUP BY i.order_id, COALESCE(t.product_category_name_english,'unclassified')
), category_rank AS (
 SELECT *, ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY category_gmv DESC, category) AS rn
 FROM category_values
)
SELECT o.*, c.customer_unique_id, c.customer_state, c.customer_city,
 COALESCE(i.gmv,0) AS gmv, COALESCE(i.freight,0) AS freight,
 COALESCE(i.units,0) AS units, COALESCE(i.seller_count,0) AS seller_count,
 p.payment_value, r.review_score, COALESCE(k.category,'unclassified') AS primary_category,
 substr(o.order_purchase_timestamp,1,7) AS purchase_month,
 CASE WHEN o.order_status='delivered' AND o.order_delivered_customer_date IS NOT NULL
 AND o.order_estimated_delivery_date IS NOT NULL THEN 1 ELSE 0 END AS delivery_eligible,
 CASE WHEN o.order_status='delivered' AND o.order_delivered_customer_date IS NOT NULL
 AND o.order_estimated_delivery_date IS NOT NULL
 THEN CASE WHEN date(o.order_delivered_customer_date)>date(o.order_estimated_delivery_date)
 THEN 1 ELSE 0 END END AS is_late,
 CASE WHEN o.order_status='delivered' AND o.order_delivered_customer_date IS NOT NULL
 THEN julianday(o.order_delivered_customer_date)-julianday(o.order_purchase_timestamp) END AS delivery_days
FROM orders o JOIN customers c USING(customer_id)
LEFT JOIN items i USING(order_id)
LEFT JOIN payments_agg p USING(order_id)
LEFT JOIN review_rank r ON o.order_id=r.order_id AND r.rn=1
LEFT JOIN category_rank k ON o.order_id=k.order_id AND k.rn=1;
CREATE UNIQUE INDEX ix_fact_order ON fact_order(order_id);
CREATE INDEX ix_fact_month_state ON fact_order(purchase_month,customer_state);

DROP TABLE IF EXISTS fact_item;
CREATE TABLE fact_item AS
SELECT i.*, s.seller_state, s.seller_city,
 COALESCE(t.product_category_name_english,'unclassified') AS category
FROM order_items i LEFT JOIN sellers s USING(seller_id)
LEFT JOIN products p USING(product_id)
LEFT JOIN category_translation t USING(product_category_name);
CREATE UNIQUE INDEX ix_fact_item ON fact_item(order_id,order_item_id);
