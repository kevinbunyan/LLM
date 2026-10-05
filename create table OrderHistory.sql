

SELECT e.*, d.EventYear, d.EventMonth, d.EventMonthRank, d.EventMonthRankReverse, c.CustomerName, [ProductName], ProductCategory 
into  OrderHistory 
FROM [live].[dbo].[tblEvent] as e 
join live.dbo.tblDateDimension as d on e.EventYYMMDD = d.EventYYMMDD 
join [live].[dbo].tblCustomer as c on e.CustomerID = C.CustomerID 
join [live].[dbo].tblProduct as p on e.productid = p.productid 
join live.dbo.tblProductCategory as pc on p.productid = pc.productid



