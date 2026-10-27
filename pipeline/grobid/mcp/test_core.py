# Last updated: 2026-10-20 · Codex / Full-Stack · path and scientific-body regression checks.
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import core


class CoreTests(unittest.TestCase):
    def test_paths_are_relative_pdf_only_and_symlinks_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root / 'ok.pdf').write_bytes(b'%PDF-1.4\nexample')
            outside = Path(external) / 'outside.pdf'
            outside.write_bytes(b'%PDF-1.4\nexample')
            (root / 'escape.pdf').symlink_to(outside)
            with patch.dict(os.environ, {'PDF_ROOT': directory}):
                self.assertEqual(core.resolve_pdf('ok.pdf'), root.resolve()/'ok.pdf')
                for bad in ('../outside.pdf', str(outside), 'escape.pdf'):
                    with self.assertRaises(ValueError): core.resolve_pdf(bad)

    def test_invalid_pdf_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'bad.pdf').write_text('not a PDF')
            with patch.dict(os.environ, {'PDF_ROOT': directory}):
                with self.assertRaises(ValueError): core.resolve_pdf('bad.pdf')

    def test_bibliography_and_header_are_excluded_from_body(self):
        xml=b'''<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><p>private header</p></teiHeader>
        <text><body><div><head>Results</head><p>Protein <ref>1</ref> binds aroma.</p></div></body>
        <back><listBibl><biblStruct><title>Reference title</title></biblStruct></listBibl></back></text></TEI>'''
        _, text=core.scientific_body(xml)
        self.assertIn('Protein 1 binds aroma.', text)
        self.assertNotIn('Reference title', text)
        self.assertNotIn('private header', text)
        self.assertNotIn('<', text)


if __name__=='__main__': unittest.main()
