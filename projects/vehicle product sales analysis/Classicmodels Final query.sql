-- Run classic models script
-- Tables are created

-- Overview of sales of 2004. Breakdown by product,country,city and include sales value,cost of sales, net profit

select t1.orderDate, t1.orderNumber, quantityOrdered, priceEach, productName, productLine, buyPrice, city, country
from  orders t1
inner join orderdetails t2
on t1.orderNumber = t2.orderNumber
inner join products t3
on t2.productCode = t3.productCode
inner join customers t4
on t1.customerNumber = t4.customerNumber
where year(orderdate) = 2004;
-- Excel: (classic models 2004--->2004 data and overview
-- Copy these data into excel and calculate sales value,cost of sales, net profit
-- Create pivot table for sum of sales,sum of cost of sales, sum of net profit
-- Create chart of the pivot table

-- Excel: (classic models 2004--->country
-- Overview of sales by country

-- Breakdown of products purchased together
with prod_sales as
(
select orderNumber,t1.productCode,productLine
from orderdetails t1
inner join products t2
on t1.productCode = t2.productCode
)
select distinct t1.orderNumber, t1.productline as prod1, t2.productline as prod2 from
prod_sales t1 left join prod_sales t2
on t1.orderNumber = t2.orderNumber and t1.productline <> t2.productline;

-- Copy the query result into excel
-- Excel: (classic models 2004--->products purchased together
-- Find corealtion using creating pivot table and chart

-- Breakdown of sales by credit limit to see if we can get higher sales for customer who have higher credit limit
with sales as (
select t1.orderNumber, t1.customerNumber,productCode, quantityOrdered, priceEach, priceEach * quantityOrdered as sales_value,creditLimit
from  orders t1
inner join orderdetails t2
on t1.orderNumber = t2.orderNumber
inner join customers t3
on t1.customerNumber = t3.customerNumber
)
select ordernumber, customernumber,
case when creditlimit < 75000 then 'less than 75k'
when creditlimit between 75000 and 100000 then 'btw 75-100k'
when creditlimit between 100000 and 150000 then 'btw 100-150k'
when creditlimit > 100000 then 'greater than 100k'
else 'other'
end as creditlimit_grp,
sum(sales_value) as sales_value
from sales
group by ordernumber, customernumber, creditlimit_grp;

-- Copy the quesry result inot Excel
 -- Excel: (classic models 2004--->credit limit grouped
 -- Create pivot table and chart
 
 -- Sales value change from previous order to see if new customers who make first purchase are likely to spend more
 
 with main_cte as
(
select ordernumber, orderdate, customernumber, sum(sales_value) as sales_value
from
(select t1.orderNumber, orderDate, customerNumber, productCode, quantityOrdered * priceEach as sales_value
from orders t1
inner join orderdetails t2
on t1.orderNumber = t2.orderNumber) main
group by ordernumber, orderdate, customernumber
),

sales_query as
(
select t1.*, customername, row_number() over (partition by customername order by orderdate) as purchasenumber,
lag(sales_value) over(partition by customername order by orderdate) as prev_sales_value
from main_cte t1
inner join customers t2
on t1.customernumber = t2.customernumber)

select *, sales_value-prev_sales_value as purchase_value_change
from sales_query
where prev_sales_value is not null;

-- Copy the quesry result inot Excel
 -- Excel: (classic models 2004--->purchase value change
 -- Create pivot table
 
 -- Office sales by customer country
 with main_cte as
(
select t1.orderNumber,
t2.productCode,
t2.quantityOrdered,
t2.priceEach,
quantityOrdered * priceEach as sales_value,
t3.city as customercity,
t3.country as customercountry,
t4.productLine,
t6.city as office_city,
t6.country as office_country
from orders t1
inner join orderdetails t2
on t1.orderNumber = t2.orderNumber
inner join customers t3
on t1.customerNumber = t3.customerNumber
inner join products t4
on t2.productCode = t4.productCode
inner join employees t5
on t3.salesRepEmployeeNumber = t5.employeeNumber
inner join offices t6
on t5.officeCode = t6.officeCode
)

select 
ordernumber,
customercity,
customercountry,
productline,
office_city,
office_country,
sum(sales_value) as sales_value
from main_cte
group by 
ordernumber,
customercity,
customercountry,
productline,
office_city,
office_country;

-- Copy the quesry result inot Excel
 -- Excel: (classic models 2004 ---> office sales
 -- Create pivot table and chart
 
 -- Customers affected by late shipping
 SELECT *,
date_add(shippeddate, interval 3 day) as latest_arrival,
case when date_add(shippeddate, interval 3 day) > requiredDate then 1 else 0 end as late_flag
FROM orders
where
(case when date_add(shippeddate, interval 3 day) > requiredDate then 1 else 0 end = 1);

-- Customers who have gone over credit limit and money owed
with cte_sales as
(
select
orderDate,
t1.customerNumber,
t1.orderNumber,
customerName,
productCode,
creditLimit,
quantityOrdered * priceEach as sales_value
from orders t1
inner join orderdetails t2
on t1.orderNumber = t2.orderNumber
inner join customers t3
on t1.customerNumber = t3.customerNumber
),

running_total_sales_cte as
(
select *,
lead(orderdate) over (partition by customernumber order by orderdate) as next_order_date
from
	(
	select orderdate,
	ordernumber,
	customernumber,
	customername,creditlimit,
	sum(sales_value) as sales_value
	from cte_sales
	group by
	orderdate,
	ordernumber,
	customernumber,
	customername,
	creditlimit
	) subquery
),

payment_cte as
(select *
from payments),

main_cte as
(
select t1.*,
sum(sales_value) over (partition by t1.customernumber order by orderdate) as running_total_sales,
sum(amount) over (partition by t1.customerNumber order by orderdate) as running_total_payment
from running_total_sales_cte t1
left join payment_cte t2
on t1.customernumber = t2.customernumber and t2.paymentdate between t1.orderdate and case when t1.next_order_date is null then current_date else next_order_date end
)

select * ,running_total_sales - running_total_payment as money_owed,
creditlimit - (running_total_sales - running_total_payment) as difference
from main_cte;

-- Create VIEW for PowerBI
create or replace view sales_data_for_power_bi as

select
orderDate,ord.orderNumber,p.productName,p.productLine,cu.customerName,cu.country as csutomercountry,
o.country as officecountry,
buyPrice,
priceEach,
quantityOrdered,
quantityOrdered * priceEach as sales_value,
quantityOrdered * buyPrice as cost_of_sales
from orders ord
inner join orderdetails ordt
on ord.orderNumber = ordt.orderNumber
inner join customers cu
on ord.customerNumber = cu.customerNumber
inner join products p
on ordt.productCode = p.productCode
inner join employees emp
on cu.salesRepEmployeeNumber = emp.employeeNumber
inner join offices o
on emp.officeCode = o.officeCode;

-- Import thr created view into powerBI to create sales dashboard
