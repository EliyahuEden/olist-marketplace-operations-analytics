# Native Power BI DAX measures

All measures are attached to Orders. Source snapshot tables and relationships are in Olist.SemanticModel/model.bim.

## Orders

Folder: Business KPIs

```dax
Orders = COUNTROWS(Orders)
```
Format: `#,0`

## Delivered Orders

Folder: Business KPIs

```dax
Delivered Orders = CALCULATE([Orders], Orders[Status] = "delivered")
```
Format: `#,0`

## Delivered GMV

Folder: Business KPIs

```dax
Delivered GMV = CALCULATE(SUM(Orders[GMV]), Orders[Status] = "delivered")
```
Format: `"R$ "#,0.00`

## AOV

Folder: Business KPIs

```dax
AOV = DIVIDE([Delivered GMV], [Delivered Orders])
```
Format: `"R$ "#,0`

## Eligible Deliveries

Folder: Business KPIs

```dax
Eligible Deliveries = CALCULATE([Orders], Orders[Eligible] = 1)
```
Format: `#,0`

## Late Orders

Folder: Business KPIs

```dax
Late Orders = CALCULATE([Orders], Orders[Eligible] = 1, Orders[Late] = 1)
```
Format: `#,0`

## Late Rate

Folder: Business KPIs

```dax
Late Rate = DIVIDE([Late Orders], [Eligible Deliveries])
```
Format: `0.0%`

## On Time Rate

Folder: Business KPIs

```dax
On Time Rate = IF([Eligible Deliveries]>0, 1-[Late Rate])
```
Format: `0.0%`

## Reviewed Deliveries

Folder: Business KPIs

```dax
Reviewed Deliveries = CALCULATE([Eligible Deliveries], KEEPFILTERS(NOT ISBLANK(Orders[ReviewScore])))
```
Format: `#,0`

## Average Review

Folder: Business KPIs

```dax
Average Review = CALCULATE(AVERAGE(Orders[ReviewScore]), Orders[Eligible]=1)
```
Format: `0.00`

## Low Rating Rate

Folder: Business KPIs

```dax
Low Rating Rate = DIVIDE(CALCULATE([Reviewed Deliveries], Orders[ReviewScore] IN {1,2}), [Reviewed Deliveries])
```
Format: `0.0%`

## Low Rating Late

Folder: Business KPIs

```dax
Low Rating Late = CALCULATE([Low Rating Rate], Orders[Late]=1)
```
Format: `0.0%`

## Low Rating On Time

Folder: Business KPIs

```dax
Low Rating On Time = CALCULATE([Low Rating Rate], Orders[Late]=0)
```
Format: `0.0%`

## Rating Risk Ratio

Folder: Business KPIs

```dax
Rating Risk Ratio = DIVIDE([Low Rating Late],[Low Rating On Time])
```
Format: `0.0"×"`

## Median Delivery Days

Folder: Business KPIs

```dax
Median Delivery Days = CALCULATE(MEDIAN(Orders[DeliveryDays]), Orders[Eligible]=1)
```
Format: `0.0" days"`

## Freight Ratio

Folder: Business KPIs

```dax
Freight Ratio = DIVIDE(CALCULATE(SUM(Orders[Freight]),Orders[Status]="delivered"),[Delivered GMV])
```
Format: `0.0%`

## GMV Headline

Folder: Display

```dax
GMV Headline = "R$ " & FORMAT(DIVIDE([Delivered GMV],1000000),"0.00") & "M"
```

## Delivered Caption

Folder: Display

```dax
Delivered Caption = FORMAT([Delivered Orders],"#,0") & " delivered orders · excludes freight"
```

## Late Caption

Folder: Display

```dax
Late Caption = FORMAT([Late Orders],"#,0") & " late / " & FORMAT([Eligible Deliveries],"#,0") & " eligible"
```

## Review Caption

Folder: Display

```dax
Review Caption = FORMAT([Reviewed Deliveries],"#,0") & " reviewed eligible deliveries"
```

## Scope Caption

Folder: Display

```dax
Scope Caption = FORMAT([Orders],"#,0") & " orders in view"
```

## Growth Benchmark

Folder: Fixed benchmarks

```dax
Growth Benchmark = MAX(Benchmarks[YTDGrowth])
```
Format: `+0.0%;-0.0%`

## Repeat Benchmark

Folder: Fixed benchmarks

```dax
Repeat Benchmark = MAX(Benchmarks[Repeat90])
```
Format: `0.0%`

## Risk Base Rate

Folder: Fixed benchmarks

```dax
Risk Base Rate = MAX(Benchmarks[RiskBaseRate])
```
Format: `0.0%`

## Risk Flagged Rate

Folder: Fixed benchmarks

```dax
Risk Flagged Rate = MAX(Benchmarks[RiskFlaggedRate])
```
Format: `0.0%`

## Risk Lift

Folder: Fixed benchmarks

```dax
Risk Lift = MAX(Benchmarks[RiskLift])
```
Format: `0.00"×"`

## Risk Capture

Folder: Fixed benchmarks

```dax
Risk Capture = MAX(Benchmarks[RiskCapture])
```
Format: `0.0%`

## Cohort Repeat Rate

Folder: Fixed benchmarks

```dax
Cohort Repeat Rate = MAX(Cohorts[Repeat90])
```
Format: `0.0%`

## Cohort Buyers

Folder: Fixed benchmarks

```dax
Cohort Buyers = SUM(Cohorts[Customers])
```
Format: `#,0`

## Reduction Rate

Folder: Scenario

```dax
Reduction Rate = DIVIDE(SELECTEDVALUE(Reduction[Value],20),100)
```
Format: `0%`

## Avoided Late Orders

Folder: Scenario

```dax
Avoided Late Orders = ROUND([Late Orders]*[Reduction Rate],0)
```
Format: `#,0`

## Scenario Late Rate

Folder: Scenario

```dax
Scenario Late Rate = [Late Rate]*(1-[Reduction Rate])
```
Format: `0.0%`

## Scenario Caption

Folder: Scenario

```dax
Scenario Caption = FORMAT([Late Rate],"0.0%") & " → " & FORMAT([Scenario Late Rate],"0.0%") & " late rate"
```

## Top Category GMV

Folder: Ranking

```dax
Top Category GMV = IF(RANKX(ALLSELECTED(Categories[Category]),[Delivered GMV],,DESC,Dense)<=6,[Delivered GMV])
```
Format: `"R$ "#,0`

## Top State Late Orders

Folder: Ranking

```dax
Top State Late Orders = IF(RANKX(ALLSELECTED(States[State]),[Late Orders],,DESC,Dense)<=6,[Late Orders])
```
Format: `#,0`

## Eligible Share

Folder: Business KPIs

```dax
Eligible Share = DIVIDE([Eligible Deliveries],CALCULATE([Eligible Deliveries],REMOVEFILTERS(States)))
```
Format: `0.0%`

## Delivery Band Share

Folder: Business KPIs

```dax
Delivery Band Share = DIVIDE([Eligible Deliveries],CALCULATE([Eligible Deliveries],REMOVEFILTERS(Orders[DeliveryBand],Orders[DeliveryBandOrder])))
```
Format: `0.0%`

## Seller Eligible

Folder: Seller investigation

```dax
Seller Eligible = CALCULATE([Eligible Deliveries],NOT ISBLANK(Orders[SingleSellerId]))
```
Format: `#,0`

## Seller Late

Folder: Seller investigation

```dax
Seller Late = CALCULATE([Late Orders],NOT ISBLANK(Orders[SingleSellerId]))
```
Format: `#,0`

## Seller Rate

Folder: Seller investigation

```dax
Seller Rate = DIVIDE([Seller Late],[Seller Eligible])
```
Format: `0.0%`

## Queue Eligible

Folder: Seller investigation

```dax
Queue Eligible = IF([Seller Eligible]>=100 && NOT ISBLANK(SELECTEDVALUE(Sellers[SellerId])), [Seller Eligible])
```
Format: `#,0`

## Queue Late

Folder: Seller investigation

```dax
Queue Late = IF([Seller Eligible]>=100 && NOT ISBLANK(SELECTEDVALUE(Sellers[SellerId])), [Seller Late])
```
Format: `#,0`

## Queue Rate

Folder: Seller investigation

```dax
Queue Rate = IF([Seller Eligible]>=100 && NOT ISBLANK(SELECTEDVALUE(Sellers[SellerId])), [Seller Rate])
```
Format: `0.0%`

## Queue GMV

Folder: Seller investigation

```dax
Queue GMV = IF([Seller Eligible]>=100 && NOT ISBLANK(SELECTEDVALUE(Sellers[SellerId])), [Delivered GMV])
```
Format: `"R$ "#,0`
