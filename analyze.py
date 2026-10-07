"""Retail Operations Analytics: KPIs, cash reconciliation, coaching insights, forecast."""
import sqlite3, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

con = sqlite3.connect("store.db")
OUT = Path("output"); OUT.mkdir(exist_ok=True)

# 1. Daily performance: sales, margin, labor % (SQL joins/CTEs)
daily = pd.read_sql("""
WITH s AS (SELECT sale_date, SUM(revenue) rev, SUM(revenue-cogs) gp, COUNT(*) txns
           FROM sales GROUP BY sale_date),
     l AS (SELECT sale_date, SUM(hours*wage) labor, SUM(hours) hrs FROM shifts GROUP BY sale_date)
SELECT s.sale_date, s.rev, s.gp, s.txns, l.labor, l.hrs,
       ROUND(100.0*l.labor/s.rev,1) AS labor_pct,
       ROUND(s.rev/l.hrs,2) AS sales_per_labor_hr
FROM s JOIN l USING(sale_date) ORDER BY sale_date""", con, parse_dates=["sale_date"])
daily.to_csv(OUT/"daily_kpis.csv", index=False)

# 2. Cash reconciliation: expected cash vs deposit, flag variances
recon = pd.read_sql("""
SELECT d.sale_date,
       ROUND(SUM(CASE WHEN s.payment='cash' THEN s.revenue END),2) AS expected,
       d.deposited,
       ROUND(d.deposited - SUM(CASE WHEN s.payment='cash' THEN s.revenue END),2) AS variance
FROM deposits d JOIN sales s USING(sale_date) GROUP BY d.sale_date""", con)
flags = recon[recon.variance.abs() > 0.01]
flags.to_csv(OUT/"reconciliation_exceptions.csv", index=False)

# 3. Credit application coaching: submit rate by associate
credit = pd.read_sql("""
SELECT associate, SUM(offers) offers, SUM(submitted) submitted,
       ROUND(100.0*SUM(submitted)/SUM(offers),1) AS submit_rate_pct
FROM credit_apps GROUP BY associate ORDER BY submit_rate_pct DESC""", con)
credit["vs_team_avg"] = (credit.submit_rate_pct -
                         100*credit.submitted.sum()/credit.offers.sum()).round(1)
credit.to_csv(OUT/"credit_app_by_associate.csv", index=False)

# 4. Category mix and margin
cat = pd.read_sql("""SELECT category, SUM(revenue) rev,
       ROUND(100.0*SUM(revenue-cogs)/SUM(revenue),1) AS margin_pct
       FROM sales GROUP BY category ORDER BY rev DESC""", con)
cat.to_csv(OUT/"category_mix.csv", index=False)

# 5. 7-day forecast: day-of-week average x recent 4-week trend
daily["dow"] = daily.sale_date.dt.dayofweek
dow_avg = daily.groupby("dow").rev.mean()
recent = daily.tail(28).rev.mean() / daily.rev.mean()
last = daily.sale_date.max()
fc = pd.DataFrame({"date": [last + pd.Timedelta(days=i) for i in range(1, 8)]})
fc["forecast_rev"] = [round(dow_avg[d.dayofweek] * recent, 2) for d in fc.date]
fc["suggested_labor_hrs"] = (fc.forecast_rev / daily.sales_per_labor_hr.mean()).round(1)
fc.to_csv(OUT/"forecast_next_7_days.csv", index=False)

# Charts
fig, ax = plt.subplots(2, 2, figsize=(13, 8))
daily.set_index("sale_date").rev.rolling(7).mean().plot(ax=ax[0,0], title="7-Day Avg Daily Revenue")
daily.set_index("sale_date").labor_pct.rolling(7).mean().plot(ax=ax[0,1], title="7-Day Avg Labor % of Sales")
credit.set_index("associate").submit_rate_pct.plot.bar(ax=ax[1,0], title="Credit App Submit Rate by Associate (%)")
ax[1,1].bar(fc.date.dt.strftime("%a"), fc.forecast_rev); ax[1,1].set_title("Forecast Revenue - Next 7 Days")
plt.tight_layout(); plt.savefig(OUT/"dashboard.png", dpi=130)

# Summary
print(f"Total revenue: ${daily.rev.sum():,.0f} | Gross margin: {100*daily.gp.sum()/daily.rev.sum():.1f}%")
print(f"Avg labor % of sales: {daily.labor_pct.mean():.1f}%")
print(f"Reconciliation exceptions: {len(flags)} of {len(recon)} days "
      f"(net variance ${flags.variance.sum():,.2f})")
print(f"Top credit-app associate: {credit.iloc[0].associate} ({credit.iloc[0].submit_rate_pct}%) | "
      f"Lowest: {credit.iloc[-1].associate} ({credit.iloc[-1].submit_rate_pct}%)")
print("\nForecast:\n", fc.to_string(index=False))
