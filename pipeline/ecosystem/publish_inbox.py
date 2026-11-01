"""Prepare one atomic publication from a private, complete Google Sheets range export.

Input JSON: workbook_id, modified_at (Drive timestamp with timezone), tabs (title -> rows).
--sql produces one safe statement for the authenticated Neon connector. Default: counts only.
"""
import argparse
import base64
import datetime as dt
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'server'))
from ecosystem_inbox import TABS, reviewed_inbox


def prepare(document):
    key = document['workbook_id']
    if not re.fullmatch(r'[A-Za-z0-9_-]{10,128}', key):
        raise ValueError('Invalid workbook identifier')
    version = dt.datetime.fromisoformat(document['modified_at'].replace('Z', '+00:00'))
    if version.utcoffset() is None:
        raise ValueError('Drive timestamp must have a timezone')
    inbox = reviewed_inbox(document['tabs'])
    for tab, (section, _) in TABS.items():
        expected = sorted(tuple(pair) for pair in document['expected_reviewed'][tab])
        actual = sorted((row['id'], row['status']) for row in inbox[section])
        if actual != expected:
            raise ValueError('Incomplete or changed sheet range: ' + tab)
    encoded = base64.b64encode(json.dumps(inbox, ensure_ascii=False, allow_nan=False,
                                         separators=(',', ':')).encode()).decode('ascii')
    # Only constrained identifiers, an ISO timestamp and base64 appear in SQL.
    # Reject a different workbook, stale exports or a conflicting same-version payload.
    sql = f"""INSERT INTO ecosystem_module.inbox_snapshot AS prev(singleton, workbook_id, checked_at, inbox)
VALUES(true, '{key}', '{version.isoformat()}', convert_from(decode('{encoded}','base64'),'UTF8')::jsonb)
ON CONFLICT(singleton) DO UPDATE SET checked_at=excluded.checked_at, inbox=excluded.inbox
WHERE prev.workbook_id=excluded.workbook_id AND prev.checked_at < excluded.checked_at
RETURNING checked_at"""
    return inbox, sql


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--sql', action='store_true')
    args = parser.parse_args()
    inbox, statement = prepare(json.loads(args.input.read_text()))
    print(statement if args.sql else json.dumps({k:len(v) for k,v in inbox.items()}))
