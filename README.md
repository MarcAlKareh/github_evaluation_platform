# GitHub Evaluation Agent

Evaluate GitHub profiles for role fit (backend, frontend, ml, devops).

## Setup

```bash
pip install -r requirements.txt
```

Add `GITHUB_TOKEN` to a `.env` file (recommended for rate limits).

## CLI

```bash
python evaluation.py frontend gaearon torvalds
python evaluation.py frontend gaearon torvalds --json
```

## API (FastAPI)

```bash
uvicorn api:app --reload
```

- Interactive docs: http://127.0.0.1:8000/docs
- List roles: `GET /roles`
- Evaluate: `POST /evaluate` with body `{"role": "frontend", "usernames": ["gaearon", "torvalds"]}`
- Quick test: `GET /evaluate?role=frontend&usernames=gaearon,torvalds`
