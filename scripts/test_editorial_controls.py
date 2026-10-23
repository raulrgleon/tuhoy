import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import editorial_controls as controls
import daily_edition as daily
import writer

class ControlsTests(unittest.TestCase):
    def test_lock_excludes_concurrent_run_and_recovers_after_release(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'edition.lock'
            with controls.edition_lock(p) as a:
                self.assertTrue(a)
                with controls.edition_lock(p) as b:
                    self.assertFalse(b)
            with controls.edition_lock(p) as c:
                self.assertTrue(c)

    def test_sensitive_news_require_human_review(self):
        for title in ['ICE detiene a una familia', 'Cambia la ley de inmigración', 'Muere un actor', 'Elecciones en Brasil', 'Nuevas vacunas']:
            self.assertTrue(controls.review_reasons(title, ''))
        self.assertFalse(controls.review_reasons('Abre una biblioteca comunitaria', 'Un espacio de lectura'))

    def test_unlicensed_source_is_not_downloaded(self):
        with patch.object(daily, 'ROOT', Path('/nonexistent')), patch.object(daily, 'http_get') as get:
            self.assertIsNone(daily.source_photo('https://news.example/story', '<meta property="og:image" content="https://news.example/photo.jpg">'))
            get.assert_not_called()

    def test_explicit_image_permission_requires_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'permissions.json';url='https://example.com/a.jpg'
            p.write_text(json.dumps({url:{'authorized':True,'license':'Written permission','credit':'Author','evidence':'https://example.com/permission'}}))
            self.assertIsNotNone(controls.licensed_source(url,p))
            self.assertIsNone(controls.licensed_source('https://example.com/other.jpg',p))
            p.write_text('bad json');self.assertIsNone(controls.licensed_source(url,p))

    def test_commons_unknown_or_restricted_license_is_rejected(self):
        for value in ['', 'CC BY-NC 4.0', 'CC BY-ND 4.0', 'Some CC license']:
            self.assertFalse(controls.commons_license(value,'https://creativecommons.org'))
        for value in ['CC BY-SA 4.0','CC BY 3.0','CC0','Public domain']:
            self.assertTrue(controls.commons_license(value,'https://creativecommons.org'))
        self.assertFalse(controls.commons_license('CC BY 4.0','javascript:alert(1)'))

    def test_factcheck_missing_or_malformed_claims_fails_closed(self):
        for result in [{}, {'unsupported':{}}, {'unsupported':[{}]}, {'unsupported':['claim']}]:
            with patch.object(writer,'read_prompt',return_value='text'),patch.object(writer,'chat',return_value=json.dumps(result)):
                with self.assertRaises(writer.WriterError):writer.factcheck_pass({},[],{})
        with patch.object(writer,'read_prompt',return_value='text'),patch.object(writer,'chat',return_value='{"unsupported":[]}'):
            self.assertEqual(writer.factcheck_pass({},[],{}),[])

    def test_provenance_written_private(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'images.jsonl';controls.record_image(p,{'image':'public-url'})
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
            self.assertEqual(json.loads(p.read_text()),{'image':'public-url'})

    def test_illustration_is_labeled_and_valid(self):
        graphic=daily.editorial_graphic('Una noticia con título en español')
        if graphic is None:self.skipTest('Pillow not installed locally; checked on production runtime')
        self.assertTrue(graphic[0].startswith(b'\x89PNG'))
        self.assertIn('no es una fotografía',graphic[3])

if __name__=='__main__':unittest.main()
