"""
CodeReviewEnv — Entry point.
Launches the FastAPI server from the server package.
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
