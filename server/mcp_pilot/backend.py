"""Bounded scientific reads. Never imports the web server or calls a reasoning model."""
import os
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import dotenv_values

class Backend:
    def __init__(self, corpus_env=None, graph_env=None):
        self.corpus_url = self._url(corpus_env, 'MCP_DATABASE_URL')
        self.graph_url = self._url(graph_env, 'MCP_GRAPH_DATABASE_URL')

    @staticmethod
    def _url(path, key):
        if os.environ.get(key): return os.environ[key]
        if path: return dotenv_values(Path(path)).get('DATABASE_URL')
        return None

    @contextmanager
    def db(self, graph=False):
        url = self.graph_url if graph else self.corpus_url
        if not url: raise ValueError('Scientific data connection is not configured')
        try:
            conn = psycopg2.connect(url, connect_timeout=10)
            conn.set_session(readonly=True, autocommit=False)
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SET LOCAL statement_timeout = '5s'")
                    yield cur
            finally:
                conn.rollback(); conn.close()
        except psycopg2.Error:
            raise RuntimeError('Scientific retrieval is unavailable; check the private service configuration') from None

    @staticmethod
    def validate(query, limit):
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 1000:
            raise ValueError('Query must contain 1–1000 characters')
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
            raise ValueError('Limit must be an integer from 1 to 10')
        return query.strip()

    @staticmethod
    def source(row):
        row = dict(row)
        row['id'] = str(row['id'])
        doi = row.get('doi')
        if doi:
            row['url'] = 'https://doi.org/' + doi.removeprefix('https://doi.org/').removeprefix('http://doi.org/')
        elif urlparse(row.get('url') or '').scheme not in ('https','http'):
            row['url'] = 'https://meatcode-oracle.onrender.com/api/papers/' + str(row['id'])
        return row

    def search(self, query, limit=5):
        query = self.validate(query, limit)
        with self.db() as cur:
            cur.execute("""SELECT id,name AS title,year,doi,url,review_status::text AS review_status,
                ts_rank_cd(search_vec,websearch_to_tsquery('english',%s))::float AS rank
                FROM public.sources WHERE search_vec @@ websearch_to_tsquery('english',%s)
                ORDER BY rank DESC,id LIMIT %s""",(query,query,limit))
            rows = cur.fetchall()
            fallback = False
            if not rows:
                terms = ' OR '.join(query.split()[:24]); fallback = True
                cur.execute("""SELECT id,name AS title,year,doi,url,review_status::text AS review_status,
                    ts_rank_cd(search_vec,websearch_to_tsquery('english',%s))::float AS rank
                    FROM public.sources WHERE search_vec @@ websearch_to_tsquery('english',%s)
                    ORDER BY rank DESC,id LIMIT %s""",(terms,terms,limit))
                rows = cur.fetchall()
        return {'results':[self.source(r) for r in rows], 'mode':'postgres_fts',
                'or_fallback':fallback,'relevance_threshold':None,
                'notice':'Bibliographic matches, not validated scientific conclusions. Rank is lexical, not confidence. Use fetch for source summaries.'}

    def fetch(self, id):
        if not isinstance(id,str) or not id.isascii() or not id.isdecimal() or len(id)>10:
            raise ValueError('Use a numeric source id returned by search')
        with self.db() as cur:
            cur.execute("""SELECT id,name AS title,year,doi,url,review_status::text AS review_status,
                main_claim,tailored_abstract,top_keywords FROM public.sources WHERE id=%s""",(int(id),))
            row=cur.fetchone()
        if not row: return {'status':'not_found','id':id}
        result=self.source(row)
        for key in ['main_claim','tailored_abstract','top_keywords']:
            if isinstance(result.get(key),str):result[key]=result[key][:4000]
        result['text']='\n\n'.join(str(result[k]) for k in ('main_claim','tailored_abstract') if result.get(k)) or 'No stored structured summary is available. Consult the cited paper.'
        result['notice']='Stored structured summaries; verify scientific claims against the cited paper. No raw full text, private notes or user chats are returned.'
        return result

    def graph_search(self, query, limit=5):
        query=self.validate(query,limit)
        from server import lightrag_retrieval
        def run(sql,args=()):
            with self.db(graph=True) as cur:
                cur.execute(sql,args);return [dict(r) for r in cur.fetchall()]
        result=lightrag_retrieval.search(query,run,limit=limit,use_vectors=False)
        # Bound descriptions and evidence fan-out at the client boundary.
        for item in result.get('items',[]):
            item['content']=item['content'][:1500]
            item['chunk_ids']=item.get('chunk_ids',[])[:20]
        result['notice']='Extracted three-paper demo; relationships are candidates, not human-validated scientific facts. Lexical seeds plus bounded one-hop graph expansion. Vectors are not used in this pilot.'
        result['items']=result.get('items',[])[:2*limit]
        return result
