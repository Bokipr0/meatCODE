"""Generate an idempotent, insert-only import for the sourced organization collection."""
import json
from pathlib import Path


def statement(path):
    rows = json.loads(Path(path).read_text())
    if len(rows) < 70 or len({r['name'].casefold() for r in rows}) != len(rows):
        raise ValueError('Expected at least 70 unique organizations')
    values = []
    for row in rows:
        if row['org_type'] not in ('company', 'ngo_gov') or not row['source_url'].startswith('https://'):
            raise ValueError('Invalid organization type or provenance')
        fields = [row[key] for key in ('name','org_type','country','website','description')]
        values.append('(' + ','.join("'" + value.replace("'", "''") + "'" for value in fields) + ')')
    return '''WITH candidates(name,org_type,country,website,description) AS (VALUES
''' + ',\n'.join(values) + '''
), added AS (
 INSERT INTO public.organizations(name,org_type,country,website,description)
 SELECT c.name,c.org_type::expert_org_type,c.country,c.website,c.description FROM candidates c
 WHERE NOT EXISTS (SELECT 1 FROM public.organizations o WHERE lower(o.name)=lower(c.name))
 ON CONFLICT DO NOTHING
 RETURNING id,org_type
)
SELECT count(*) AS inserted, count(*) FILTER (WHERE org_type::text='company') AS companies,
 count(*) FILTER (WHERE org_type::text='ngo_gov') AS ngos FROM added'''


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    args=parser.parse_args()
    print(statement(args.input))
