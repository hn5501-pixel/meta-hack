"""
inference.py — Baseline inference script for CodeReviewEnv.
MANDATORY FORMAT: [START], [STEP], [END] stdout lines.

Reads from environment variables:
  API_BASE_URL   LLM endpoint
  MODEL_NAME     Model identifier
  HF_TOKEN       Hugging Face / API key
  TASK_NAME      Which task to run (default: simple-function-review)
  BASE_URL       The running CodeReviewEnv server (default: http://localhost:7860)
"""

import os
import json
import sys
import requests
from typing import List, Optional
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
API_KEY      = os.getenv("HF_TOKEN",     "not-set")
BASE_URL     = os.getenv("BASE_URL",     "http://localhost:7860")
TASK_NAME    = os.getenv("TASK_NAME",    "simple-function-review")
BENCHMARK    = "code-review-env"
MAX_STEPS    = 6
TEMPERATURE  = 0.2
MAX_TOKENS   = 600


# ─── Logging helpers (exact format required by spec) ─────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    # Truncate action for log readability (keep single line)
    action_short = action.replace("\n", " ")[:120]
    print(
        f"[STEP] step={step} action={action_short!r} "
        f"reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}",
        flush=True,
    )


# ─── Environment API helpers ──────────────────────────────────────────────────

def env_reset(task_name: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/reset",
        json={"task_name": task_name},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def env_step(action_dict: dict) -> dict:
    resp = requests.post(
        f"{BASE_URL}/step",
        json=action_dict,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def env_state() -> dict:
    resp = requests.get(f"{BASE_URL}/state", timeout=10)
    resp.raise_for_status()
    return resp.json()


# ─── LLM agent ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert software engineer conducting a thorough code review.
Your job is to identify ALL bugs, security vulnerabilities, logic errors, and style issues
in the given code.

For each step, respond ONLY with a valid JSON object in this exact format:
{
  "findings": ["finding 1", "finding 2", "finding 3"],
  "severity": "low|medium|high|critical",
  "line_references": [5, 12, 18],
  "recommendation": "Overall recommendation for fixing the code"
}

Be specific. Reference exact variable names, function names, and line numbers.
For security issues, name the vulnerability class (e.g., SQL Injection, CWE-89).
Do not repeat findings from previous steps — build on them."""


def build_user_prompt(obs: dict, step: int) -> str:
    code = obs.get("code", "")
    lang = obs.get("language", "python")
    task_desc = obs.get("task_description", "")
    previous = obs.get("previous_findings", [])
    hint = obs.get("hint")

    prev_text = ""
    if previous:
        prev_text = "\n\nISSUES ALREADY IDENTIFIED:\n" + "\n".join(f"- {f}" for f in previous)

    hint_text = f"\n\nHINT: {hint}" if hint else ""

    return f"""TASK: {task_desc}

LANGUAGE: {lang}
STEP: {step} of {MAX_STEPS}

CODE TO REVIEW:
```{lang}
{code}
```
{prev_text}{hint_text}

Provide your code review findings as a JSON object. Focus on NEW issues not yet identified.
Respond with ONLY the JSON object, no markdown, no explanation."""


def get_agent_action(client: OpenAI, obs: dict, step: int, history: List[str]) -> dict:
    user_prompt = build_user_prompt(obs, step)

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        text = (completion.choices[0].message.content or "").strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        action = json.loads(text)
        # Ensure required fields
        action.setdefault("findings", [])
        action.setdefault("severity", "medium")
        action.setdefault("line_references", [])
        action.setdefault("recommendation", "")
        return action

    except json.JSONDecodeError:
        # Fallback: extract any findings from raw text
        return {
            "findings": [text[:200]] if text else ["Unable to parse response"],
            "severity": "medium",
            "line_references": [],
            "recommendation": text[:200] if text else "",
        }
    except Exception as exc:
        return {
            "findings": [f"Agent error: {exc}"],
            "severity": "low",
            "line_references": [],
            "recommendation": "",
        }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    rewards:    List[float] = []
    steps_taken = 0
    success     = False
    done        = False
    error_msg:  Optional[str] = None
    history:    List[str] = []

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        reset_result = env_reset(TASK_NAME)
        obs = reset_result.get("observation", reset_result)

        for step in range(1, MAX_STEPS + 1):
            # Get action from LLM agent
            action_dict = get_agent_action(client, obs, step, history)
            action_str  = json.dumps(action_dict)

            # Step environment
            step_result = env_step(action_dict)

            reward = float(step_result.get("reward", 0.0))
            done   = bool(step_result.get("done", False))
            info   = step_result.get("info", {})
            error  = None

            rewards.append(reward)
            steps_taken = step

            # Record for history
            history.append(
                f"Step {step}: score={info.get('cumulative_score', 0):.2f} "
                f"reward={reward:.2f}"
            )

            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            if done:
                # Success if cumulative score ≥ 0.5
                success = info.get("best_score", 0) >= 0.5 or sum(rewards) >= 0.4
                break

            obs = step_result.get("observation", obs)

        if not rewards:
            success = False

        if rewards and not done:
            # Episode ended by max steps without finding all issues — evaluate final state
            final_state = env_state()
            total_r = final_state.get("total_reward", 0)
            success = total_r >= 0.4

    except Exception as exc:
        error_msg = str(exc)
        print(f"[DEBUG] Inference error: {exc}", file=sys.stderr, flush=True)
        if not rewards:
            rewards = [0.0]

    finally:
        log_end(success=success, steps=steps_taken, rewards=rewards)


if __name__ == "__main__":
    main()
