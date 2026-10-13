import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_digest  # noqa: E402

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def post(slug, section, hours_ago=1, image=True, tags=(), featured=False):
    return {
        "slug": slug,
        "title": slug,
        "url": f"https://tuhoy.com/{slug}/",
        "published_at": (NOW - timedelta(hours=hours_ago)).isoformat(),
        "feature_image": "https://tuhoy.com/img.jpg" if image else None,
        "featured": featured,
        "tags": [{"name": section.capitalize(), "slug": section}] + [{"name": t, "slug": t} for t in tags],
    }


class PickPostsTest(unittest.TestCase):
    def test_mezcla_secciones_con_inmigracion_primero(self):
        posts = [post(f"inm{i}", "inmigracion", i + 1) for i in range(5)] + [
            post("mundo1", "mundo", 2), post("salud1", "salud", 3)]
        picked = [p["slug"] for p in daily_digest.pick_posts(posts, NOW, 6)]
        self.assertEqual(picked[0], "inm0")
        self.assertIn("mundo1", picked)
        self.assertIn("salud1", picked)
        self.assertEqual(sum(s.startswith("inm") for s in picked), 3)

    def test_descarta_viejas_sin_foto_y_internas(self):
        posts = [
            post("vieja", "mundo", hours_ago=30),
            post("sinfoto", "mundo", image=False),
            post("auto", "mundo", tags=("#resumen-automatico",)),
            post("buena", "mundo"),
        ]
        self.assertEqual([p["slug"] for p in daily_digest.pick_posts(posts, NOW, 6)], ["buena"])

    def test_html_lleva_enlaces_y_pie(self):
        body = daily_digest.build_html([post("a", "mundo"), post("b", "salud")], NOW)
        self.assertIn('href="https://tuhoy.com/a/"', body)
        self.assertEqual(body.count("<img"), 1)
        self.assertIn("Suscríbete gratis", body)


if __name__ == "__main__":
    unittest.main()
