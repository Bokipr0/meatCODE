# Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · in-memory stores for the accounts + Claude-link tests (no Postgres, no network)
import time


class MemoryStore:
    """Same interface as user_accounts.PgStore."""

    def __init__(self):
        self.users, self.by_id, self.sessions, self._next, self.purged = {}, {}, {}, 1, 0

    def get_user_by_email(self, email):
        u = self.users.get(email.lower())
        return dict(u) if u else None

    def _new(self, **kw):
        u = {"id": self._next, "email": None, "password_hash": None, "display_name": None, "disabled": False, "claude_only": False}
        u.update(kw)
        self._next += 1
        self.by_id[u["id"]] = u
        return u

    def create_user(self, email, password_hash, display_name):
        u = self._new(email=email.lower(), password_hash=password_hash, display_name=display_name)
        self.users[email.lower()] = u
        return {k: v for k, v in u.items() if k != "password_hash"}

    def create_claude_user(self):
        u = self._new(claude_only=True)
        return {k: v for k, v in u.items() if k != "password_hash"}

    def set_display_name(self, user_id, name):
        self.by_id[user_id]["display_name"] = name

    def set_credentials(self, user_id, email, password_hash):
        u = self.by_id[user_id]
        if email.lower() in self.users or u["email"]:
            return False
        u.update(email=email.lower(), password_hash=password_hash)
        self.users[email.lower()] = u
        return True

    def activate_sessions(self, user_id):
        for s in self.sessions.values():
            if s["user_id"] == user_id:
                s["pending"] = False
        self.by_id[user_id]["last_login_at"] = time.time()                       # the Claude link completing counts as a login

    def purge_stale_provisional(self):
        self.purged += 1

    def touch_login(self, user_id):
        self.by_id[user_id]["last_login_at"] = time.time()

    def create_session(self, token_hash, user_id, days, user_agent, pending=False):
        self.sessions[token_hash] = {"user_id": user_id, "expires": time.time() + days * 86400, "pending": bool(pending)}

    def session_user(self, token_hash):
        s = self.sessions.get(token_hash)
        if not s or s["expires"] < time.time():
            return None
        u = self.by_id.get(s["user_id"])
        return {**{k: v for k, v in u.items() if k != "password_hash"}, "pending": s["pending"]} if u else None

    def delete_session(self, token_hash):
        self.sessions.pop(token_hash, None)


class MemoryLinkStore:
    """Same interface as claude_link.PgLinkStore."""

    def __init__(self):
        self.rows = {}

    def get(self, user_id):
        r = self.rows.get(user_id)
        return dict(r) if r else None

    def ensure_row(self, user_id):
        self.rows.setdefault(user_id, {"user_id": user_id, "user_profile_id": None, "connection_id": None,
                                       "status": "unlinked", "pending_state_hash": None, "pending_verifier": None,
                                       "pending_expires_at": None, "linked_at": None, "last_error": None})

    def set_profile(self, user_id, profile_id):
        self.rows[user_id]["user_profile_id"] = profile_id

    def set_pending(self, user_id, state_hash, verifier):
        r = self.rows[user_id]
        r.update(pending_state_hash=state_hash, pending_verifier=verifier, pending_expires_at=time.time() + 600,
                 last_error=None)
        if r["status"] != "linked":
            r["status"] = "pending"

    def take_pending(self, user_id, state_hash):
        r = self.rows.get(user_id)
        if not r or r["pending_state_hash"] != state_hash or (r["pending_expires_at"] or 0) < time.time():
            return None
        v = r["pending_verifier"]
        r.update(pending_state_hash=None, pending_verifier=None, pending_expires_at=None)
        return v

    def mark_linked(self, user_id, connection_id):
        self.rows[user_id].update(status="linked", connection_id=connection_id, linked_at="now", last_error=None)

    def mark_revoked(self, user_id, error=None):
        self.rows[user_id].update(status="revoked", last_error=error)

    def set_error(self, user_id, code):
        self.rows[user_id]["last_error"] = code

    def set_needs_credits(self, user_id, flag):
        self.rows[user_id]["needs_credits"] = bool(flag)


class MemoryUsageStore:
    """Same interface as usage_log.PgUsageStore. `users` (a MemoryStore) supplies last_login_at like the SQL join does."""

    def __init__(self, users=None, links=None):
        self.rows, self.last_used, self.users, self.links = [], {}, users, links

    def record(self, user_id, route, model, input_tokens, output_tokens, status, **extra):
        self.rows.append({"user_id": user_id, "route": route, "model": model, "input_tokens": input_tokens,
                          "output_tokens": output_tokens, "status": status, "created_at": time.time(), **extra})
        if status != "error":
            self.last_used[user_id] = time.time()
            if self.links and extra.get("billed_to", "user_profile") != "trial" and user_id in self.links.rows:
                self.links.rows[user_id]["needs_credits"] = False          # like the SQL: a successful billed call proves credit

    def trial_answer_times(self, user_id):
        import datetime
        return [datetime.datetime.fromtimestamp(r["created_at"], datetime.timezone.utc) for r in self.rows
                if r["user_id"] == user_id and r.get("billed_to") == "trial" and r.get("kind") == "answer"]

    def last_times(self, user_id):
        import datetime
        ts = lambda v: datetime.datetime.fromtimestamp(v, datetime.timezone.utc) if v else None
        login = self.users.by_id.get(user_id, {}).get("last_login_at") if self.users else None
        return {"last_login_at": ts(login), "last_used_at": ts(self.last_used.get(user_id))}

    def month_totals(self, user_id):
        mine = [r for r in self.rows if r["user_id"] == user_id]
        return {"requests": len(mine), "input_tokens": sum(r["input_tokens"] for r in mine),
                "output_tokens": sum(r["output_tokens"] for r in mine)}

    def recent(self, user_id, limit=8):
        import datetime
        mine = [r for r in reversed(self.rows) if r["user_id"] == user_id][:limit]
        return [{**r, "created_at": datetime.datetime.fromtimestamp(r["created_at"], datetime.timezone.utc)} for r in mine]
