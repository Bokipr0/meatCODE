# Last updated: 2026-11-21 UTC · Claude (Sonnet 5.5) · NEW — per-user usage log behind the profile pop-out (flag `user_accounts`)
"""What a signed-in individual has used, from requests billed to their own Claude organization.

Metadata only (route, model, token counts, status) — never a question, an answer or source text.
`snapshot()` is what GET /api/account/usage returns; the stores are tiny so tests use an in-memory twin.
"""
from datetime import datetime, timezone

ROUTE_LABELS = {
    "/api/ask": "Oracle answer",
    "/api/consensus-demo": "Consensus check",
    "/api/ecosystem/intent": "Ecosystem search",
    "/api/graph-oracle/ask": "Graph Oracle",
}
RECENT_LIMIT = 8


def route_label(route: str) -> str:
    return ROUTE_LABELS.get(route, "Claude request")


class PgUsageStore:
    def __init__(self, database_url):
        self.url = database_url

    def _run(self, sql, params=(), fetch="none"):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(self.url)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                out = None
                if fetch == "one" and cur.description:
                    row = cur.fetchone()
                    out = dict(row) if row else None
                elif fetch == "all" and cur.description:
                    out = [dict(r) for r in cur.fetchall()]
            conn.commit()
            return out
        finally:
            conn.close()

    def record(self, user_id, route, model, input_tokens, output_tokens, status):
        self._run("INSERT INTO app_usage_log (user_id, route, model, input_tokens, output_tokens, status) "
                  "VALUES (%s,%s,%s,%s,%s,%s)",
                  (user_id, (route or "")[:120], (model or "")[:80] or None, int(input_tokens or 0),
                   int(output_tokens or 0), "error" if status == "error" else "ok"))

    def month_totals(self, user_id):
        return self._run("SELECT count(*)::int AS requests, COALESCE(sum(input_tokens),0)::bigint AS input_tokens, "
                         "COALESCE(sum(output_tokens),0)::bigint AS output_tokens FROM app_usage_log "
                         "WHERE user_id=%s AND created_at >= date_trunc('month', now())", (user_id,), "one")

    def recent(self, user_id, limit=RECENT_LIMIT):
        return self._run("SELECT created_at, route, model, input_tokens, output_tokens, status FROM app_usage_log "
                         "WHERE user_id=%s ORDER BY created_at DESC, id DESC LIMIT %s", (user_id, int(limit)), "all") or []


def snapshot(store, user_id) -> dict:
    """The JSON the pop-out shows. Raises if the table is missing — the route turns that into available:false."""
    totals = store.month_totals(user_id) or {}
    return {
        "month_label": datetime.now(timezone.utc).strftime("%B %Y"),
        "requests": int(totals.get("requests") or 0),
        "input_tokens": int(totals.get("input_tokens") or 0),
        "output_tokens": int(totals.get("output_tokens") or 0),
        "recent": [{"at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else r["created_at"], "label": route_label(r.get("route")), "model": r.get("model"),
                    "input_tokens": int(r.get("input_tokens") or 0), "output_tokens": int(r.get("output_tokens") or 0),
                    "status": r.get("status") or "ok"} for r in store.recent(user_id)],
    }
