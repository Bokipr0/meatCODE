import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
from ecosystem_inbox import TABS, reviewed_inbox


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.tabs = {}
        for name, (_, fields) in TABS.items():
            headers = ['ID','Status','Name / title','Link','Reviewer notes','Public contact',*fields]
            self.tabs[name] = [headers, ['item-'+name.replace(' & ', '-'),'Approved','Example','javascript:alert(1)','private note','test@example.org']]

    def test_only_reviewed_and_public_fields_across_all_tabs(self):
        self.tabs['Experts'][1][1] = 'Merged'
        self.tabs['Events'].append(['declined','Declined','Hidden'])
        self.tabs['Courses'][1][self.tabs['Courses'][0].index('Status')] = 'On hold'
        result = reviewed_inbox(self.tabs)
        self.assertEqual([len(rows) for rows in result.values()], [1,1,0,1,1])
        self.assertEqual(result['events'][0]['link'], '')
        for private in ('private note','test@example.org','Hidden','javascript:'):
            self.assertNotIn(private, repr(result))
        self.assertNotIn('score', result['experts'][0])
        self.tabs['Experts'][1][1] = 'Declined'
        self.assertEqual(reviewed_inbox(self.tabs)['experts'], [])

    def test_incomplete_or_invalid_editions_rejected(self):
        self.tabs['Events'][1][0] = '" unsafe-id'
        with self.assertRaises(ValueError): reviewed_inbox(self.tabs)
        del self.tabs['Experts']
        with self.assertRaises(KeyError): reviewed_inbox(self.tabs)
