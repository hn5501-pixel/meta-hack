"""
CodeReviewEnv — Core environment logic.
Implements step() / reset() / state() per OpenEnv spec.
"""
import copy
from typing import Optional

from .models import (
    CodeReviewObservation,
    CodeReviewAction,
    StepResult,
    ResetResult,
    StateResult,
)
from .tasks import ALL_TASKS, GRADERS


class CodeReviewEnv:
    """
    Real-world OpenEnv environment: AI code reviewer.

    An agent is given code snippets and must identify bugs, security issues,
    and style problems. The environment provides partial rewards as the agent
    progressively uncovers more issues.

    Episode flow:
        reset(task_name) → observe code → step(action) → partial reward
        → observe updated code context → step(action) → ... → done
    """

    def __init__(self, task_name: str = "simple-function-review"):
        if task_name not in ALL_TASKS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(ALL_TASKS.keys())}")
        self.task_name = task_name
        self._task = ALL_TASKS[task_name]
        self._grader = GRADERS[task_name]
        self._step_number: int = 0
        self._done: bool = False
        self._total_reward: float = 0.0
        self._all_findings: list[str] = []
        self._best_score: float = 0.0
        self._step_rewards: list[float] = []

    def reset(self) -> ResetResult:
        """Reset environment to initial state, return first observation."""
        self._step_number = 0
        self._done = False
        self._total_reward = 0.0
        self._all_findings = []
        self._best_score = 0.0
        self._step_rewards = []

        obs = self._make_observation()
        return ResetResult(observation=obs, info={"task": self.task_name})

    def step(self, action: CodeReviewAction) -> StepResult:
        """
        Process one review action from the agent.

        Reward signal:
          - Partial reward for each newly identified issue category.
          - Bonus for correct severity rating.
          - Penalty for empty or trivially short findings.
          - Episode ends when max_steps reached or agent finds all issues.
        """
        if self._done:
            obs = self._make_observation()
            return StepResult(
                observation=obs,
                reward=0.0,
                done=True,
                info={"warning": "Episode already done"},
            )

        self._step_number += 1

        # Accumulate findings across steps (agent builds understanding)
        new_findings = action.findings or []
        self._all_findings.extend(new_findings)

        # Score the cumulative action so far
        cumulative_action = {
            "findings": self._all_findings,
            "severity": action.severity,
            "line_references": action.line_references,
            "recommendation": action.recommendation,
        }
        current_score = self._grader(cumulative_action)

        # Reward = improvement over best seen so far (partial progress signal)
        step_reward = max(0.0, current_score - self._best_score)
        self._best_score = max(self._best_score, current_score)

        # Small penalty for completely empty or useless responses
        if not new_findings and not action.recommendation:
            step_reward = step_reward - 0.05

        # Small bonus for adding line references (shows precision)
        if action.line_references:
            step_reward = min(1.0, step_reward + 0.02)

        step_reward = round(min(max(step_reward, -0.1), 1.0), 4)
        self._step_rewards.append(step_reward)
        self._total_reward += step_reward

        # Check termination
        max_steps = self._task["max_steps"]
        all_found = current_score >= 0.85
        self._done = (self._step_number >= max_steps) or all_found

        obs = self._make_observation()

        info = {
            "cumulative_score": current_score,
            "best_score": self._best_score,
            "step_reward": step_reward,
            "issues_found_pct": round(current_score * 100, 1),
            "all_issues_found": all_found,
        }

        return StepResult(
            observation=obs,
            reward=step_reward,
            done=self._done,
            info=info,
        )

    def state(self) -> StateResult:
        """Return current environment state without advancing the episode."""
        return StateResult(
            observation=self._make_observation(),
            step_number=self._step_number,
            done=self._done,
            total_reward=round(self._total_reward, 4),
            task_name=self.task_name,
        )

    def _make_observation(self) -> CodeReviewObservation:
        task = self._task

        # After step 1, provide a hint if score is low (partial progress signal)
        hint: Optional[str] = None
        if self._step_number >= 2 and self._best_score < 0.4:
            hint = (
                f"You've identified {round(self._best_score * 100)}% of issues so far. "
                f"Consider looking at: error handling, data flow between operations, "
                f"and security implications."
            )
        elif self._step_number >= 3 and self._best_score < 0.7:
            hint = (
                f"Score: {round(self._best_score * 100)}%. "
                f"Think about: what happens in edge cases? What if inputs are unexpected?"
            )

        return CodeReviewObservation(
            code=task["code"],
            language=task["language"],
            task_description=task["task_description"],
            step_number=self._step_number,
            previous_findings=list(self._all_findings),
            hint=hint,
        )
