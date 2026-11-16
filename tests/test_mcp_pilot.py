"""Boundary checks without network access or model calls."""
import unittest
from unittest.mock import patch
from server.mcp_pilot.backend import Backend

class MCPBoundaries(unittest.TestCase):
    def test_bad_queries_never_open_database(self):
        b=Backend()
        with patch.object(b,'db',side_effect=AssertionError('database should not open')):
            for query in ['', ' ', 'x'*1001]:
                with self.assertRaises(ValueError):b.search(query)
            for limit in [0,11,True,1.2]:
                with self.assertRaises(ValueError):b.graph_search('Maillard',limit)

    def test_bad_ids_never_open_database(self):
        b=Backend()
        with patch.object(b,'db',side_effect=AssertionError('database should not open')):
            for ident in ['../.env','1; SELECT password','１２','1'*11]:
                with self.assertRaises(ValueError):b.fetch(ident)

    def test_publisher_url_fallback(self):
        source=Backend.source({'id':1,'url':'javascript:alert(1)','doi':None})
        self.assertTrue(source['url'].startswith('https://meatcode-oracle.onrender.com/'))
        self.assertEqual(Backend.source({'id':2,'url':None,'doi':'10.1234/test'})['url'],'https://doi.org/10.1234/test')

    def test_explicit_lexical_graph_does_not_embed(self):
        from server import lightrag_retrieval as graph
        def run(sql,args=()):
            if 'to_regclass' in sql:return [{'installed':True}]
            if 'FROM lightrag_demo.batches' in sql:return [{'batch_id':'test','created_at':None,'embedding_model':'test','embedding_dimension':1024,'manifest':{'expected_counts':{}},'review_state':'extracted_demo'}]
            return []
        with patch.object(graph,'embedding',side_effect=AssertionError('No model call')):
            result=graph.search('Maillard cysteine',run,use_vectors=False)
        self.assertEqual(result['mode'],'lexical_graph')
        self.assertEqual(result['embedding_issue'],'not_requested')
        self.assertEqual(result['items'],[])

if __name__=='__main__':unittest.main()
