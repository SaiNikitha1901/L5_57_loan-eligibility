# Lab 5: Reflection

**Name:** Sai Nikitha Perumalla
**SRN:** PES2UG24AM142

### 1. Which issues were the easiest to fix, and which were the hardest? Why?

**Easiest:** the Flake8 style issues (E302 blank lines, E501 long lines, F401 unused import, F541 empty f-string) and most Pylint convention messages (snake_case names, docstrings, `else` after `return`). Each message gives an exact line and an unambiguous fix, and none of them changes behaviour.

**Hardest:** the Bandit findings and the logic bugs, because the tool points at a problem but does not tell you what to replace it with.
- **B402/B321 (FTP):** removing `ftplib` is easy. Deciding what replaces it is the real work. I moved the upload to HTTPS (`http.client.HTTPSConnection`) with the credentials sent over TLS. I also had to move the hardcoded password (B107) into environment variables.
- **B302 (marshal):** switching to JSON meant changing the file format (`loans.bin` → `loans.json`). Removing the global `applications` (W0603) at the same time changed how saving works: it now reads, updates and writes the file.
- **The eligibility bug** was the hardest of all, because no tool reported it. `checkEligibility` returned `True` as soon as the credit score was above 750 *or* income was above 25000, before checking FOIR or the loan type. I found it by reading the demo output: someone with 80% of income already going to EMIs, and a "crypto" loan, were both approved.

### 2. Did the static analysis tools report any false positives? If so, describe one example.

Yes, mostly the Low-severity Bandit findings, which are "audit this" hints rather than confirmed vulnerabilities:
- **B603 (`subprocess` without `shell=True`):** the call used a list of arguments, not a shell string, so there was no shell injection. Bandit flags every `subprocess` call so that a person checks it. (B607 for the partial path `mail` was a real but minor issue, and I replaced the call with `smtplib` anyway.)
- **B404 (importing `subprocess`):** this fires on the import alone. Importing a module is not a vulnerability by itself.
- **B311 (`random`):** this is only a real problem when the value has to be unpredictable. Here it was borderline rather than a false positive, because guessable application IDs could let someone enumerate other customers' records, so I switched to `secrets`.

On the Pylint side, **R0913 (too many arguments, 6/5)** on `checkEligibility` is more of a design opinion than a defect: five or six inputs is reasonable for an eligibility rule. It went away because the sixth argument (`history`) was dead code.

The opposite case matters just as much: the tools gave **false negatives** on all four logic bugs (wrong rate unit, eligibility shortcut, interest saved including principal, 950 accepted as a credit score). Pylint gave the fixed file 10/10 *before* I fixed those bugs. A perfect score does not mean the program is correct.

### 3. How would you integrate static analysis tools into your actual software development workflow?

- **Locally, before every commit:** a `pre-commit` hook that runs `flake8`, `pylint` and `bandit` on the changed files. I would also run them in the editor (VS Code Pylint/Flake8 extensions) so issues show up while I type.
- **In CI (GitHub Actions) on every push and pull request:** a job that installs the tools and runs all three. It would fail the build on any Bandit High/Medium finding (`bandit -ll`), on any Flake8 error, or when Pylint drops below a threshold (`pylint --fail-under=9.5`). Reports would be saved as build artifacts so reviewers can see them.
- **Shared configuration in the repo** (`.pylintrc` / `pyproject.toml`, `.flake8`, Bandit config). Everyone then runs the same rules, and a project-wide rule is turned off in one place rather than with scattered `# noqa` / `# nosec` comments. Any suppression gets a comment explaining why.
- **Together with tests:** static analysis would not have caught the four logic bugs here, so unit tests (for example `check_eligibility(35, 15000, 760, 12000, "personal") is False`) run in the same pipeline.

### 4. What tangible improvements did you observe in the code quality, readability, or potential robustness after applying the fixes?

- **Security:** Bandit went from 8 issues (2 High, 1 Medium) to none. There is no plaintext FTP, no password in the source, no unsafe deserialisation, no predictable IDs and no shell-out.
- **Correctness:** the demo now prints sensible numbers. The EMI is 10379.18 instead of 375000. Applicants who are over-leveraged or ask for an unsupported loan type are rejected. The maximum loan accounts for interest (722600.60 instead of 900000). Interest saved no longer counts the prepaid principal (12275.07 instead of 62275.07). A score of 950 is `INVALID`.
- **Robustness:** every file is opened with `with` and an explicit encoding, so handles are never leaked. Edge cases that used to crash or give wrong answers are handled: a 0% rate, zero income, no FOIR headroom, and a missing loan-book file. The mutable default that leaked state between calls is gone.
- **Readability and maintainability:** Pylint went from 5.17 to 10.00/10 and Flake8 is clean. The code has snake_case names, docstrings that state units ("annual_rate is a fraction"), and named constants (`MAX_FOIR`, `MIN_CREDIT_SCORE`, `ALLOWED_LOAN_TYPES`) instead of magic numbers. There is no global state, and the `__main__` guard means the module can be imported and tested without running the demo.
