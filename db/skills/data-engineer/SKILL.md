---
name: data-engineer
description: >-
  MeatCODE data-engineering playbook for the Neon Postgres database. Its core is
  safe schema changes — drop, add, or rename a column or table — with
  dependent-view handling, transaction safety, numbered migration files, live
  apply + verification, and a plain-language walkthrough so Lior can do it himself.
  Use this WHENEVER the user wants to remove/delete/drop an unused column or table,
  add or rename a column, clean up the `sources`, `molecules`, `experts`, or any
  other Neon table, "get rid of these queries/columns", reshape/restructure the DB,
  run a migration, or asks "how do I change the schema myself?" — even when phrased
  casually like "delete these columns", "this field is empty, drop it", or "can you
  remove this from the DB". Prefer this skill over ad-hoc SQL for any DDL against
  the MeatCODE database; it prevents the two classic failures (dropping data that
  was still used, and DROP COLUMN blocked by a dependent view).
---

# MeatCODE — data engineer (safe schema changes on Neon)

This is the MeatCODE **data-engineering** skill. Its current playbook is **safe schema changes** on the production Neon Postgres database — extend it as new data-engineering procedures get proven.

Two things go wrong when people change a live schema by hand, and this skill exists to prevent both:

1. **Dropping something that was still in use** — a column that looked empty but wasn't, or a table another view/query depended on.
2. **`DROP COLUMN` blocked by a dependent view** — Postgres refuses to drop a column that any view reads, with `cannot drop column … because other objects depend on it`. The fix is not to blindly `CASCADE` (that silently deletes the view too).

The whole discipline is: **prove the data is expendable, prove nothing structural depends on it, then make the change inside a transaction so any surprise is a `ROLLBACK` and not a cleanup job.** After applying, verify and log it.

Default mode is **apply-and-teach**: run the change against Neon yourself, write the migration file, AND explain the steps so Lior can do it himself next time. If the user only wants the SQL drafted (not applied), give them the migration + the self-service recipe and stop before touching the live DB.

---

## The core principle: two independent safety checks

Before any destructive change, answer both — they are independent and you need both green:

| Check | Question | How to answer |
|---|---|---|
| **Data safety** | Is the data actually expendable? | For a drop: `SELECT count(col) FROM t;` — `count()` ignores NULLs, so `0` means every row is empty. If it's non-zero, stop and confirm with the user that losing it is intended. |
| **Structural safety** | What depends on this object? | Query the catalog for dependent views / FKs / generated columns (queries below). A dependency doesn't block you, but you must handle it deliberately. |

If either check surprises you, **stop and surface it to the user** rather than pressing on.

---

## Setup: connecting to Neon

The connection string lives in `meatCODE/.env` as `DATABASE_URL`. From the sandbox, load it and connect with psycopg2:

```python
import os, psycopg2
for l in open("meatCODE/.env"):
    if l.startswith("DATABASE_URL"):
        os.environ["DATABASE_URL"] = l.split("=", 1)[1].strip()
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = False          # keep manual control so we can ROLLBACK
cur = conn.cursor()
```

Keep `autocommit = False` — the whole point is that a bad result can be rolled back. Only `conn.commit()` once verification inside the transaction looks right.

Lior can run the same SQL himself without Python via the **Neon SQL Editor** (console.neon.tech → project → SQL Editor) or a desktop client he already has (**TablePlus / Postico**) pointed at `DATABASE_URL`.

---

## Pre-flight: find what depends on the object

This is the step everyone forgets. Run it *before* editing.

**Views that read a column:**
```sql
SELECT DISTINCT view_name
FROM information_schema.view_column_usage
WHERE table_name = 'molecules' AND column_name = 'aliases';
```

**Foreign keys that reference a table:**
```sql
SELECT conrelid::regclass AS referencing_table, conname
FROM pg_constraint
WHERE confrelid = 'molecules'::regclass AND contype = 'f';
```

**Capture a view's definition** so you can rebuild it after the column is gone:
```sql
SELECT pg_get_viewdef('v_mvl_gaps'::regclass, true);
```

If a dependent view exists, decide: is the column actually used by the view's logic, or is it a *dead branch* (e.g. an alias-match clause over an empty column that can never match)? Dead branches can be removed with no behavior change. Live logic means the view genuinely needs the data — reconsider the drop.

---

## Workflows by change type

### Drop a column (the most common request)

1. **Data safety:** `SELECT count(<col>) FROM <table>;` → expect `0`, else confirm with user.
2. **Structural safety:** run the view-usage query above.
3. **Write the migration** (see convention below) wrapped in `BEGIN … COMMIT`.
4. If a view depends on the column: inside the same transaction, `DROP VIEW` → `ALTER TABLE … DROP COLUMN` → `CREATE VIEW …` rebuilt **without** the reference. (Full pattern in the next section.)
5. **Apply** to Neon, then **verify**: the column is gone, the row count is unchanged, and every rebuilt view still returns rows.

Minimal SQL when nothing depends on the column:
```sql
BEGIN;
ALTER TABLE <table> DROP COLUMN IF EXISTS <col>;
COMMIT;
```

### Add a column

Additive and safe, but choose the default deliberately — a `NOT NULL` column with no default fails on a non-empty table.
```sql
BEGIN;
ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <col> <type>;   -- nullable, no rewrite
-- if it must be NOT NULL, backfill first, then SET NOT NULL in a later step
COMMIT;
```

### Rename a column or table

Cheap at the catalog level, but **every view, query, and app string that names the old identifier breaks**. Grep the repo (`server/`, `app/`, `pipeline/`, `db/`) for the old name first and update those in the same change.
```sql
BEGIN;
ALTER TABLE <table> RENAME COLUMN <old> TO <new>;
COMMIT;
```

### Drop a table

Run the FK query first. Prefer rebuilding dependents over `CASCADE`. If truly orphaned:
```sql
BEGIN;
DROP TABLE IF EXISTS <table>;
COMMIT;
```

---

## Handling dependent views — the #1 gotcha

When a view reads a column you want to drop, you have two options:

- **Rebuild the view without the reference (preferred, non-destructive).** Capture the definition with `pg_get_viewdef`, remove only the term that touches the doomed column, and recreate it in the same transaction. The view keeps working. This is right when the column is empty or the reference is a dead branch, so removing it doesn't change results.
- **`DROP COLUMN … CASCADE` (fast, destructive).** Postgres drops the column *and every dependent view*. Only use this when you're certain those views are disposable — otherwise you'll quietly lose them.

Canonical rebuild pattern (this is exactly how `sources` and `molecules` were cleaned up in migrations 0007 / 0008):
```sql
BEGIN;
DROP VIEW IF EXISTS v_mvl_gaps;
ALTER TABLE molecules DROP COLUMN IF EXISTS aliases;
CREATE VIEW v_mvl_gaps AS
 SELECT ...            -- original definition, minus the clause that referenced `aliases`
 FROM meaty_volatile_library mvl
 WHERE NOT (EXISTS (SELECT 1 FROM molecules m WHERE lower(m.name) = lower(mvl.compound)));
COMMIT;
```

---

## Migration file convention

Every applied change is captured as a **forward-only, numbered SQL file** in `meatCODE/db/migrations/`, so the schema history is reconstructable and other agents stay in sync. Do not renumber or edit already-applied migrations — always add the next number.

- Filename: `NNNN_short_description.sql` (e.g. `0009_add_molecule_source_link.sql`). Use the next unused number.
- Wrap the body in `BEGIN; … COMMIT;`.
- Open with a header comment: **what** changed, **why** it's safe (the two checks), and **when** it was applied to Neon.

Template:
```sql
-- =============================================================================
-- NNNN — <what changed> (<who asked / why>).
-- <Data-safety note: e.g. "col was 0/799 non-null">.
-- <Structural-safety note: e.g. "referenced only by dead branch of v_x; rebuilt">.
-- Applied to Neon: <YYYY-MM-DD>.
-- =============================================================================
BEGIN;
<statements>
COMMIT;
```

---

## Apply live + verify

Run the migration through the psycopg2 connection, then **verify inside the same script** before trusting it:

```python
cur.execute(open("meatCODE/db/migrations/NNNN_....sql").read())
conn.commit()

# verify: column gone, rows intact, dependent views still queryable
cur.execute("SELECT count(*) FROM information_schema.columns "
            "WHERE table_name='molecules' AND column_name='aliases'")
assert cur.fetchone()[0] == 0, "column still present"
cur.execute("SELECT count(*) FROM molecules"); print("rows:", cur.fetchone()[0])
for v in ("v_mvl_gaps", "v_mvl_x_molecules_fuzzy"):
    cur.execute(f"SELECT count(*) FROM {v}"); print(v, "ok:", cur.fetchone()[0])
```

A good verification confirms three things: the structural change happened, the **row count is unchanged** (you changed shape, not data), and every rebuilt/dependent view still returns rows.

---

## Log it

Append a short dated entry to `meatCODE/AGENT_UPDATE_LOG.md` so the shared brain stays current — what changed, why it was safe, and the verified result. One paragraph is enough. If the change alters project status, also update `PROJECT_STATE.md`. (Pushing to GitHub is Lior's step via the sync command; agents don't run git here.)

---

## Teach-the-user mode (always include in apply-and-teach)

After making the change, give Lior the self-service recipe so he owns it:

1. **Where to run it:** Neon SQL Editor (console.neon.tech) or TablePlus / Postico connected with `DATABASE_URL`.
2. **Confirm empty:** `SELECT count(col) FROM table;` — `0` means safe to drop (count ignores NULLs).
3. **Check dependents:** the `information_schema.view_column_usage` query above.
4. **Drop inside a transaction:** `BEGIN; ALTER TABLE … DROP COLUMN …; COMMIT;` — and if it errors with *"other objects depend on it,"* either rebuild the view without the column (safe) or `DROP COLUMN … CASCADE` (also drops the view — only if disposable).

The one rule to leave him with: **`count(col)=0` tells you the data is safe to lose; the dependency check tells you the structure will let go. Check both, and keep it inside `BEGIN…COMMIT` so a surprise is a `ROLLBACK`.**

---

## Safety rules

- Never drop a column/table whose data check isn't `0` without an explicit user OK.
- Always transaction-wrap DDL; only `COMMIT` after in-transaction verification looks right.
- Prefer rebuilding a dependent view over `CASCADE`.
- Never test this skill by running destructive DDL against real tables — use a throwaway scratch table if you need to prove the workflow.
- Renames are not free: update every code/view reference in the same change.
