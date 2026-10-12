"""Seed the demo data the Nexora backend needs to create runs.

The backend's ``RunOrchestrator.create_run`` requires two things that a fresh
migration does not populate:

1. a ``repository_snapshots`` row per workspace (``ValueError: No repository
   snapshot for workspace`` otherwise), whose ``snapshot_path`` must exist on
   disk because the analyzer/security gateway read it directly, and
2. at least one enabled row in ``model_registry`` (``ValueError: No enabled
   models in registry`` otherwise).

This script is idempotent: re-running it updates the existing rows instead of
duplicating them. It only writes seed data -- no backend code is touched.

    python seed_demo_data.py
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "nexora.db"
FIXTURES = ROOT / "nexora" / "fixtures"

COMMIT_HASHES = {
    "sample-calculator": "9f1c2a4d5e6b7c8d9e0f1a2b3c4d5e6f",
    "sample-api": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
    "sample-cli": "7f8e9d0c1b2a39485766554433221100",
}

# Secondary provider. Nebius rows already exist from the migration; these Gemini
# rows are appended AFTER them on purpose -- ``ModelRouter.route`` picks the
# first row of the matching tier bucket in registry order, so appending keeps
# auto-routing on the primary provider. Gemini is reachable only through
# ``RoutingMode.FIXED`` + ``requested_model_id``.
GEMINI_MODELS = [
    {
        "model_id": "gemini-3.8-flash",
        "display_name": "Gemini 3.8 Flash",
        "tier": "super",
        "context_capacity": 1_048_576,
        "max_output_tokens": 8_192,
        "is_enabled": 1,
    },
    {
        "model_id": "gemini-3.5-flash-lite",
        "display_name": "Gemini 3.5 Flash Lite",
        "tier": "nano",
        "context_capacity": 1_048_576,
        "max_output_tokens": 4_096,
        "is_enabled": 1,
    },
    {
        # Registered but off: this key's quota tier rejects it with HTTP 429,
        # so it stays opt-in rather than breaking a run mid-flight.
        "model_id": "gemini-3.1-pro-preview",
        "display_name": "Gemini 3.1 Pro (preview)",
        "tier": "ultra",
        "context_capacity": 1_048_576,
        "max_output_tokens": 8_192,
        "is_enabled": 0,
    },
]


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"database not found: {db_path}")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def seed_snapshots(con: sqlite3.Connection) -> int:
    """One snapshot per workspace pointing at its on-disk fixture tree."""
    workspaces = con.execute(
        "SELECT id, name FROM workspaces ORDER BY created_at, name"
    ).fetchall()
    if not workspaces:
        raise SystemExit("no workspaces found -- run the schema migration first")

    inserted = 0
    for ws in workspaces:
        snapshot_path = FIXTURES / ws["name"]
        if not snapshot_path.is_dir():
            raise SystemExit(
                f"fixture directory missing for workspace {ws['name']!r}: {snapshot_path}"
            )
        py_files = sorted(snapshot_path.rglob("*.py"))
        if not py_files:
            raise SystemExit(f"no .py files under {snapshot_path}")

        existing = con.execute(
            "SELECT id FROM repository_snapshots WHERE workspace_id = ? ORDER BY created_at DESC LIMIT 1",
            (ws["id"],),
        ).fetchone()

        absolute = str(snapshot_path.resolve()).replace("\\", "/")
        commit_hash = COMMIT_HASHES.get(ws["name"], uuid.uuid5(uuid.NAMESPACE_URL, ws["name"]).hex)

        if existing:
            con.execute(
                "UPDATE repository_snapshots SET commit_hash = ?, branch_name = 'main',"
                " snapshot_path = ? WHERE id = ?",
                (commit_hash, absolute, existing["id"]),
            )
        else:
            con.execute(
                "INSERT INTO repository_snapshots"
                " (id, workspace_id, commit_hash, branch_name, snapshot_path, created_at)"
                " VALUES (?, ?, ?, 'main', ?, ?)",
                (str(uuid.uuid4()), ws["id"], commit_hash, absolute, utcnow()),
            )
            inserted += 1
        print(f"  snapshot  {ws['name']:<20} -> {absolute} ({len(py_files)} py files)")

    return inserted


def seed_gemini_models(con: sqlite3.Connection) -> int:
    """Register Gemini rows as the secondary provider.

    Appended after the primary provider's rows so registry order -- and with it
    ``ModelRouter``'s auto tier pick -- stays on Nebius.
    """
    inserted = 0
    for spec in GEMINI_MODELS:
        row = con.execute(
            "SELECT id FROM model_registry WHERE model_id = ?", (spec["model_id"],)
        ).fetchone()
        if row:
            con.execute(
                "UPDATE model_registry SET display_name = ?, provider = 'gemini',"
                " tier = ?, context_capacity = ?, max_output_tokens = ?,"
                " supports_tools = 1, supports_reasoning = 1, terms_reviewed = 1"
                " WHERE id = ?",
                (
                    spec["display_name"],
                    spec["tier"],
                    spec["context_capacity"],
                    spec["max_output_tokens"],
                    row["id"],
                ),
            )
            continue

        con.execute(
            "INSERT INTO model_registry"
            " (id, model_id, display_name, provider, tier, context_capacity,"
            "  max_output_tokens, supports_tools, supports_reasoning, is_enabled,"
            "  terms_reviewed, created_at)"
            " VALUES (?, ?, ?, 'gemini', ?, ?, ?, 1, 1, ?, 1, ?)",
            (
                str(uuid.uuid4()),
                spec["model_id"],
                spec["display_name"],
                spec["tier"],
                spec["context_capacity"],
                spec["max_output_tokens"],
                spec["is_enabled"],
                utcnow(),
            ),
        )
        inserted += 1
    return inserted


def seed_models(con: sqlite3.Connection) -> int:
    """Register secondary-provider rows, then enable the registry."""
    added = seed_gemini_models(con)
    enabled = con.execute(
        "UPDATE model_registry SET is_enabled = 1, terms_reviewed = 1"
        " WHERE provider = 'nebius' AND (is_enabled = 0 OR terms_reviewed = 0)"
    ).rowcount

    print(f"  {added} gemini row(s) inserted")
    for row in con.execute(
        "SELECT model_id, display_name, provider, tier, is_enabled"
        " FROM model_registry ORDER BY rowid"
    ):
        flag = "on " if row["is_enabled"] else "off"
        print(
            f"  model     {row['model_id']:<24} {row['display_name']:<24}"
            f" {row['provider']:<7} tier={row['tier']:<6} {flag}"
        )
    return enabled or 0


def verify(con: sqlite3.Connection) -> None:
    problems: list[str] = []

    orphan = con.execute(
        "SELECT w.name FROM workspaces w"
        " LEFT JOIN repository_snapshots s ON s.workspace_id = w.id"
        " WHERE s.id IS NULL"
    ).fetchall()
    for row in orphan:
        problems.append(f"workspace {row['name']!r} has no repository snapshot")

    if not con.execute(
        "SELECT 1 FROM model_registry WHERE is_enabled = 1 LIMIT 1"
    ).fetchone():
        problems.append("no enabled models in model_registry")

    # Auto routing picks the first enabled row of the matching tier bucket in
    # registry order, so a secondary-provider row inserted ahead of the primary
    # one would silently take over auto mode. Fail loudly instead.
    for tier in ("nano", "super", "ultra"):
        head = con.execute(
            "SELECT provider FROM model_registry"
            " WHERE is_enabled = 1 AND tier = ? ORDER BY rowid LIMIT 1",
            (tier,),
        ).fetchone()
        if head and head["provider"] != "nebius":
            problems.append(
                f"auto-routing for tier {tier!r} would resolve to secondary "
                f"provider {head['provider']!r}, not the primary provider"
            )

    for row in con.execute("SELECT snapshot_path FROM repository_snapshots"):
        if not Path(row["snapshot_path"]).is_dir():
            problems.append(f"snapshot_path does not exist: {row['snapshot_path']}")

    if not con.execute(
        "SELECT 1 FROM budget_profiles WHERE is_default = 1 LIMIT 1"
    ).fetchone():
        problems.append("no default budget profile")

    if problems:
        print("\nFAILED:")
        for problem in problems:
            print(f"  - {problem}")
        raise SystemExit(1)
    print("\nOK: every workspace has a snapshot, models are enabled, paths resolve.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    args = parser.parse_args()

    print(f"Seeding {args.db}")
    con = connect(args.db)
    try:
        print("\nRepository snapshots:")
        snapshots = seed_snapshots(con)
        print(f"  ({snapshots} new row(s), existing rows refreshed)\n")

        print("Model registry:")
        models = seed_models(con)
        print(f"  ({models} row(s) updated)\n")

        con.commit()
        verify(con)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
