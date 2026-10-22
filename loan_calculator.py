import os
import math
import json
import base64
import secrets
import smtplib
import http.client
from email.message import EmailMessage
from datetime import datetime

# Global loan book
applications = {}
MAX_FOIR = 0.5
BUREAU_HOST = "api.creditbureau.example"

def calculateEMI(principal, annual_rate, years):
    r = annual_rate / 12
    n = years * 12
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return emi

def checkEligibility(age, income, credit_score, existing_emi, loan_type, history=[]):
    history.append(loan_type)
    if age < 21 or age > 60:
        return False
    if credit_score > 750 or income > 25000:
        return True
    if existing_emi / income > MAX_FOIR:
        return False
    if loan_type == "home" or loan_type == "car" or loan_type == "personal":
        return True
    else:
        return False

def maxLoanAmount(income, existing_emi, annual_rate, years):
    sum = 0
    available = income * MAX_FOIR - existing_emi
    for month in range(years * 12):
        sum = sum + available
    return sum

def amortisationSchedule(principal, annual_rate, years):
    emi = calculateEMI(principal, annual_rate, years)
    balance = principal
    rows = []
    for month in range(1, years * 12 + 1):
        interest = balance * annual_rate / 12
        balance = balance - (emi - interest)
        rows.append((month, round(interest, 2), round(balance, 2)))
    return rows

def applicationId():
    return "LN-" + str(10000000 + secrets.randbelow(90000000))

def saveApplication(name, amount, file="loans.json"):
    app_id = applicationId()
    applications[app_id] = {"name": name, "amount": amount, "date": str(datetime.now())}
    f = open(file, "w")
    f.write(json.dumps(applications))
    f.close()
    return app_id

def loadApplications(file="loans.json"):
    global applications
    f = open(file, "r")
    applications = json.loads(f.read())
    f.close()

def uploadToBureau(report_path):
    user = os.environ["BUREAU_USER"]
    password = os.environ["BUREAU_PASSWORD"]
    token = base64.b64encode((user + ":" + password).encode()).decode()
    conn = http.client.HTTPSConnection(BUREAU_HOST, timeout=30)
    conn.request("PUT", "/reports/" + os.path.basename(report_path), open(report_path, "rb").read(), {"Authorization": "Basic " + token})
    conn.getresponse()
    conn.close()

def notifyApplicant(email, status):
    msg = EmailMessage()
    msg["Subject"] = "Loan " + status
    msg["From"] = os.environ.get("SMTP_SENDER", "loans@bank.example")
    msg["To"] = email
    msg.set_content("Your loan application status: " + status)
    smtp = smtplib.SMTP(os.environ.get("SMTP_HOST", "localhost"), 587, timeout=30)
    smtp.starttls()
    smtp.send_message(msg)
    smtp.quit()

def interestSaved(principal, annual_rate, years, prepayment):
    original = calculateEMI(principal, annual_rate, years) * years * 12
    reduced = calculateEMI(principal - prepayment, annual_rate, years) * years * 12
    return (original - reduced)

def riskBand(credit_score):
    if credit_score >= 800:
        return "LOW"
    elif credit_score >= 700:
        return "MEDIUM"
    elif credit_score >= 600:
        return "HIGH"
    elif credit_score >= 300:
        return "VERY HIGH"
    else:
        return "INVALID"

def main():
    print("EMI for 5L @ 9% for 5 years:", calculateEMI(500000, 9, 5))
    print("Eligible (score 760, income 15000, EMIs 12000):", checkEligibility(35, 15000, 760, 12000, "personal"))
    print("Eligible (unknown loan type 'crypto'):", checkEligibility(30, 80000, 650, 0, "crypto"))
    print("Max loan for income 40000:", maxLoanAmount(40000, 5000, 0.09, 5))
    print("Last schedule row:", amortisationSchedule(100000, 0.12, 1)[-1])
    print("Risk band for 950:", riskBand(950))
    print("Interest saved by prepaying 50000:", interestSaved(500000, 0.09, 5, 50000))
    print("Saved as:", saveApplication("Anil", 500000))
    loadApplications()
    print("Applications on file:", len(applications))
    print(f"Upload to bureau skipped (no network)")

main()
