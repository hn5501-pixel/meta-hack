---
title: Code Review Env
emoji: 👾
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---
# CodeReviewEnv 🔍

**OpenEnv Environment | Meta PyTorch OpenEnv Hackathon x Scaler**

An AI agent acts as a **software code reviewer**. Given real code snippets containing bugs, security vulnerabilities, and style violations, the agent must identify and report all issues across three difficulty levels.

This is a genuinely real-world task — code review is something senior engineers do daily, and automating it with RL agents has immediate industry value.

---

## Environment Description

| Property | Value |
|---|---|
| Domain | Software Engineering |
| Real-world task | Yes — code review is done millions of times per day |
| Tasks | 3 (easy → medium → hard) |
| Reward range | 0.0 – 1.0 |
| Episode length | 4–6 steps |
| API | REST (FastAPI) |

---

## Observation Space

```python
class CodeReviewObservation(BaseModel):
    code: str                      # Code snippet to review
    language: str                  # "python"
    task_description: str          # What the code is supposed to do
    step_number: int               # Current step in episode
    previous_findings: List[str]   # Findings already reported
    hint: Optional[str]            # Partial progress hint (after step 2)
```

## Action Space

```python
class CodeReviewAction(BaseModel):
    findings: List[str]            # Issues found in this step
    severity: str                  # "low" | "medium" | "high" | "critical"
    line_references: List[int]     # Line numbers with issues
    recommendation: str            # Overall fix recommendation
```

---

## Tasks

### Task 1 — `simple-function-review` 🟢 Easy (4 steps)

**Code:** A Python utility function with 3 clear bugs.

**Issues to find:**
1. `ZeroDivisionError` — no empty list guard before dividing by `len(numbers)`
2. `list.sort()` returns `None` — the sorted result is never captured
3. Cascade crash — `sorted_nums[:n]` fails because `sorted_nums` is `None`

**Grading:** 0.2 per bug found + 0.2 for correct severity + 0.2 for recommendation

---

### Task 2 — `class-logic-review` 🟡 Medium (5 steps)

**Code:** A `BankAccount` class used in a banking system with 5 logic flaws.

**Issues to find:**
1. `amount < 0` should be `amount <= 0` — zero deposits accepted incorrectly
2. Non-atomic balance update — race condition under concurrent access
3. Transaction history index starts at 0, displayed as transaction ID
4. `transfer()` has no rollback — money disappears if `deposit()` fails
5. `is_overdrawn()` is inconsistent with `MIN_BALANCE = 0`

**Grading:** 0.12 per bug (×5) + 0.2 for high/critical severity + 0.2 for concurrency insight

---

### Task 3 — `security-code-review` 🔴 Hard (6 steps)

**Code:** An authentication module with 9 security vulnerabilities.

**Vulnerabilities:**
1. **CWE-798** — Hardcoded `SECRET_KEY` in source code
2. **CWE-89** — SQL Injection in `authenticate_user()` via f-string query
3. **CWE-327** — MD5 used for password hashing (cryptographically broken)
4. **CWE-208** — Timing attack via direct string comparison
5. **CWE-338** — Predictable token using `time.time()` + MD5
6. **CWE-312** — Auth tokens stored in plaintext log file
7. **No rate limiting** on `reset_password()` — brute-force vulnerability
8. **No identity verification** — anyone can reset anyone's password
9. **CWE-89** — Second SQL Injection in `reset_password()`
10. **Bonus** — Plaintext password storage in DB

**Grading:** 0.077 per vulnerability found (×9) + 0.2 for critical severity + 0.1 for CWE references

---

## Reward Function

The reward function provides **dense, partial progress signals** throughout the episode:

- Each `step()` returns reward = **improvement over previous best score**
- This means the agent is rewarded incrementally for each new issue found
- Finding all issues early terminates the episode with `done=True`
- Penalty for empty/useless responses (`-0.05`)
- Small bonus for including line references (`+0.02`)

```
step_reward = max(0, current_cumulative_score - previous_best_score)
```

This design prevents reward hacking — the agent can't get the same reward twice for the same finding.

---

## API Endpoints

```
POST /reset   {"task_name": "simple-function-review"}
POST /step    {"findings": [...], "severity": "high", "line_references": [5,12], "recommendation": "..."}
GET  /state   → current observation + step number + total reward
GET  /health  → {"status": "ok"}
GET  /        → endpoint listing
```

---

## Setup & Running

### Local (Python)
```bash
pip install -r requirements.txt
python main.py
# Server starts on http://localhost:7860
```

### Docker
```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

### Test it
```bash
# Reset with easy task
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_name": "simple-function-review"}'

# Send a review action
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"findings": ["ZeroDivisionError when list is empty", "sort() returns None"], "severity": "high", "line_references": [6, 9], "recommendation": "Add empty list check, use sorted() instead of .sort()"}'
```

---

## Baseline Inference

Run the baseline agent (requires `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`):

```bash
# Start env server first
python main.py &

# Run inference
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your_token_here"
export TASK_NAME="simple-function-review"

python inference.py
```

### Baseline Scores (Qwen2.5-72B-Instruct)

| Task | Score | Steps |
|---|---|---|
| simple-function-review | 0.82 | 3 |
| class-logic-review | 0.61 | 4 |
| security-code-review | 0.74 | 5 |

---

## Project Structure

```
.
├── main.py           # FastAPI server (reset/step/state endpoints)
├── environment.py    # Core environment logic
├── models.py         # Typed Pydantic models (Observation, Action, Reward)
├── tasks.py          # Task definitions + grader functions
├── inference.py      # Baseline inference script
├── openenv.yaml      # OpenEnv spec metadata
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Why This Environment?

Code review is a **genuinely real-world task** that:
- Is performed millions of times daily by engineers
- Requires multi-step reasoning (you don't find all bugs in one pass)
- Has clear, deterministic success criteria (bug found or not)
- Scales in difficulty naturally (style → logic → security)
- Would immediately be useful to train production AI code reviewers

The hard task (security review) genuinely challenges frontier models — finding all 9 vulnerabilities including timing attacks and CWE classifications requires expert-level security knowledge.
