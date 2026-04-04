"""
Typed Pydantic models for CodeReviewEnv.
Implements the OpenEnv spec: Observation, Action, Reward, StepResult.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class CodeReviewObservation(BaseModel):
    code: str = Field(description="The code snippet to review")
    language: str = Field(description="Programming language of the snippet")
    task_description: str = Field(description="What the code is supposed to do")
    step_number: int = Field(description="Current step in the episode")
    previous_findings: List[str] = Field(
        default_factory=list,
        description="Findings reported in previous steps"
    )
    hint: Optional[str] = Field(
        default=None,
        description="Optional hint for partial progress"
    )


class CodeReviewAction(BaseModel):
    findings: List[str] = Field(
        description="List of issues found (bugs, security issues, style problems)",
        min_length=0
    )
    severity: str = Field(
        description="Overall severity: 'low', 'medium', 'high', 'critical'",
        default="medium"
    )
    line_references: List[int] = Field(
        default_factory=list,
        description="Line numbers where issues were found"
    )
    recommendation: str = Field(
        default="",
        description="Overall recommendation or fix summary"
    )


class CodeReviewReward(BaseModel):
    value: float = Field(description="Reward between 0.0 and 1.0", ge=0.0, le=1.0)
    breakdown: dict = Field(
        default_factory=dict,
        description="Breakdown of reward components"
    )


class StepResult(BaseModel):
    observation: CodeReviewObservation
    reward: float = Field(ge=-0.1, le=1.0)
    done: bool
    info: dict = Field(default_factory=dict)


class ResetResult(BaseModel):
    observation: CodeReviewObservation
    info: dict = Field(default_factory=dict)


class StateResult(BaseModel):
    observation: CodeReviewObservation
    step_number: int
    done: bool
    total_reward: float
    task_name: str
