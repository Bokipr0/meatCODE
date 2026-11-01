"""Publish complete, human-reviewed editions of the private Ecosystem inbox."""
import datetime as dt
import math
import re
from urllib.parse import urlsplit

TABS = {
    'Experts': ('experts', ('Affiliation', 'Role', 'Country', 'Expertise', 'Profile URL')),
    'Events': ('events', ('Organiser', 'Start date', 'End date', 'Location / online', 'CFP deadline', 'Registration deadline', 'Cost')),
    'Courses': ('courses', ('Provider', 'Level', 'Format', 'Duration', 'Cost', 'Language', 'Next start')),
    'News & Articles': ('news', ('Type', 'Publication', 'Published date', 'Authors', 'DOI', 'Summary')),
    'Ecosystem': ('eco', ('Type', 'Segment', 'Country', 'Website', 'Recent activity')),
}
DATE_FIELDS = {'Start date', 'End date', 'CFP deadline', 'Registration deadline', 'Next start', 'Published date'}
EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')
URL = re.compile(r'https?://[^\s)<>";]+')


def text(value):
    return EMAIL.sub('', str(value if value is not None else '')).strip()


def public_url(value):
    value = str(value or '').strip()
    if not URL.fullmatch(value) or EMAIL.search(value):
        return ''
    try:
        parsed = urlsplit(value)
        return value if parsed.hostname and not parsed.username and not parsed.password else ''
    except ValueError:
        return ''


def field_value(key, value):
    if key in ('Website', 'Profile URL'):
        url = public_url(value)
        if key == 'Profile URL' and re.search(r'(?:linkedin\.com|researchgate\.net)', url, re.I):
            return ''
        return url
    if key in DATE_FIELDS and isinstance(value, (int, float)) and 1 <= value <= 2958465:
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(value))).isoformat()
    return text(value)


def reviewed_inbox(tables):
    """Replace all five sections together. Only explicitly approved fields leave here."""
    result, seen = {}, set()
    for title, (section, fields) in TABS.items():
        rows = tables[title]
        header = rows[0] if rows else []
        required = {'ID', 'Status', 'Name / title', 'Link', *fields}
        named_headers = [name for name in header if name]
        if not required.issubset(named_headers) or len(named_headers) != len(set(named_headers)):
            raise ValueError('Incomplete or ambiguous headers in ' + title)
        output = result[section] = []
        for values in rows[1:]:
            row = dict(zip(header, values))
            status = text(row.get('Status'))
            if status not in ('Approved', 'Merged'):
                continue
            key, name = text(row.get('ID')), text(row.get('Name / title'))
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,159}', key) or key in seen or not name:
                raise ValueError('Missing or duplicate identity in ' + title)
            seen.add(key)
            facts = {f: field_value(f, row.get(f)) for f in fields}
            record = dict(id=key, name=name, status=status, f={k:v for k,v in facts.items() if v})
            if section != 'experts':
                try:
                    score = float(row.get('Score') or 0)
                except (TypeError, ValueError):
                    score = 0
                evidence = URL.findall(str(row.get('Evidence (per criterion, with links)') or ''))
                record.update(link=public_url(row.get('Link')), why=text(row.get('Why it matters')),
                              evidence=' '.join(dict.fromkeys(u for u in evidence if public_url(u))),
                              tier=row.get('Tier') if row.get('Tier') in ('P0','P1','P2','P3') else '',
                              score=score if math.isfinite(score) else 0)
            output.append(record)
    return result


def current(pg_rows):
    rows = pg_rows("SELECT checked_at, inbox FROM ecosystem_module.inbox_snapshot WHERE singleton")
    if not rows:
        raise RuntimeError('Ecosystem inbox is not initialized')
    row = rows[0]
    return {'inbox':row['inbox'], 'checked_at':row['checked_at'].isoformat()}
