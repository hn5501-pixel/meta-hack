"""
CodeReviewEnv — FastAPI server.
Exposes OpenEnv-compliant endpoints: POST /reset, POST /step, GET /state
"""
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .environment import CodeReviewEnv
from .models import CodeReviewAction

app = FastAPI(
    title="CodeReviewEnv",
    description=(
        "OpenEnv environment: AI agent as code reviewer. "
        "Real-world task: identify bugs, security issues, and style violations in code."
    ),
    version="1.0.0",
)

def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()


# Single global env instance (stateful per container)
_env: Optional[CodeReviewEnv] = None


class ResetRequest(BaseModel):
    task_name: str = "simple-function-review"


@app.get("/")
def root():
    return {
        "name": "CodeReviewEnv",
        "version": "1.0.0",
        "tasks": [
            "simple-function-review",
            "class-logic-review",
            "security-code-review",
        ],
        "endpoints": {
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state",
        },
    }


@app.post("/reset")
def reset(request: ResetRequest = ResetRequest()):
    """Initialize or restart the environment with the given task."""
    global _env
    try:
        _env = CodeReviewEnv(task_name=request.task_name)
        result = _env.reset()
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {e}")


@app.post("/step")
def step(action: CodeReviewAction):
    """Advance the environment by one step with the given action."""
    global _env
    if _env is None:
        raise HTTPException(
            status_code=400,
            detail="Environment not initialized. Call POST /reset first."
        )
    try:
        result = _env.step(action)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step failed: {e}")


@app.get("/state")
def state():
    """Return current environment state without modifying it."""
    global _env
    if _env is None:
        raise HTTPException(
            status_code=400,
            detail="Environment not initialized. Call POST /reset first."
        )
    try:
        result = _env.state()
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"State failed: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "env_initialized": _env is not None}


