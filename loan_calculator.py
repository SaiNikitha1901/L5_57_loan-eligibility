"""Loan eligibility and EMI calculator.

Calculates EMIs, checks loan eligibility, works out the maximum loan a
customer can get, builds amortisation schedules, assigns risk bands from
credit scores, estimates the interest saved by prepaying and stores
application records in a JSON file.
"""
import base64
import http.client
import json
import os
import secrets
import smtplib
from datetime import datetime
from email.message import EmailMessage

MAX_FOIR = 0.5
MIN_AGE = 21
MAX_AGE = 60
STRONG_CREDIT_SCORE = 750
STRONG_INCOME = 25000
MIN_CREDIT_SCORE = 300
MAX_CREDIT_SCORE = 900
ALLOWED_LOAN_TYPES = ("home", "car", "personal")
BUREAU_HOST = "api.creditbureau.example"
DEFAULT_STORE = "loans.json"

def calculate_emi(principal, annual_rate, years):
    """Return the monthly EMI for a loan; annual_rate is a fraction (0.09 = 9%)."""
    rate = annual_rate / 12
    months = years * 12
    if rate == 0:
        return principal / months
    return principal * rate * (1 + rate) ** months / ((1 + rate) ** months - 1)

def check_eligibility(age, income, credit_score, existing_emi, loan_type):
    """Return True if the applicant qualifies for the requested loan type.

    Every applicant must be of age, ask for a supported loan type and keep
    total EMIs within MAX_FOIR of income; on top of that they need either a
    strong credit score or a strong income.
    """
    if not MIN_AGE <= age <= MAX_AGE:
        return False
    if loan_type not in ALLOWED_LOAN_TYPES or income <= 0:
        return False
    if existing_emi / income > MAX_FOIR:
        return False
    return credit_score > STRONG_CREDIT_SCORE or income > STRONG_INCOME

def max_loan_amount(income, existing_emi, annual_rate, years):
    """Return the largest principal whose EMI fits in the applicant's FOIR headroom."""
    available = income * MAX_FOIR - existing_emi
    if available <= 0:
        return 0.0
    rate = annual_rate / 12
    months = years * 12
    if rate == 0:
        return available * months
    return available * ((1 + rate) ** months - 1) / (rate * (1 + rate) ** months)

def amortisation_schedule(principal, annual_rate, years):
    """Return (month, interest, closing balance) rows for the loan's full tenure."""
    emi = calculate_emi(principal, annual_rate, years)
    balance = principal
    rows = []
    for month in range(1, years * 12 + 1):
        interest = balance * annual_rate / 12
        balance = balance - (emi - interest)
        rows.append((month, round(interest, 2), max(0.0, round(balance, 2))))
    return rows

def application_id():
    """Return a new, unpredictable application ID such as 'LN-48213907'."""
    return "LN-" + str(10000000 + secrets.randbelow(90000000))

def load_applications(file=DEFAULT_STORE):
    """Return the saved applications, or an empty dict if none are on file."""
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as store:
        return json.load(store)

def save_application(name, amount, file=DEFAULT_STORE):
    """Add an application to the loan book on disk and return its ID."""
    applications = load_applications(file)
    app_id = application_id()
    applications[app_id] = {"name": name, "amount": amount, "date": str(datetime.now())}
    with open(file, "w", encoding="utf-8") as store:
        json.dump(applications, store, indent=2)
    return app_id

def upload_to_bureau(report_path):
    """Upload a report to the credit bureau over HTTPS.

    Credentials come from the BUREAU_USER and BUREAU_PASSWORD environment variables.
    """
    user = os.environ["BUREAU_USER"]
    password = os.environ["BUREAU_PASSWORD"]
    token = base64.b64encode((user + ":" + password).encode()).decode()
    with open(report_path, "rb") as report:
        body = report.read()
    conn = http.client.HTTPSConnection(BUREAU_HOST, timeout=30)
    try:
        conn.request("PUT", "/reports/" + os.path.basename(report_path), body,
                     {"Authorization": "Basic " + token})
        response = conn.getresponse()
        if response.status >= 300:
            raise ConnectionError(f"Bureau upload failed: {response.status} {response.reason}")
    finally:
        conn.close()

def notify_applicant(email, status):
    """Email the applicant their loan status through the SMTP_HOST relay."""
    msg = EmailMessage()
    msg["Subject"] = "Loan " + status
    msg["From"] = os.environ.get("SMTP_SENDER", "loans@bank.example")
    msg["To"] = email
    msg.set_content("Your loan application status: " + status)
    with smtplib.SMTP(os.environ.get("SMTP_HOST", "localhost"), 587, timeout=30) as smtp:
        smtp.starttls()
        smtp.send_message(msg)

def interest_saved(principal, annual_rate, years, prepayment):
    """Return the interest saved by prepaying part of the principal up front.

    The prepayment itself is principal, not interest, so it is excluded.
    """
    original = calculate_emi(principal, annual_rate, years) * years * 12
    reduced = calculate_emi(principal - prepayment, annual_rate, years) * years * 12
    return original - reduced - prepayment

def risk_band(credit_score):
    """Map a credit score (valid range 300-900) to a risk band."""
    if not MIN_CREDIT_SCORE <= credit_score <= MAX_CREDIT_SCORE:
        return "INVALID"
    if credit_score >= 800:
        return "LOW"
    if credit_score >= 700:
        return "MEDIUM"
    if credit_score >= 600:
        return "HIGH"
    return "VERY HIGH"

def main():
    """Run a short demo of the calculator."""
    print("EMI for 5L @ 9% for 5 years:", round(calculate_emi(500000, 0.09, 5), 2))
    print("Eligible (score 760, income 15000, EMIs 12000):",
          check_eligibility(35, 15000, 760, 12000, "personal"))
    print("Eligible (unknown loan type 'crypto'):", check_eligibility(30, 80000, 650, 0, "crypto"))
    print("Max loan for income 40000:", round(max_loan_amount(40000, 5000, 0.09, 5), 2))
    print("Last schedule row:", amortisation_schedule(100000, 0.12, 1)[-1])
    print("Risk band for 950:", risk_band(950))
    print("Interest saved by prepaying 50000:", round(interest_saved(500000, 0.09, 5, 50000), 2))
    print("Saved as:", save_application("Anil", 500000))
    print("Applications on file:", len(load_applications()))
    print("Upload to bureau skipped (no network)")

if __name__ == "__main__":
    main()
