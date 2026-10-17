import unittest
import tiktok_video as v
class EditorialVideoTests(unittest.TestCase):
    def test_scenes_are_complete_source_sentences(self):
        sentences=['Esta primera oración contiene siete palabras sobre la noticia publicada.','Esta segunda oración conserva los hechos exactos de la fuente original.','Esta tercera oración ofrece otro dato sin inventar nombres ni cifras.','Esta cuarta oración cierra el relato con información del artículo original.']
        scenes=v.build_scenes({'title':'Titular','html':''.join('<p>'+s+'</p>' for s in sentences)})
        self.assertEqual([s['text'] for s in scenes],sentences)
    def test_short_article_blocks_generation(self):
        with self.assertRaises(ValueError): v.build_scenes({'title':'Titular','html':'<p>Muy corto.</p>'})
    def test_foreign_and_non_https_images_are_blocked(self):
        for url in ['http://tuhoy.com/content/images/a.jpg','https://evil.test/a.jpg','https://tuhoy.com.evil.test/content/images/a.jpg','https://tuhoy.com/ghost/a.jpg']:
            with self.subTest(url=url),self.assertRaises(ValueError):v.safe_image(url)
    def test_invalid_id_is_blocked_before_api_or_filesystem(self):
        with self.assertRaises(ValueError):v.create_asset('../../secret')
if __name__=='__main__': unittest.main()
