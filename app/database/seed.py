# app/database/seed.py

import random
from datetime import date, timedelta
from app.database.db import get_session, create_all_tables
from app.database.models import Category, Transaction, Anomaly


CATEGORY_DATA = [
    ("Food & Dining",    "#FF6B6B"),
    ("Transport",        "#4ECDC4"),
    ("Utilities",        "#45B7D1"),
    ("Rent & Housing",   "#96CEB4"),
    ("Shopping",         "#FFEAA7"),
    ("Healthcare",       "#DDA0DD"),
    ("Entertainment",    "#98D8C8"),
    ("Education",        "#F7DC6F"),
    ("Salary & Income",  "#82E0AA"),
    ("Transfer",         "#AEB6BF"),
    ("Other",            "#D7DBDD"),
]

SAMPLE_DESCRIPTIONS = {
    "Food & Dining": [
        "MCDONALDS LAHORE DHA", "KFC GULBERG BRANCH",
        "PIZZA HUT DELIVERY ORDER", "CARREFOUR GROCERY STORE",
        "SAVEMART SUPERSTORE PK", "METRO CASH AND CARRY",
        "CHAI WALA CAFE CLIFTON", "BAKERS INN MORNING ORDER",
        "IMTIAZ SUPER MARKET", "STUDENT BIRYANI CANTEEN",
    ],
    "Transport": [
        "UBER TRIP PAYMENT", "CAREEM RIDE BOOKING",
        "PSO FUEL STATION PAYMENT", "TOTAL PARCO PETROL",
        "TOLL PLAZA M2 MOTORWAY", "INDRIVER APP PAYMENT",
        "BUS PASS MONTHLY RECHARGE", "PARKING FEE PAYMENT",
    ],
    "Utilities": [
        "LESCO ELECTRICITY BILL", "SSGC GAS BILL PAYMENT",
        "PTCL BROADBAND MONTHLY", "JAZZ MONTHLY PACKAGE",
        "TELENOR BILL PAYMENT", "IESCO ELECTRICITY BILL",
        "HESCO BILL PAYMENT", "WATER UTILITY CHARGES",
    ],
    "Rent & Housing": [
        "HOUSE RENT PAYMENT JAN", "APARTMENT RENT TRANSFER",
        "FLAT RENT BANK TRANSFER", "PROPERTY MAINTENANCE FEE",
    ],
    "Shopping": [
        "DARAZ.PK ONLINE PURCHASE", "ALKARAM STUDIO KARACHI",
        "GULL AHMED TEXTILE", "BONANZA SATRANGI STORE",
        "HAFEEZ CENTER PURCHASE", "AMAZON INTERNATIONAL",
        "JUNAID JAMSHED STORE",
    ],
    "Healthcare": [
        "AGA KHAN HOSPITAL FEE", "SHAUKAT KHANUM LAB TEST",
        "MEDLIFE PHARMACY", "DR CONSULTATION FEE",
        "CHUGHTAI LAB DIAGNOSTIC", "LIAQUAT NATIONAL HOSPITAL",
    ],
    "Entertainment": [
        "NETFLIX SUBSCRIPTION", "SPOTIFY PREMIUM MONTHLY",
        "CINEMA TICKET BOOKING", "YOUTUBE PREMIUM",
        "AMAZON PRIME VIDEO", "GAME PURCHASE STEAM",
    ],
    "Education": [
        "UNIVERSITY SEMESTER FEE", "COURSERA SUBSCRIPTION",
        "TEXTBOOK PURCHASE", "UDEMY COURSE PAYMENT",
        "TUITION FEE PAYMENT", "LIBRARY MEMBERSHIP FEE",
    ],
    "Salary & Income": [
        "SALARY CREDIT APRIL", "FREELANCE PAYMENT UPWORK",
        "FIVERR WITHDRAWAL", "PROJECT PAYMENT RECEIVED",
        "BONUS CREDIT",
    ],
    "Transfer": [
        "EASYPAISA TRANSFER", "JAZZCASH BANK TRANSFER",
        "RAAST INSTANT PAYMENT", "BANK TRANSFER SENT",
        "FAMILY SUPPORT TRANSFER",
    ],
    "Other": [
        "ATM CASH WITHDRAWAL", "BANK SERVICE CHARGES",
        "MISCELLANEOUS PAYMENT", "UNKNOWN DEBIT",
    ],
}

AMOUNT_RANGES = {
    "Food & Dining":    (150,   3500),
    "Transport":        (80,    1800),
    "Utilities":        (500,   9000),
    "Rent & Housing":   (15000, 55000),
    "Shopping":         (300,   12000),
    "Healthcare":       (300,   18000),
    "Entertainment":    (150,   2500),
    "Education":        (1500,  35000),
    "Salary & Income":  (45000, 180000),
    "Transfer":         (500,   25000),
    "Other":            (100,   5000),
}


def seed_categories(session):
    """Inserts all categories. Skips existing ones — safe to re-run."""
    inserted = 0
    for name, color in CATEGORY_DATA:
        existing = session.query(Category).filter_by(name=name).first()
        if not existing:
            session.add(Category(name=name, color_hex=color))
            inserted += 1

    session.commit()
    total = session.query(Category).count()
    print(f"✓ Categories: {inserted} inserted, {total} total in DB")


def seed_transactions(session, count=200):
    """Generates realistic transactions spread across 6 months."""
    categories = session.query(Category).all()
    if not categories:
        print("No categories found — run seed_categories first")
        return

    cat_by_name = {c.name: c for c in categories}

    today          = date.today()
    six_months_ago = today - timedelta(days=180)

    transactions_added = 0

    weights = {
        "Food & Dining":   25,
        "Transport":       20,
        "Shopping":        12,
        "Entertainment":    8,
        "Healthcare":       6,
        "Education":        5,
        "Utilities":        4,
        "Rent & Housing":   3,
        "Transfer":         7,
        "Salary & Income":  5,
        "Other":            5,
    }

    for _ in range(count):
        cat_name = random.choices(
            list(weights.keys()),
            weights=list(weights.values())
        )[0]

        category = cat_by_name.get(cat_name)
        if not category:
            continue

        description  = random.choice(SAMPLE_DESCRIPTIONS.get(cat_name, ["PAYMENT"]))
        min_amt, max_amt = AMOUNT_RANGES.get(cat_name, (100, 5000))
        amount       = round(random.uniform(min_amt, max_amt), 2)
        random_days  = random.randint(0, 180)
        txn_date     = six_months_ago + timedelta(days=random_days)

        session.add(Transaction(
            date=txn_date,
            description=description,
            amount=amount,
            category_id=category.id,
            confidence=round(random.uniform(0.70, 0.99), 2),
            raw_text=description,
            is_anomaly=False,
        ))
        transactions_added += 1

    session.commit()

    # Add obvious anomalies for demo purposes
    anomaly_data = [
        ("SUSPICIOUS WIRE TRANSFER OVERSEAS", 280000, "Transfer",  "high"),
        ("UNKNOWN MERCHANT DUBAI UAE",          92000, "Shopping",  "high"),
        ("LARGE CASH WITHDRAWAL ATM",           75000, "Other",     "medium"),
        ("DUPLICATE PAYMENT DETECTED",          45000, "Utilities", "medium"),
        ("UNUSUAL LATE NIGHT TRANSACTION",      38000, "Other",     "low"),
    ]

    anomalies_added = 0
    for desc, amt, cat_name, severity in anomaly_data:
        category = cat_by_name.get(cat_name)
        if not category:
            continue

        txn = Transaction(
            date=today - timedelta(days=random.randint(1, 45)),
            description=desc,
            amount=amt,
            category_id=category.id,
            is_anomaly=True,
            confidence=round(random.uniform(0.80, 0.96), 2),
            raw_text=desc,
        )
        session.add(txn)
        session.flush()

        session.add(Anomaly(
            transaction_id=txn.id,
            reason=f"Amount Rs {amt:,.0f} is significantly above category average",
            severity=severity,
        ))
        anomalies_added += 1

    session.commit()

    total = session.query(Transaction).count()
    print(f"✓ Transactions: {transactions_added} normal + {anomalies_added} anomalies = {total} total")


def run_seed():
    """Master function — creates tables then seeds all data."""
    print("\n" + "="*50)
    print("  Expense Intelligence System — DB Setup")
    print("="*50)

    print("\n[1/3] Creating tables...")
    create_all_tables()

    session = get_session()
    try:
        print("\n[2/3] Seeding categories...")
        seed_categories(session)

        print("\n[3/3] Seeding transactions...")
        seed_transactions(session, count=200)

        print("\n" + "="*50)
        cat_count  = session.query(Category).count()
        txn_count  = session.query(Transaction).count()
        anom_count = session.query(Transaction).filter_by(is_anomaly=True).count()

        print(f"  Categories:   {cat_count}")
        print(f"  Transactions: {txn_count}")
        print(f"  Anomalies:    {anom_count}")
        print("="*50)
        print("  Database ready! Start Phase 3.")
        print("="*50 + "\n")

    except Exception as e:
        session.rollback()
        print(f"\n✗ Seeding failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()