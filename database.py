"""Storage layer for SRNHS Dashboard.

Local development uses SQLite so the app runs immediately after extracting the ZIP.
Published multi-user installations should set DATA_BACKEND=supabase and provide the
server-side Supabase URL and backend-only Secret key as environment variables. The service
key is never sent to browser JavaScript.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

import requests
from werkzeug.security import check_password_hash, generate_password_hash

from config import (
    DATA_BACKEND,
    FIRST_ACCOUNT_NAME,
    FIRST_ACCOUNT_PASSWORD,
    FIRST_ACCOUNT_USERNAME,
    LOCAL_DB_PATH,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)
from seed_data import ACTIONS, COHORT, GRADE_LABELS, LEVELS, RECORDS, RESOURCES, ROOM_SIZES, SETTINGS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class StorageError(RuntimeError):
    pass


class Storage:
    def __init__(self) -> None:
        self.mode = DATA_BACKEND
        if self.mode == "supabase":
            if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
                raise StorageError("Supabase mode requires SUPABASE_URL and a backend-only SUPABASE_SECRET_KEY (legacy service-role fallback is also supported).")
            self.remote = SupabaseRest(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        else:
            self.mode = "sqlite"
            LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._create_local_schema()
        self.ensure_seed_data()

    # -------------------------- Local SQL helpers --------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _create_local_schema(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS dashboard_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            dashboard_title TEXT NOT NULL,
            school_name TEXT NOT NULL,
            location TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            logo_url TEXT NOT NULL,
            login_background_url TEXT NOT NULL,
            main_green TEXT NOT NULL,
            sidebar_color TEXT NOT NULL,
            page_background TEXT NOT NULL,
            updated_at TEXT,
            updated_by TEXT
        );
        CREATE TABLE IF NOT EXISTS account_holders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            avatar_url TEXT,
            account_status TEXT NOT NULL DEFAULT 'Active',
            last_active TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS school_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_year TEXT NOT NULL,
            level TEXT NOT NULL,
            grade_level TEXT NOT NULL,
            enrollment INTEGER NOT NULL DEFAULT 0,
            dropouts INTEGER NOT NULL DEFAULT 0,
            repeaters INTEGER NOT NULL DEFAULT 0,
            teachers INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT,
            UNIQUE (school_year, grade_level)
        );
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_year TEXT NOT NULL UNIQUE,
            jhs_classrooms INTEGER NOT NULL DEFAULT 0,
            shs_classrooms INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT
        );
        CREATE TABLE IF NOT EXISTS room_sizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grade_level TEXT NOT NULL UNIQUE,
            room_length REAL NOT NULL,
            room_width REAL NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT
        );
        CREATE TABLE IF NOT EXISTS cohort_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_year TEXT NOT NULL UNIQUE,
            baseline_year TEXT NOT NULL,
            grade7_baseline INTEGER NOT NULL,
            grade12_current INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT
        );
        CREATE TABLE IF NOT EXISTS action_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_year TEXT NOT NULL,
            analysis_type TEXT NOT NULL DEFAULT 'Prescriptive',
            focus_area TEXT NOT NULL,
            observed_pattern TEXT NOT NULL,
            data_basis TEXT,
            suggested_action TEXT NOT NULL,
            responsible_group TEXT NOT NULL,
            target_indicator TEXT,
            baseline_value TEXT,
            target_value TEXT,
            monitoring_period TEXT,
            current_result TEXT,
            status TEXT NOT NULL,
            progress_notes TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT
        );
        CREATE TABLE IF NOT EXISTS change_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at TEXT NOT NULL,
            display_name TEXT NOT NULL,
            action_label TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            undone INTEGER NOT NULL DEFAULT 0,
            undone_at TEXT
        );
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at TEXT NOT NULL,
            account_holder_id INTEGER,
            display_name TEXT NOT NULL,
            action TEXT NOT NULL,
            section TEXT NOT NULL,
            affected_record TEXT,
            details TEXT,
            FOREIGN KEY(account_holder_id) REFERENCES account_holders(id)
        );
        CREATE TABLE IF NOT EXISTS report_exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_name TEXT NOT NULL,
            exported_by TEXT NOT NULL,
            exported_at TEXT NOT NULL,
            selected_years TEXT,
            format TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workbook_exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exported_by TEXT NOT NULL,
            exported_at TEXT NOT NULL,
            file_name TEXT NOT NULL,
            included_school_years TEXT
        );
        """
        with self._connect() as conn:
            conn.executescript(schema)
            # Lightweight migrations let an older local preview database open after upgrade.
            existing = {row[1] for row in conn.execute("PRAGMA table_info(action_plans)").fetchall()}
            action_columns = {
                "analysis_type": "TEXT NOT NULL DEFAULT 'Prescriptive'",
                "data_basis": "TEXT",
                "target_indicator": "TEXT",
                "baseline_value": "TEXT",
                "target_value": "TEXT",
                "monitoring_period": "TEXT",
                "current_result": "TEXT",
                "progress_notes": "TEXT",
            }
            for column, declaration in action_columns.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE action_plans ADD COLUMN {column} {declaration}")

    # ---------------------------- Generic access ----------------------------
    def _list(self, table: str, order: str | None = None) -> list[dict[str, Any]]:
        if self.mode == "supabase":
            return self.remote.select(table, order=order)
        sql = f"SELECT * FROM {table}"
        if order:
            safe = order.replace(".desc", " DESC").replace(".asc", " ASC")
            sql += f" ORDER BY {safe}"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]

    def _insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "supabase":
            return self.remote.insert(table, row)[0]
        cols = list(row)
        placeholders = ",".join("?" for _ in cols)
        with self._connect() as conn:
            cur = conn.execute(
                f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                [row[c] for c in cols],
            )
            row = {**row, "id": cur.lastrowid}
        return row

    def _update(self, table: str, row_id: int, values: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "supabase":
            return self.remote.update(table, {"id": row_id}, values)[0]
        assignments = ",".join(f"{col}=?" for col in values)
        with self._connect() as conn:
            conn.execute(f"UPDATE {table} SET {assignments} WHERE id=?", [*values.values(), row_id])
            item = conn.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()
        return dict(item)

    def _delete(self, table: str, row_id: int) -> None:
        if self.mode == "supabase":
            self.remote.delete(table, {"id": row_id})
            return
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))

    def _find_one(self, table: str, filters: dict[str, Any]) -> dict[str, Any] | None:
        if self.mode == "supabase":
            rows = self.remote.select(table, filters=filters, limit=1)
            return rows[0] if rows else None
        where = " AND ".join(f"{key}=?" for key in filters)
        with self._connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE {where} LIMIT 1", list(filters.values())).fetchone()
        return dict(row) if row else None

    # ------------------------------- Seeding --------------------------------
    def ensure_seed_data(self) -> None:
        if self.mode == "supabase" and FIRST_ACCOUNT_PASSWORD == "srnhsadmin":
            raise StorageError("Set a private FIRST_ACCOUNT_PASSWORD environment variable before the first online deployment.")
        now = utc_now()
        if not self._find_one("dashboard_settings", {"id": 1}):
            values = {"id": 1, **SETTINGS, "updated_at": now, "updated_by": FIRST_ACCOUNT_USERNAME}
            self._insert("dashboard_settings", values)
        if not self.list_accounts():
            self._insert(
                "account_holders",
                {
                    "full_name": FIRST_ACCOUNT_NAME,
                    "username": FIRST_ACCOUNT_USERNAME,
                    "password_hash": generate_password_hash(FIRST_ACCOUNT_PASSWORD),
                    "avatar_url": "",
                    "account_status": "Active",
                    "last_active": "",
                    "created_at": now,
                    "updated_at": now,
                },
            )
        if not self.list_records():
            for year, payload in RECORDS.items():
                for index, grade in enumerate(GRADE_LABELS):
                    self.upsert_record(
                        {
                            "school_year": year,
                            "level": LEVELS[index],
                            "grade_level": grade,
                            "enrollment": payload["grades"][index],
                            "dropouts": payload["dropouts"][index],
                            "repeaters": payload["repeaters"][index],
                            "teachers": payload["teachers"][index],
                        },
                        FIRST_ACCOUNT_USERNAME,
                    )
            for year, payload in RESOURCES.items():
                self.upsert_resource(year, payload["jhs_classrooms"], payload["shs_classrooms"], FIRST_ACCOUNT_USERNAME)
            for grade, dims in ROOM_SIZES.items():
                self.upsert_room_size(grade, dims[0], dims[1], FIRST_ACCOUNT_USERNAME)
            for year, payload in COHORT.items():
                self.upsert_cohort(
                    year, payload["baseline_year"], payload["grade7_baseline"], payload["grade12_current"], FIRST_ACCOUNT_USERNAME
                )
            for action in ACTIONS:
                self.create_action(action, FIRST_ACCOUNT_USERNAME)

    # ------------------------------ Accounts --------------------------------
    def list_accounts(self) -> list[dict[str, Any]]:
        rows = self._list("account_holders", order="created_at.asc")
        for row in rows:
            row.pop("password_hash", None)
            row["password_display"] = "••••••••"
        return rows

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        account = self._find_one("account_holders", {"username": username})
        if not account or account.get("account_status") != "Active":
            return None
        if not check_password_hash(account["password_hash"], password):
            return None
        self._update("account_holders", account["id"], {"last_active": utc_now(), "updated_at": utc_now()})
        account.pop("password_hash", None)
        return account

    def create_account(self, full_name: str, username: str, password: str, avatar_url: str = "") -> dict[str, Any]:
        if self._find_one("account_holders", {"username": username}):
            raise StorageError("That username is already in use.")
        now = utc_now()
        row = self._insert(
            "account_holders",
            {
                "full_name": full_name,
                "username": username,
                "password_hash": generate_password_hash(password),
                "avatar_url": avatar_url,
                "account_status": "Active",
                "last_active": "",
                "created_at": now,
                "updated_at": now,
            },
        )
        row.pop("password_hash", None)
        row["password_display"] = "••••••••"
        return row

    def update_account(self, account_id: int, full_name: str, username: str, password: str | None = None, avatar_url: str | None = None) -> dict[str, Any]:
        existing = self._find_one("account_holders", {"username": username})
        if existing and int(existing["id"]) != int(account_id):
            raise StorageError("That username is already in use.")
        values = {"full_name": full_name, "username": username, "updated_at": utc_now()}
        if password:
            values["password_hash"] = generate_password_hash(password)
        if avatar_url is not None:
            values["avatar_url"] = avatar_url
        row = self._update("account_holders", account_id, values)
        row.pop("password_hash", None)
        row["password_display"] = "••••••••"
        return row

    def delete_account(self, account_id: int) -> None:
        if len(self.list_accounts()) <= 1:
            raise StorageError("At least one account holder must remain.")
        self._delete("account_holders", account_id)

    # --------------------------- Dashboard settings --------------------------
    def get_settings(self) -> dict[str, Any]:
        return self._find_one("dashboard_settings", {"id": 1}) or SETTINGS.copy()

    def update_settings(self, values: dict[str, Any], username: str) -> dict[str, Any]:
        allowed = {
            "dashboard_title", "school_name", "location", "subtitle", "logo_url",
            "login_background_url", "main_green", "sidebar_color", "page_background"
        }
        clean = {k: v for k, v in values.items() if k in allowed and isinstance(v, str)}
        clean.update({"updated_at": utc_now(), "updated_by": username})
        return self._update("dashboard_settings", 1, clean)

    # ------------------------------- Records --------------------------------
    def list_records(self) -> list[dict[str, Any]]:
        return self._list("school_records", order="school_year.desc")

    def upsert_record(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        now = utc_now()
        fields = {
            "school_year": str(payload["school_year"]).strip(),
            "level": str(payload["level"]).strip(),
            "grade_level": str(payload["grade_level"]).strip(),
            "enrollment": int(payload.get("enrollment") or 0),
            "dropouts": int(payload.get("dropouts") or 0),
            "repeaters": int(payload.get("repeaters") or 0),
            "teachers": int(payload.get("teachers") or 0),
            "updated_at": now,
            "updated_by": username,
        }
        existing = self._find_one("school_records", {"school_year": fields["school_year"], "grade_level": fields["grade_level"]})
        if existing:
            return self._update("school_records", existing["id"], fields)
        fields["created_at"] = now
        return self._insert("school_records", fields)

    def list_resources(self) -> list[dict[str, Any]]:
        return self._list("resources", order="school_year.desc")

    def upsert_resource(self, year: str, jhs: int, shs: int, username: str) -> dict[str, Any]:
        now = utc_now()
        values = {"school_year": year, "jhs_classrooms": int(jhs or 0), "shs_classrooms": int(shs or 0), "updated_at": now, "updated_by": username}
        existing = self._find_one("resources", {"school_year": year})
        if existing:
            return self._update("resources", existing["id"], values)
        values["created_at"] = now
        return self._insert("resources", values)

    def list_room_sizes(self) -> list[dict[str, Any]]:
        return self._list("room_sizes", order="grade_level.asc")

    def upsert_room_size(self, grade: str, length: float, width: float, username: str) -> dict[str, Any]:
        values = {"grade_level": grade, "room_length": float(length), "room_width": float(width), "updated_at": utc_now(), "updated_by": username}
        existing = self._find_one("room_sizes", {"grade_level": grade})
        if existing:
            return self._update("room_sizes", existing["id"], values)
        return self._insert("room_sizes", values)

    def list_cohort(self) -> list[dict[str, Any]]:
        return self._list("cohort_records", order="school_year.desc")

    def upsert_cohort(self, year: str, baseline_year: str, grade7: int, grade12: int, username: str) -> dict[str, Any]:
        now = utc_now()
        values = {
            "school_year": year, "baseline_year": baseline_year, "grade7_baseline": int(grade7 or 0),
            "grade12_current": int(grade12 or 0), "updated_at": now, "updated_by": username
        }
        existing = self._find_one("cohort_records", {"school_year": year})
        if existing:
            return self._update("cohort_records", existing["id"], values)
        values["created_at"] = now
        return self._insert("cohort_records", values)

    # ----------------------- Change history and delete -----------------------
    DATA_TABLES = ["school_records", "resources", "room_sizes", "cohort_records", "action_plans"]

    def snapshot_data(self, action_label: str, username: str) -> dict[str, Any]:
        """Save a reversible copy before an important school-data change."""
        payload = {table: self._list(table) for table in self.DATA_TABLES}
        return self._insert(
            "change_history",
            {
                "occurred_at": utc_now(),
                "display_name": username,
                "action_label": action_label,
                "snapshot_json": json.dumps(payload),
                "undone": False,
                "undone_at": None,
            },
        )

    def replace_school_data_from_workbook(self, imported: dict[str, Any], username: str) -> None:
        """Replace school records represented by an uploaded full workbook.

        Use this only after a user confirms full synchronization. Account holders,
        display settings and activity history are intentionally preserved.
        """
        for table in ["school_records", "resources", "cohort_records", "action_plans"]:
            for row in self._list(table):
                self._delete(table, int(row["id"]))
        for record in imported.get("records", []):
            self.upsert_record(record, username)
        for resource in imported.get("resources", []):
            self.upsert_resource(resource["school_year"], resource["jhs_classrooms"], resource["shs_classrooms"], username)
        for cohort in imported.get("cohorts", []):
            self.upsert_cohort(cohort["school_year"], cohort["baseline_year"], cohort["grade7_baseline"], cohort["grade12_current"], username)
        for action in imported.get("actions", []):
            self.upsert_action(action, username)

    def delete_school_year(self, school_year: str) -> dict[str, int]:
        """Remove a whole school year from records and related planning data."""
        counts: dict[str, int] = {}
        for table in ["school_records", "resources", "cohort_records", "action_plans"]:
            rows = [row for row in self._list(table) if str(row.get("school_year")) == school_year]
            counts[table] = len(rows)
            for row in rows:
                self._delete(table, int(row["id"]))
        return counts

    def delete_action(self, action_id: int) -> None:
        self._delete("action_plans", action_id)

    def undo_last_data_change(self, username: str) -> str:
        """Restore the most recent school-data snapshot exactly once."""
        if self.mode == "supabase":
            rows = self.remote.select("change_history", filters={"undone": "false"}, order="id.desc", limit=1)
        else:
            with self._connect() as conn:
                found = conn.execute("SELECT * FROM change_history WHERE undone=0 ORDER BY id DESC LIMIT 1").fetchone()
            rows = [dict(found)] if found else []
        if not rows:
            raise StorageError("No saved data change is available to undo.")
        change = rows[0]
        payload = json.loads(change["snapshot_json"])
        for table in self.DATA_TABLES:
            for row in self._list(table):
                self._delete(table, int(row["id"]))
            for row in payload.get(table, []):
                restored = {key: value for key, value in row.items() if key != "id"}
                self._insert(table, restored)
        self._update("change_history", int(change["id"]), {"undone": True, "undone_at": utc_now()})
        return str(change["action_label"])

    # --------------------------- Actions & activity --------------------------
    def list_actions(self) -> list[dict[str, Any]]:
        return self._list("action_plans", order="updated_at.desc")

    ACTION_FIELDS = [
        "school_year", "analysis_type", "focus_area", "observed_pattern", "data_basis",
        "suggested_action", "responsible_group", "target_indicator", "baseline_value",
        "target_value", "monitoring_period", "current_result", "status",
        "progress_notes", "notes"
    ]

    def create_action(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        now = utc_now()
        values = {key: str(payload.get(key, "")).strip() for key in self.ACTION_FIELDS}
        values["analysis_type"] = values["analysis_type"] or "Prescriptive"
        values["status"] = values["status"] or "Suggested"
        values.update({"created_at": now, "updated_at": now, "updated_by": username})
        return self._insert("action_plans", values)

    def update_action(self, action_id: int, payload: dict[str, Any], username: str) -> dict[str, Any]:
        values = {key: str(payload.get(key, "")).strip() for key in self.ACTION_FIELDS if key in payload}
        values.update({"updated_at": utc_now(), "updated_by": username})
        return self._update("action_plans", action_id, values)

    def upsert_action(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        year = str(payload.get("school_year", "")).strip()
        area = str(payload.get("focus_area", "")).strip()
        existing = self._find_one("action_plans", {"school_year": year, "focus_area": area}) if year and area else None
        if existing:
            return self.update_action(int(existing["id"]), payload, username)
        return self.create_action(payload, username)

    def log_activity(self, account: dict[str, Any] | None, action: str, section: str, affected: str = "", details: str = "") -> dict[str, Any]:
        name = account.get("full_name", "System") if account else "System"
        account_id = account.get("id") if account else None
        return self._insert(
            "activity_logs",
            {
                "occurred_at": utc_now(), "account_holder_id": account_id, "display_name": name,
                "action": action, "section": section, "affected_record": affected, "details": details,
            },
        )

    def list_activity(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._list("activity_logs", order="occurred_at.desc")
        return rows[:limit]

    def save_report_export(self, report_name: str, username: str, years: list[str], format_name: str) -> None:
        self._insert("report_exports", {"report_name": report_name, "exported_by": username, "exported_at": utc_now(), "selected_years": json.dumps(years), "format": format_name})

    def save_workbook_export(self, username: str, filename: str, years: list[str]) -> None:
        self._insert("workbook_exports", {"exported_by": username, "exported_at": utc_now(), "file_name": filename, "included_school_years": json.dumps(years)})


class SupabaseRest:
    """Small server-only PostgREST client for Supabase tables."""

    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, table: str, params: dict[str, Any] | None = None, body: Any = None, prefer: str = "return=representation") -> list[dict[str, Any]]:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        response = requests.request(method, f"{self.base_url}/rest/v1/{table}", headers=headers, params=params or {}, json=body, timeout=30)
        if not response.ok:
            raise StorageError(f"Supabase request failed for {table}: {response.status_code} {response.text[:300]}")
        if not response.text:
            return []
        return response.json()

    def select(self, table: str, filters: dict[str, Any] | None = None, order: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"select": "*"}
        for key, value in (filters or {}).items():
            params[key] = f"eq.{value}"
        if order:
            params["order"] = order
        if limit:
            params["limit"] = limit
        return self._request("GET", table, params=params, prefer="")

    def insert(self, table: str, row: dict[str, Any]) -> list[dict[str, Any]]:
        return self._request("POST", table, body=row)

    def update(self, table: str, filters: dict[str, Any], values: dict[str, Any]) -> list[dict[str, Any]]:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        return self._request("PATCH", table, params=params, body=values)

    def delete(self, table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        return self._request("DELETE", table, params=params)
