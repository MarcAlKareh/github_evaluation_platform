"""
FastAPI server for the GitHub evaluator.

Run:
    uvicorn api:app --reload

Then open http://127.0.0.1:8000/docs for interactive API docs.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from evaluation import ROLE_PROFILES, run_evaluation

app = FastAPI(
    title="GitHub Evaluation API",
    description="Evaluate and rank GitHub candidates for engineering roles.",
    version="1.0.0",
)

# Allow a frontend on another port to call this API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvaluateRequest(BaseModel):
    role: str = Field(default="backend", examples=["frontend"])
    usernames: list[str] = Field(..., min_length=1, examples=[["gaearon", "torvalds"]])


@app.get("/")
def root():
    return {
        "message": "GitHub Evaluation API",
        "docs": "/docs",
        "roles": list(ROLE_PROFILES.keys()),
    }


@app.get("/roles")
def list_roles():
    return {key: profile["label"] for key, profile in ROLE_PROFILES.items()}


@app.post("/evaluate")
def evaluate_candidates(body: EvaluateRequest):
    """Evaluate one or more GitHub usernames for a role. Returns ranked JSON."""
    try:
        report = run_evaluation(body.role, body.usernames)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not report.get("ranking"):
        raise HTTPException(
            status_code=404,
            detail="No candidates could be evaluated",
            headers={"X-Errors": str(report.get("errors", []))},
        )

    return report


@app.get("/evaluate")
def evaluate_candidates_get(
    role: str = Query(default="backend"),
    usernames: str = Query(..., description="Comma-separated GitHub usernames"),
):
    """Same as POST /evaluate — handy for quick browser tests."""
    username_list = [u.strip().lstrip("@") for u in usernames.split(",") if u.strip()]
    return evaluate_candidates(EvaluateRequest(role=role, usernames=username_list))
