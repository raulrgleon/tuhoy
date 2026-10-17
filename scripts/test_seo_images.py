import unittest
import daily_edition as d
class SourceImageSelection(unittest.TestCase):
    def test_only_declared_same_image_large_variants(self):
        raw='<img srcset="https://cdn.test/news-640x480.jpg 640w, https://cdn.test/news-1600x1000.jpg 1600w, https://cdn.test/unrelated.jpg 2000w">'
        self.assertEqual(d.large_photo_candidates(raw,'https://publisher.test/story','https://cdn.test/news-960x640.jpg'),['https://cdn.test/news-1600x1000.jpg'])
    def test_no_guessed_or_insecure_candidates(self):
        self.assertEqual(d.large_photo_candidates('<img srcset="http://cdn.test/news.jpg 1600w">','https://publisher.test/story','https://cdn.test/news.jpg'),[])
    def test_deduplicates_and_bounds_candidates(self):
        raw='<img srcset="'+','.join(f'https://cdn.test/news.jpg?w={n} {n}w' for n in [1200,1300,1400,1500,1500])+'">'
        c=d.large_photo_candidates(raw,'https://publisher.test/story','https://cdn.test/news.jpg?w=960');self.assertEqual(len(c),3);self.assertTrue(c[0].endswith('1500'))
if __name__=='__main__':unittest.main()
