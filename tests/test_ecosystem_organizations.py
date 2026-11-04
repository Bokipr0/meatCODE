import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import ecosystem_organizations as orgs


class OrganizationSearchTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'id':i,'name':'Organization '+str(i),'org_type':kind,'country':country,
                    'website':'example.org','description':'Develops savoury aroma for plant-based meat.'}
                   for i,kind,country in [(1,'company','Germany'),(2,'company','United States'),(3,'ngo_gov','Germany'),(4,'company','France')]]

    def search(self,text,**kwargs):
        def model(prompt):
            self.assertIn('DIRECTORY DATA',prompt)
            return json.dumps({'intent':'explore','topics':[],'sector':'academic','region':'any',
                               'matches':[{'id':i,'evidence':'savoury aroma for plant-based meat'} for i in [2,3,1,4,999]], **kwargs.pop('model',{})})
        return orgs.read_request({'text':text,**kwargs},lambda sql,args:self.rows,model)

    def test_companies_override_wrong_academic_reading_and_honor_count_geography(self):
        result=self.search('List 1 companies for plant-based meat aroma in Europe')
        self.assertEqual(result['sector'],'industry')
        self.assertEqual([r['id'] for r in result['organizations']],[1])

    def test_ngo_country_is_enforced(self):
        result=self.search('NGOs for aroma in Germany')
        self.assertEqual([r['id'] for r in result['organizations']],[3])

    def test_unfounded_matches_are_rejected(self):
        result=self.search('Companies for aroma',model={'matches':[{'id':1,'evidence':'Invented expertise'},{'id':999,'evidence':'savoury aroma for plant-based meat'}]})
        self.assertEqual(result['organizations'],[])

    def test_control_filters_override_original_query(self):
        result=self.search('Companies for aroma in Germany',filters={'entity':'organizations','country':'FR','region':'europe','sector':'industry'})
        self.assertEqual([r['id'] for r in result['organizations']],[4])

    def test_refinement_keeps_subject_and_organization_mode(self):
        result=self.search('Only Europe',prev={'entity':'organizations','query':'Companies for aroma','sector':'industry','limit':1})
        self.assertEqual(result['query'],'Companies for aroma')
        self.assertEqual(len(result['organizations']),1)

    def test_activity_filter_does_not_invent_activity_dates(self):
        result=self.search('Companies for aroma',model={'since':2025})
        self.assertEqual(result['organizations'],[])

    def test_people_request_remains_people(self):
        result=orgs.read_request({'text':'Find industry researchers'},lambda *_:self.fail('unneeded directory read'),lambda _:json.dumps({'intent':'collaborate','topics':[],'sector':'industry','region':'any'}))
        self.assertEqual(result['entity'],'people')

    def test_unsafe_websites_not_exposed(self):
        self.assertIsNone(orgs.website('javascript:alert(1)'))
        self.assertEqual(orgs.website('example.org'),'https://example.org')

if __name__=='__main__':unittest.main()
