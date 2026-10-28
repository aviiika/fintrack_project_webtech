"""Seed demo user, sample txns (HDFC+SBI+ICICI), budgets, holdings and loans.

Also trains the initial ML categoriser: the seeded corpus is deliberately sized
above settings.ml_min_training_samples so a fresh install has a working model
rather than falling back to keyword rules until the user imports enough data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from app.database.session import SessionLocal, init_db
from app.models.budget import Budget
from app.models.liability import Liability
from app.models.stock_holding import StockHolding
from app.models.user import User
from app.services.csv_parser import parse_csv_bytes
from app.services.loan_service import calculate_emi
from app.services.networth_service import snapshot_now
from app.services.transaction_service import import_transactions
from app.utils.logging import configure_logging, get_logger
from app.utils.security import hash_password

logger = get_logger(__name__)

HDFC_CSV = b"""Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance
01/05/25,Zomato Food Order,,01/05/25,450.00,,48500.00
02/05/25,Amazon Shopping,,02/05/25,2399.00,,46101.00
03/05/25,Salary May 2025,,03/05/25,,52000.00,98101.00
04/05/25,House Rent Payment,,04/05/25,12000.00,,86101.00
05/05/25,JIO Prepaid Recharge,,05/05/25,299.00,,85802.00
06/05/25,Netflix Subscription,,06/05/25,649.00,,85153.00
07/05/25,Ola Cab Booking,,07/05/25,180.00,,84973.00
08/05/25,Swiggy Dinner,,08/05/25,680.00,,84293.00
09/05/25,BigBasket Groceries,,09/05/25,1850.00,,82443.00
10/05/25,Uber Ride,,10/05/25,220.00,,82223.00
11/05/25,Apollo Pharmacy,,11/05/25,540.00,,81683.00
12/05/25,Groww SIP Investment,,12/05/25,5000.00,,76683.00
13/05/25,IRCTC Train Ticket,,13/05/25,1240.00,,75443.00
14/05/25,Reliance Fresh Grocery,,14/05/25,920.00,,74523.00
15/05/25,Udemy Course Purchase,,15/05/25,499.00,,74024.00
16/05/25,Swiggy Lunch,,16/05/25,320.00,,73704.00
17/05/25,Petrol Pump Payment,,17/05/25,1500.00,,72204.00
18/05/25,Zomato Breakfast,,18/05/25,210.00,,71994.00
19/05/25,BESCOM Electricity Bill,,19/05/25,1200.00,,70794.00
20/05/25,Freelance Payment Received,,20/05/25,,8000.00,78794.00
21/05/25,Myntra Clothing,,21/05/25,1799.00,,76995.00
22/05/25,Rapido Bike Taxi,,22/05/25,95.00,,76900.00
23/05/25,1mg Medicine Order,,23/05/25,680.00,,76220.00
24/05/25,Spotify Premium,,24/05/25,119.00,,76101.00
25/05/25,Blinkit Groceries,,25/05/25,760.00,,75341.00
26/05/25,Restaurant Dinner,,26/05/25,1200.00,,74141.00
27/05/25,Airtel Broadband,,27/05/25,799.00,,73342.00
28/05/25,Amazon Prime Annual,,28/05/25,1499.00,,71843.00
29/05/25,Zerodha Mutual Fund,,29/05/25,3000.00,,68843.00
30/05/25,BookMyShow Movie,,30/05/25,560.00,,68283.00
31/05/25,Salary Bonus,,31/05/25,,5000.00,73283.00
"""

SBI_CSV = b"""Txn Date,Description,Ref No./Cheque No.,Debit,Credit,Balance
01 May 2025,UPI-Swiggy Technologies,123456789,340.00,,22000.00
03 May 2025,SALARY CREDIT MAY25,,,25000.00,47000.00
05 May 2025,UPI-Zomato Online,234567890,550.00,,46450.00
07 May 2025,NEFT-Rent May 2025,345678901,8000.00,,38450.00
09 May 2025,UPI-Ola Cabs India,456789012,250.00,,38200.00
10 May 2025,UPI-BigBasket,567890123,1200.00,,37000.00
12 May 2025,LIC Premium Payment,678901234,2500.00,,34500.00
14 May 2025,UPI-Paytm Recharge,789012345,299.00,,34201.00
16 May 2025,UPI-Uber India,890123456,180.00,,34021.00
18 May 2025,ATM Withdrawal,901234567,2000.00,,32021.00
20 May 2025,UPI-Zepto Groceries,012345678,680.00,,31341.00
22 May 2025,FREELANCE PAYMENT IMPS,112345678,,12000.00,43341.00
24 May 2025,UPI-Udemy Course,223456789,499.00,,42842.00
26 May 2025,UPI-PVR Cinemas,334567890,480.00,,42362.00
28 May 2025,NEFT-EMI HDFC Loan,445678901,4500.00,,37862.00
30 May 2025,UPI-Apollo Pharmacy,556789012,320.00,,37542.00
"""

# A third bank, in a third date/column format -- demonstrates the parser registry
# handling ICICI alongside HDFC and SBI, and pushes the seeded corpus past the
# 50-sample floor so an initial ML model actually trains on a fresh install.
ICICI_CSV = b"""Transaction Date,Transaction Remarks,Withdrawal Amount (INR ),Deposit Amount (INR ),Balance (INR )
02/05/2025,POS/Reliance Fresh Grocery,1340.00,,64200.00
03/05/2025,UPI/Dominos Pizza Order,720.00,,63480.00
04/05/2025,NEFT/Consulting Income,,18000.00,81480.00
05/05/2025,POS/Croma Electronics,8499.00,,72981.00
06/05/2025,UPI/Rapido Bike Taxi,95.00,,72886.00
08/05/2025,ACH/BESCOM Electricity Bill,1870.00,,71016.00
09/05/2025,UPI/Blinkit Groceries,640.00,,70376.00
11/05/2025,UPI/Spotify Premium,119.00,,70257.00
12/05/2025,POS/Indian Oil Petrol Pump,2200.00,,68057.00
13/05/2025,UPI/Cult Fit Membership,1499.00,,66558.00
15/05/2025,NEFT/SIP Axis Mutual Fund,6000.00,,60558.00
16/05/2025,UPI/Practo Doctor Consult,600.00,,59958.00
17/05/2025,POS/Lifestyle Clothing,3250.00,,56708.00
19/05/2025,UPI/Airtel Postpaid Bill,799.00,,55909.00
20/05/2025,UPI/Starbucks Coffee,430.00,,55479.00
21/05/2025,IMPS/Rent Top Up,4000.00,,51479.00
23/05/2025,UPI/Coursera Subscription,3999.00,,47480.00
24/05/2025,POS/MedPlus Pharmacy,415.00,,47065.00
25/05/2025,UPI/BookMyShow Tickets,700.00,,46365.00
27/05/2025,UPI/Metro Card Recharge,500.00,,45865.00
29/05/2025,NEFT/Car Loan EMI,12500.00,,33365.00
31/05/2025,UPI/Amazon Fresh Groceries,1120.00,,32245.00
31/05/2025,NEFT/Annual Performance Bonus,,30000.00,62245.00
"""

# Buy prices sit near stock_service.REFERENCE_PRICES so the demo portfolio shows
# a realistic mix of modest gains and losses rather than implausible extremes.
HOLDINGS = [("RELIANCE", 10, 2740.0), ("TCS", 5, 4250.0),
            ("INFY", 15, 1690.0), ("HDFCBANK", 8, 1745.0)]

# Sized for the demo persona (a student / early-career user): an education loan
# part-way through repayment plus a small consumer loan nearly paid off. The
# resulting net worth is mildly negative, which is the honest picture for
# someone still repaying an education loan -- and a better teaching artifact
# than data cooked to show a flattering number.
LOANS = [("Education Loan", "education_loan", 350_000, 9.0, 84, "2022-07-01"),
         ("Two-Wheeler Loan", "car_loan", 95_000, 11.5, 36, "2024-03-01")]

BUDGETS = [("Food & Dining",9000,"2025-05"),("Groceries",7000,"2025-05"),
           ("Transport",5000,"2025-05"),("Entertainment",1900,"2025-05"),
           ("Shopping",6000,"2025-05"),("Health",3000,"2025-05"),
           ("Utilities",3500,"2025-05")]

def seed():
    configure_logging()
    init_db()
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == "demo@fintrack.app")):
            logger.info("Demo user exists — skipping seed."); return

        user = User(email="demo@fintrack.app", full_name="Demo User",
                    hashed_password=hash_password("demo12345"))
        db.add(user); db.flush()

        for bank, csv, fname in [("hdfc", HDFC_CSV, "sample_hdfc.csv"),
                                  ("sbi", SBI_CSV, "sample_sbi.csv"),
                                  ("icici", ICICI_CSV, "sample_icici.csv")]:
            records = parse_csv_bytes(csv, bank, fname)
            import_transactions(db, user.id, records, fname, bank)

        for cat, lim, m in BUDGETS:
            db.add(Budget(category=cat, monthly_limit=lim, month=m, owner_id=user.id))
        db.commit()

        # Week 2/3 demo data: a few holdings and a loan, so the Portfolio, Net Worth
        # and Loans pages have something to show on a fresh install.
        for symbol, qty, avg in HOLDINGS:
            db.add(StockHolding(symbol=symbol, exchange="NSE", quantity=qty,
                                 avg_buy_price=avg, owner_id=user.id))
        for name, ltype, principal, rate, tenure, start in LOANS:
            db.add(Liability(name=name, liability_type=ltype, principal_amount=principal,
                             interest_rate_annual=rate, tenure_months=tenure,
                             emi_amount=calculate_emi(principal, rate, tenure),
                             start_date=start, owner_id=user.id))
        db.commit()
        snapshot_now(db, user.id)
        logger.info("Seed complete. Login: demo@fintrack.app / demo12345")

        # Train the initial ML model from the seed data
        logger.info("Training initial ML categoriser from seed data...")
        from app.ml.training.train_categoriser import train
        result = train()
        logger.info("Training result: %s", result.get("message"))

        # The rows above were imported before any model existed, so they're all
        # tagged 'rules_no_model'. Now that a model is trained FROM them, give it
        # a say on the ones no human has corrected -- otherwise a fresh install
        # shows a trained model that has visibly categorised nothing.
        if result.get("status") == "trained":
            from app.ml.inference.backfill import backfill_predictions
            bf = backfill_predictions(db)
            logger.info("Backfill: %s of %s rows claimed by ML (%s re-categorised)",
                        bf["ml_assigned"], bf["examined"], bf["changed"])
    finally:
        db.close()

if __name__ == "__main__":
    seed()
