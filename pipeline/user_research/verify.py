# Last updated: 2026-10-28 15:51 UTC · Data/Backend · live rollback-only verification; no test rows committed.
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

from settings import ROOT, settings


def run(environment):
    conf=settings(environment)
    if not conf.get('DATABASE_URL'):
        raise RuntimeError('Research database is not configured.')
    os.environ['USER_RESEARCH_TEST_DB_URL']=conf['DATABASE_URL']
    spec=importlib.util.spec_from_file_location('test_user_research',ROOT/'tests/test_user_research.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    # Suppress full exception/SQL tracebacks so credentials/feedback never enter logs.
    result=unittest.TestResult();suite.run(result)
    import psycopg2
    conn=psycopg2.connect(conf['DATABASE_URL'],connect_timeout=5)
    try:
        with conn.cursor() as cur:
            counts={}
            for table in ('sessions','events','feedback','withdrawals','clarity_exports'):
                cur.execute('SELECT count(*) FROM user_research.'+table)
                counts[table]=cur.fetchone()[0]
        conn.rollback()
    finally:conn.close()
    return {'environment':environment,'tests':result.testsRun,'failures':len(result.failures),
            'errors':len(result.errors),'skipped':len(result.skipped),'retained_rows':counts,
            'ok':result.wasSuccessful()}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--environment',required=True,choices=('dev','prod'))
    args=parser.parse_args()
    try:
        report=run(args.environment);print(json.dumps(report));sys.exit(0 if report['ok'] else 1)
    except Exception as exc:
        print(json.dumps({'ok':False,'error_type':type(exc).__name__,'error_code':'rollback_verification_stopped'}));sys.exit(1)
