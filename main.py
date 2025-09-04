"""
Minimal FastAPI app for the DevOps interview task.

What it does:
- Provides a tiny authenticated API.
- Fetches jokes from https://official-joke-api.appspot.com/random_joke.
- Persists unique jokes (by external_id) into a local SQLite DB.
- Allows listing and retrieving stored jokes.

Intentionally *omitted* (on purpose for the interviewee to add/justify):
- Health/readiness/liveness endpoints
- Observability/metrics
- Robust retries/circuit breakers
- Proper user management & secure auth
- Migrations and production DB settings
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import httpx
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

DB_PATH = os.getenv("DATABASE_PATH", "jokes.db")
EXTERNAL_JOKE_BASE_URL = os.getenv("EXTERNAL_JOKE_BASE_URL", "https://official-joke-api.appspot.com")
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "3.0"))

# --- super-minimal "auth" (in-memory) ----------------------------------------
# One demo user; replace with real auth in production.
DEMO_USERS = {"admin": "admin"}  # username: password
TOKENS: Dict[str, str] = {}  # token -> username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    user = TOKENS.get(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user

# --- DB helpers ---------------------------------------------------------------
def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jokes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id INTEGER UNIQUE,
                type TEXT,
                setup TEXT NOT NULL,
                punchline TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_jokes_created_at ON jokes(created_at DESC);
            """
        )
        conn.commit()

# --- Schemas -----------------------------------------------------------------
class JokeOut(BaseModel):
    id: int
    external_id: Optional[int] = None
    type: Optional[str] = None
    setup: str
    punchline: str
    created_at: str

class JokeList(BaseModel):
    items: List[JokeOut]
    total: int
    limit: int
    offset: int

# --- External client ----------------------------------------------------------
async def fetch_random_joke() -> Dict[str, Any]:
    url = f"{EXTERNAL_JOKE_BASE_URL}/random_joke"
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

# --- FastAPI app --------------------------------------------------------------
app = FastAPI(title="Minimal Joke API")

@app.on_event("startup")
def _startup():
    init_db()

# ---- Auth endpoints ----------------------------------------------------------
@app.post("/auth/token")
def issue_token(form: OAuth2PasswordRequestForm = Depends()):
    # super-minimal auth: accept the demo user only
    if DEMO_USERS.get(form.username) != form.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = secrets.token_urlsafe(32)
    TOKENS[token] = form.username
    return {"access_token": token, "token_type": "bearer"}

# ---- Business endpoints ------------------------------------------------------
@app.post("/jokes/fetch", response_model=JokeList, summary="Fetch N jokes from the public API and persist uniques")
async def fetch_and_store(
    count: int = Query(1, ge=1, le=20, description="How many jokes to fetch"),
    user: str = Depends(get_current_user),
):
    """
    Calls the external joke API `count` times, stores unique jokes (by external_id),
    and returns the most recently stored jokes (not guaranteed to equal `count` if duplicates occur).
    """
    stored_ids: list[int] = []
    now = datetime.now(timezone.utc).isoformat()

    with connect() as conn:
        for _ in range(count):
            data = await fetch_random_joke()
            ext_id = data.get("id")
            setup = data.get("setup") or ""
            punchline = data.get("punchline") or ""
            jtype = data.get("type")

            # INSERT OR IGNORE ensures uniqueness by external_id
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO jokes (external_id, type, setup, punchline, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ext_id, jtype, setup, punchline, now),
            )
            if cur.rowcount:  # inserted
                stored_ids.append(cur.lastrowid)
        conn.commit()

        # Return the latest items we just inserted (if any) else latest overall
        if stored_ids:
            placeholders = ",".join(["?"] * len(stored_ids))
            rows = conn.execute(
                f"SELECT id, external_id, type, setup, punchline, created_at FROM jokes WHERE id IN ({placeholders}) ORDER BY id DESC",
                stored_ids,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, external_id, type, setup, punchline, created_at FROM jokes ORDER BY id DESC LIMIT ?",
                (count,),
            ).fetchall()

    items = [JokeOut(**dict(r)) for r in rows]
    return JokeList(items=items, total=len(items), limit=len(items), offset=0)

@app.get("/jokes", response_model=JokeList, summary="List stored jokes")
def list_jokes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None, description="Search in setup/punchline"),
    user: str = Depends(get_current_user),
):
    where = ""
    params: list[Any] = []
    if q:
        where = "WHERE setup LIKE ? OR punchline LIKE ?"
        like = f"%{q}%"
        params.extend([like, like])

    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM jokes {where}", params).fetchone()[0]
        params_with_paging = params + [limit, offset]
        rows = conn.execute(
            f"""
            SELECT id, external_id, type, setup, punchline, created_at
            FROM jokes
            {where}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            params_with_paging,
        ).fetchall()

    items = [JokeOut(**dict(r)) for r in rows]
    return JokeList(items=items, total=total, limit=limit, offset=offset)

@app.get("/jokes/{joke_id}", response_model=JokeOut, summary="Get a single stored joke by id")
def get_joke(joke_id: int, user: str = Depends(get_current_user)):
    with connect() as conn:
        row = conn.execute(
            "SELECT id, external_id, type, setup, punchline, created_at FROM jokes WHERE id = ?",
            (joke_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return JokeOut(**dict(row))
