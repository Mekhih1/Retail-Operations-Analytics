"""Generate a synthetic retail dataset (SQLite) modeled on a mall apparel store.
All data is simulated - no real company or customer information."""
import sqlite3, random
from datetime import date, timedelta

random.seed(42)
DB = "store.db"
START, DAYS = date(2026, 4, 1), 120
CATEGORIES = {"Tops": (45, .55), "Bottoms": (70, .50), "Dresses": (110, .48),
              "Outerwear": (160, .45), "Accessories": (35, .60)}
ASSOCIATES = [f"A{str(i).zfill(2)}" for i in range(1, 13)]
DOW_FACTOR = [0.8, 0.85, 0.9, 1.0, 1.25, 1.6, 1.3]  # Mon..Sun traffic

def build():
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.executescript("""
    DROP TABLE IF EXISTS sales; DROP TABLE IF EXISTS shifts;
    DROP TABLE IF EXISTS deposits; DROP TABLE IF EXISTS credit_apps;
    CREATE TABLE sales(txn_id INTEGER PRIMARY KEY, sale_date TEXT, associate TEXT,
        category TEXT, units INTEGER, revenue REAL, cogs REAL, payment TEXT);
    CREATE TABLE shifts(sale_date TEXT, associate TEXT, hours REAL, wage REAL);
    CREATE TABLE deposits(sale_date TEXT, deposited REAL);
    CREATE TABLE credit_apps(sale_date TEXT, associate TEXT, offers INTEGER, submitted INTEGER);
    """)
    txn = 1
    for d in range(DAYS):
        day = START + timedelta(days=d)
        n_txn = int(random.gauss(55, 8) * DOW_FACTOR[day.weekday()])
        cash_total = 0.0
        for _ in range(n_txn):
            cat = random.choice(list(CATEGORIES))
            price, margin = CATEGORIES[cat]
            units = random.choices([1, 2, 3], [.6, .3, .1])[0]
            rev = round(price * units * random.uniform(.7, 1.1), 2)  # promos/markdowns
            cogs = round(rev * (1 - margin) * random.uniform(.9, 1.1), 2)
            pay = random.choices(["card", "cash", "gift"], [.78, .17, .05])[0]
            c.execute("INSERT INTO sales VALUES(?,?,?,?,?,?,?,?)",
                      (txn, day.isoformat(), random.choice(ASSOCIATES), cat, units, rev, cogs, pay))
            if pay == "cash": cash_total += rev
            txn += 1
        # deposits: usually exact, occasionally off (injected anomalies)
        variance = random.choice([0]*17 + [-5, -12.5, 8, -40, 20])
        c.execute("INSERT INTO deposits VALUES(?,?)", (day.isoformat(), round(cash_total + variance, 2)))
        for a in random.sample(ASSOCIATES, random.randint(4, 8)):
            c.execute("INSERT INTO shifts VALUES(?,?,?,?)",
                      (day.isoformat(), a, random.choice([4, 5, 6, 8]), 17.5))
            offers = random.randint(8, 20)
            c.execute("INSERT INTO credit_apps VALUES(?,?,?,?)",
                      (day.isoformat(), a, offers, int(offers * random.uniform(.05, .3))))
    con.commit(); con.close()
    print(f"Built {DB} with {txn-1} transactions over {DAYS} days")

if __name__ == "__main__":
    build()
