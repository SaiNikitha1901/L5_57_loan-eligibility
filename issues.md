# Lab 5: Static Code Analysis — Issue Log

**Name:** Sai Nikitha Perumalla
**SRN:** PES2UG24AM142
**File:** `loan_calculator.py`

## Results summary

| Tool | Before | After |
|------|--------|-------|
| Pylint | 5.17/10, 43 messages | **10.00/10**, 0 messages |
| Bandit | 8 issues (2 High, 1 Medium, 5 Low) | **No issues identified** |
| Flake8 | 22 issues | **0 issues** (empty report) |

The original reports are in `reports/before/`. The final reports are in `reports/after/` and also at the repo root (`pylint_report.txt`, `bandit_report.txt`, `flake8_report.txt`).

Line numbers below refer to the **original** `loan_calculator.py`.

## Issue table (high and medium severity first)

| # | Issue | Type | Tool / Code | Severity | Line(s) | Description | Fix Approach |
|---|-------|------|-------------|----------|---------|-------------|--------------|
| 1 | Insecure FTP module imported | Security | Bandit B402 | High | 3 | `import ftplib`: FTP sends everything, including the login, in plaintext (CWE-319). | Removed `ftplib` and upload over HTTPS with `http.client.HTTPSConnection`. |
| 2 | Plaintext FTP connection | Security | Bandit B321 | High | 68–70 | `ftplib.FTP(BUREAU_HOST)` + `ftp.login(...)` sends the bureau username and password in clear text. | `upload_to_bureau` now does an HTTPS `PUT` with a Basic-Auth header, so the credentials are protected by TLS. The upload raises `ConnectionError` on a non-2xx response. |
| 3 | Unsafe deserialisation with `marshal` | Security | Bandit B302 | Medium | 4, 57, 64 | `marshal.loads()` on a file is unsafe: `marshal` is undocumented across versions and not meant for untrusted data (CWE-502). | Store the loan book as JSON (`json.dump` / `json.load`) in `loans.json`. JSON is a plain data format. |
| 4 | Mutable default argument | Bug | Pylint W0102 | Medium | 20–21 | `history=[]` is created once, so every call to `checkEligibility` appended to the same shared list. Loan types from earlier applicants leaked into later calls. | Nothing ever read `history`, so the parameter and the `append` were removed. This also cleared R0913/R0917 (too many arguments). |
| 5 | Eligibility shortcut skips FOIR and loan-type checks | Logic bug | Found by running the demo (no tool flags it) | High | 24–25 | `if credit_score > 750 or income > 25000: return True` returned before the FOIR and loan-type checks. The demo approved someone paying 12000 of 15000 income in EMIs (80% FOIR), and also approved a `"crypto"` loan. | Age, supported loan type and FOIR ≤ 50% are now mandatory checks. A strong score **or** a strong income is the final requirement. `income <= 0` returns `False` instead of dividing by zero. |
| 6 | `maxLoanAmount` ignores interest | Logic bug | Pylint W0613 (unused `annual_rate`), W0612, W0622 | Medium | 33–38 | It just added up the monthly headroom for n months (900000), ignoring `annual_rate`. It also shadowed the built-in `sum`. | Return the present value of the affordable EMI: `available * ((1+r)^n − 1) / (r(1+r)^n)` → 722600.60, which gives exactly a 15000 EMI. A non-positive headroom returns 0, and a 0% rate is handled. |
| 7 | Wrong rate unit in EMI demo | Logic bug | Found by running the demo | Medium | 94 | `calculateEMI(500000, 9, 5)` passed 9 (a percentage) where every other call passes a fraction. The EMI came out as 375000 on a 5-lakh loan. | Pass `0.09`. The docstring states that the rate is a fraction. EMI is now 10379.18. A 0% rate no longer divides by zero. |
| 8 | Interest saved counts principal | Logic bug | Found by running the demo | Medium | 76–79 | `original − reduced` includes the 50000 prepaid principal, so it reported 62275 "interest saved". | Subtract the prepayment: `original − reduced − prepayment` → 12275.07. |
| 9 | Impossible credit score accepted | Logic bug | Found by running the demo | Medium | 81–91 | `riskBand(950)` returned `"LOW"`, but credit scores only go from 300 to 900. | Scores outside 300–900 return `"INVALID"`. The range limits are named constants. |
| 10 | Hardcoded password | Security | Bandit B107 | Low | 67 | `password="Bureau#2024"` puts a real credential in source control. | Read `BUREAU_USER` / `BUREAU_PASSWORD` from environment variables. No default is kept in code. |
| 11 | Insecure random for application IDs | Security | Bandit B311 | Low | 5, 51 | `random.randint` is predictable (Mersenne Twister), so application IDs can be guessed. | Use `secrets.randbelow` from the CSPRNG. The `LN-########` format is unchanged. |
| 12 | Shelling out to `mail` | Security | Bandit B404, B603, B607; Pylint W1510 | Low | 6, 74 | `subprocess.run(["mail", ...])` runs a binary found through `PATH` (partial path, CWE-78), with the email passed straight to it and no `check=`. | Send the email with `smtplib.SMTP` + `starttls()` and an `EmailMessage`. No subprocess is used. |
| 13 | Files opened without `with` / encoding | Bug (resource leak) | Pylint R1732, W1514 | Low | 56, 63, 70 | `open()`/`close()` by hand leaks the handle if `write`/`read` raises. The FTP upload never closed its file at all. | Use `with open(..., encoding="utf-8")` everywhere. The HTTPS connection is closed in `finally`. |
| 14 | Global mutable state | Design | Pylint W0603 | Low | 10, 62 | `loadApplications` rebinds the global `applications`, and saving overwrites the file with whatever is in memory. | Removed the global. `load_applications()` returns the dict (or `{}` if the file is missing), and `save_application()` reads, updates and writes the file. |
| 15 | Non-snake_case names | Style | Pylint C0103 | Low | 14–93 | `calculateEMI`, `checkEligibility`, ... don't follow PEP 8 function naming. | Renamed to `calculate_emi`, `check_eligibility`, `max_loan_amount`, and so on. |
| 16 | Missing docstrings | Style | Pylint C0114, C0116 | Low | 1, all functions | No module or function documentation. | Added a module docstring and a docstring for every function that states units and assumptions. |
| 17 | Redundant if/else chains | Style | Pylint R1705, R1703, R1714, C0325 | Low | 28–31, 79, 82–91 | `else` after `return`, a chained `==` instead of `in`, and parentheses after `return`. | `return loan_type in ALLOWED_LOAN_TYPES` (later merged into the eligibility rewrite); flat `if` chains; parentheses removed. |
| 18 | Unused import / empty f-string | Style | Pylint W0611, W1309; Flake8 F401, F541 | Low | 2, 104 | `import math` is never used; `f"Upload ... skipped"` has no placeholders. | Removed the import; changed to a plain string. |
| 19 | Module-level `main()` call | Design | (review) | Low | 106 | `main()` runs, and writes `loans.bin`, whenever the module is imported. | Wrapped it in `if __name__ == "__main__":`. |
| 20 | Missing blank lines | Style | Flake8 E302, E305 | Low | 14–106 | One blank line between top-level functions instead of two. | Added two blank lines around every top-level definition and the `__main__` guard. |
| 21 | Lines too long | Style | Flake8 E501; Pylint C0301 | Low | 20, 55, 70, 78, 95, 96, 100 | Lines longer than 79 characters (up to 113). | Wrapped the expressions, split the record dict over several lines, and pulled sub-expressions into local variables (`growth`, `remaining`, `smtp_host`). |

## Demo output: before vs after

| Demo line | Before | After |
|-----------|--------|-------|
| EMI for 5L @ 9% for 5 years | 375000.000000001 | 10379.18 |
| Eligible (score 760, income 15000, EMIs 12000) | True | False (80% FOIR) |
| Eligible (unknown loan type 'crypto') | True | False |
| Max loan for income 40000 | 900000.0 | 722600.6 |
| Last schedule row | (12, 87.97, 0.0) | (12, 87.97, 0.0) |
| Risk band for 950 | LOW | INVALID |
| Interest saved by prepaying 50000 | 62275.07 | 12275.07 |

## Commits

| Commit | What |
|--------|------|
| Add baseline reports | `reports/before/*` |
| **Fix all Bandit security issues** | Issues 1, 2, 3, 10, 11, 12 |
| **Fix all Pylint issues** | Issues 4, 6, 13–19 |
| Fix logic bugs visible in the demo output | Issues 5, 7, 8, 9 |
| **Fix all Flake8 (PEP 8) issues** | Issues 20, 21 |
| Add after reports, issue log and reflection | `reports/after/*`, this file, `reflection.md` |
