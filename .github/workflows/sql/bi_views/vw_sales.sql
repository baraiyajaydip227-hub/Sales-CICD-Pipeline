
CREATE OR REPLACE VIEW vw_sales AS
SELECT
    OrderID,
    OrderDate,
    City,
    Category,
    Product,
    Quantity,
    UnitPrice,
    Quantity * UnitPrice AS SalesAmount
FROM SALES;
