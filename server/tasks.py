"""
Task definitions for CodeReviewEnv.
Each task has:
  - code snippet with real bugs/issues
  - expected findings (keywords the agent must identify)
  - a grader function returning score 0.0–1.0
  - difficulty: easy / medium / hard
"""
from typing import List, Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
# TASK 1 — EASY: Simple function review
# A basic Python utility function with 3 clear bugs
# ─────────────────────────────────────────────────────────────────────────────

TASK_EASY = {
    "name": "simple-function-review",
    "difficulty": "easy",
    "language": "python",
    "task_description": (
        "Review this Python function that calculates the average of a list of numbers "
        "and returns the top N values. Find all bugs and style issues."
    ),
    "code": """\
def calculate_stats(numbers, n=0):
    \"\"\"Calculate average and return top N numbers from list.\"\"\"
    total = 0
    for num in numbers:
        total = total + num
    
    average = total / len(numbers)   # Bug 1: ZeroDivisionError if numbers is empty
    
    sorted_nums = numbers.sort()     # Bug 2: list.sort() returns None, not sorted list
    top_n = sorted_nums[:n]          # Bug 3: will crash because sorted_nums is None
    
    result = {
        "average": average,
        "top_n": top_n,
        "count": len(numbers)
    }
    return result                    # Style: no type hints, no input validation
""",
    "expected_keywords": [
        "zerodivision", "zero division", "empty list", "division by zero",
        "sort() returns none", "sort returns none", "in-place", "inplace", "returns none",
        "none", "sorted(", "type hint", "input validation", "n=0", "top_n", "crash"
    ],
    "expected_severity": ["medium", "high"],
    "max_steps": 4,
    "issues_count": 3,
}

# ─────────────────────────────────────────────────────────────────────────────
# TASK 2 — MEDIUM: Class with subtle logic bugs
# A BankAccount class with off-by-one, state, and concurrency logic issues
# ─────────────────────────────────────────────────────────────────────────────

TASK_MEDIUM = {
    "name": "class-logic-review",
    "difficulty": "medium",
    "language": "python",
    "task_description": (
        "Review this BankAccount class used in a production banking system. "
        "Find all logic bugs, edge cases, and design flaws."
    ),
    "code": """\
class BankAccount:
    MIN_BALANCE = 0
    
    def __init__(self, owner, initial_balance=0):
        self.owner = owner
        self.balance = initial_balance
        self.transaction_history = []
    
    def deposit(self, amount):
        if amount < 0:                    # Bug 1: should be <= 0 (zero deposit allowed)
            raise ValueError("Amount must be positive")
        self.balance += amount
        self.transaction_history.append(("deposit", amount))
    
    def withdraw(self, amount):
        if amount < 0:
            raise ValueError("Amount must be positive")
        if self.balance - amount < self.MIN_BALANCE:
            raise ValueError("Insufficient funds")
        self.balance -= amount            # Bug 2: not atomic — race condition in concurrent use
        self.transaction_history.append(("withdraw", amount))
        return True
    
    def get_statement(self):
        statement = ""
        for i in range(len(self.transaction_history)):
            t = self.transaction_history[i]
            statement += f"\\n{i}: {t[0]} ${t[1]}"
        return statement                  # Bug 3: index starts at 0 but displayed as transaction number
    
    def transfer(self, other_account, amount):
        self.withdraw(amount)
        other_account.deposit(amount)    # Bug 4: if deposit fails, money is lost (no rollback)
    
    def is_overdrawn(self):
        return self.balance < 0          # Bug 5: inconsistent with MIN_BALANCE = 0 logic
""",
    "expected_keywords": [
        "race condition", "atomic", "concurrency", "thread",
        "rollback", "transfer", "atomicity", "deposit fail",
        "zero deposit", "zero amount", "amount <= 0",
        "transaction number", "index", "off by one",
        "overdrawn", "min_balance", "inconsistent",
        "no rollback", "money lost"
    ],
    "expected_severity": ["high", "critical"],
    "max_steps": 5,
    "issues_count": 5,
}

# ─────────────────────────────────────────────────────────────────────────────
# TASK 3 — HARD: Security-critical authentication code
# SQL injection, timing attack, broken auth, insecure token storage
# ─────────────────────────────────────────────────────────────────────────────

TASK_HARD = {
    "name": "security-code-review",
    "difficulty": "hard",
    "language": "python",
    "task_description": (
        "Review this authentication module from a web application. "
        "This is security-critical code. Identify all security vulnerabilities, "
        "attack vectors, and CWE references where applicable."
    ),
    "code": """\
import sqlite3
import hashlib
import os
import time

SECRET_KEY = "hardcoded_secret_key_123"   # Vuln 1: CWE-798 hardcoded credentials

def authenticate_user(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # Vuln 2: CWE-89 SQL Injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchone()
    
    if not user:
        return False
    
    stored_hash = user[2]
    # Vuln 3: CWE-327 MD5 is cryptographically broken
    input_hash = hashlib.md5(password.encode()).hexdigest()
    
    # Vuln 4: CWE-208 Timing attack — direct string comparison
    if stored_hash == input_hash:
        token = generate_token(username)
        return token
    return False

def generate_token(username):
    # Vuln 5: CWE-338 Predictable token — time-based, not cryptographically secure
    token = hashlib.md5(f"{username}{time.time()}".encode()).hexdigest()
    
    # Vuln 6: CWE-312 Token stored in plaintext log file
    with open("tokens.log", "a") as f:
        f.write(f"{username}:{token}\\n")
    
    return token

def reset_password(username, new_password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # Vuln 7: No rate limiting, no verification — anyone can reset anyone's password
    # Vuln 8: CWE-89 SQL Injection again
    query = f"UPDATE users SET password='{new_password}' WHERE username='{username}'"
    cursor.execute(query)
    conn.commit()
    # Vuln 9: Password stored in plaintext, not hashed
""",
    "expected_keywords": [
        "sql injection", "sql", "injection", "cwe-89",
        "md5", "weak hash", "broken", "cwe-327",
        "hardcoded", "hardcoded secret", "cwe-798",
        "timing attack", "hmac", "secrets.compare_digest", "cwe-208",
        "predictable token", "os.urandom", "secrets.token", "cwe-338",
        "plaintext", "log", "cwe-312",
        "rate limit", "no verification", "password reset",
        "no hashing", "plaintext password"
    ],
    "expected_severity": ["critical"],
    "max_steps": 6,
    "issues_count": 9,
}

ALL_TASKS = {
    "simple-function-review": TASK_EASY,
    "class-logic-review": TASK_MEDIUM,
    "security-code-review": TASK_HARD,
}

# ─────────────────────────────────────────────────────────────────────────────
# GRADERS — deterministic, reproducible, scores 0.0–1.0
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    return text.lower().replace("-", " ").replace("_", " ")


def _count_keyword_matches(findings_text: str, keywords: List[str]) -> int:
    normalized = _normalize_text(findings_text)
    matched = set()
    for kw in keywords:
        if _normalize_text(kw) in normalized:
            matched.add(kw)
    return len(matched)


def grade_easy(action: Dict[str, Any], task: Dict[str, Any] = TASK_EASY) -> float:
    """
    Grader for easy task. Score breakdown:
    - 0.6: finding all 3 bugs (0.2 each)
    - 0.2: correct severity (medium or high)
    - 0.2: has recommendation
    """
    findings_text = " ".join(action.get("findings", [])) + " " + action.get("recommendation", "")
    keywords = task["expected_keywords"]
    matches = _count_keyword_matches(findings_text, keywords)

    # Partial credit: how many of the 3 bug categories covered
    bug_categories = [
        ["zerodivision", "zero division", "empty list", "division by zero"],
        ["sort() returns none", "sort returns none", "returns none", "in-place", "inplace", "sorted("],
        ["crash", "nonetype", "sorted_nums", "subscript", "attributeerror", "none[:n]"],
    ]
    bugs_found = 0
    normalized_findings = _normalize_text(findings_text)
    for category in bug_categories:
        if any(_normalize_text(kw) in normalized_findings for kw in category):
            bugs_found += 1

    bug_score = bugs_found / len(bug_categories) * 0.6
    severity = action.get("severity", "").lower()
    severity_score = 0.2 if severity in task["expected_severity"] else 0.1
    rec_score = 0.2 if len(action.get("recommendation", "")) > 20 else 0.0

    total = round(min(bug_score + severity_score + rec_score, 1.0), 4)
    return total


def grade_medium(action: Dict[str, Any], task: Dict[str, Any] = TASK_MEDIUM) -> float:
    """
    Grader for medium task. Score breakdown:
    - 0.6: finding bugs (0.12 per bug category, 5 categories)
    - 0.2: correct severity (high or critical)
    - 0.2: mentions concurrency/atomicity (the key insight)
    """
    findings_text = " ".join(action.get("findings", [])) + " " + action.get("recommendation", "")
    normalized_findings = _normalize_text(findings_text)

    bug_categories = [
        ["zero deposit", "zero amount", "amount <= 0", "allow zero"],
        ["race condition", "concurrent", "thread", "atomic", "not atomic"],
        ["index", "off by one", "transaction number", "starts at 0"],
        ["rollback", "no rollback", "transfer", "money lost", "deposit fail"],
        ["overdrawn", "min_balance", "inconsistent", "balance < 0"],
    ]
    bugs_found = sum(
        1 for category in bug_categories
        if any(_normalize_text(kw) in normalized_findings for kw in category)
    )
    bug_score = bugs_found / len(bug_categories) * 0.6

    severity = action.get("severity", "").lower()
    severity_score = 0.2 if severity in task["expected_severity"] else 0.05

    concurrency_score = 0.2 if any(
        kw in normalized_findings for kw in ["race condition", "atomic", "thread", "concurrent"]
    ) else 0.0

    total = round(min(bug_score + severity_score + concurrency_score, 1.0), 4)
    return total


def grade_hard(action: Dict[str, Any], task: Dict[str, Any] = TASK_HARD) -> float:
    """
    Grader for hard task. Score breakdown:
    - 0.7: identifying security vulnerabilities (0.07-0.1 each, 9 vulns)
    - 0.2: severity = critical
    - 0.1: mentions CWE numbers or specific attack names
    """
    findings_text = " ".join(action.get("findings", [])) + " " + action.get("recommendation", "")
    normalized_findings = _normalize_text(findings_text)

    vuln_categories = [
        ["sql injection", "injection", "cwe 89", "parameterized"],
        ["md5", "weak hash", "broken hash", "bcrypt", "sha256", "cwe 327"],
        ["hardcoded", "hardcoded secret", "hardcoded credential", "cwe 798"],
        ["timing attack", "compare digest", "constant time", "cwe 208"],
        ["predictable token", "os urandom", "secrets token", "cwe 338"],
        ["plaintext log", "token log", "cwe 312", "sensitive data"],
        ["rate limit", "no rate", "brute force"],
        ["no verification", "password reset", "identity verification"],
        ["plaintext password", "password not hashed", "unhashed"],
    ]
    vulns_found = sum(
        1 for category in vuln_categories
        if any(_normalize_text(kw) in normalized_findings for kw in category)
    )
    vuln_score = vulns_found / len(vuln_categories) * 0.7

    severity = action.get("severity", "").lower()
    severity_score = 0.2 if severity == "critical" else 0.0

    cwe_score = 0.1 if any(
        kw in normalized_findings for kw in ["cwe", "injection", "owasp", "vulnerability"]
    ) else 0.0

    total = round(min(vuln_score + severity_score + cwe_score, 1.0), 4)
    return total


GRADERS = {
    "simple-function-review": grade_easy,
    "class-logic-review": grade_medium,
    "security-code-review": grade_hard,
}
