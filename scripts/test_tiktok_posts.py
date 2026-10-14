import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiktok_posts as tt  # noqa: E402

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 14, 10, 0, tzinfo=TZ)


def item(i, minutes=0, **extra):
    hora = (NOW - timedelta(minutes=minutes)).isoformat()
    row = {
        "id": f"id{i}",
        "titulo": f"Nota {i}",
        "url": f"https://tuhoy.com/nota-{i}/",
        "hora": hora,
        "texto": f"Texto de la nota {i}. #ICE",
    }
    row.update(extra)
    return row


class TikTokPostsTest(unittest.TestCase):
    def test_due_mismo_criterio_que_instagram(self):
        q = {
            "pendientes": [
                item(1, minutes=-30),
                item(2, minutes=5),
                item(3, minutes=200),
                item(4, minutes=10),
            ]
        }
        due = [t["id"] for t in tt.due_posts(q, {"id4"}, NOW)]
        self.assertEqual(due, ["id2"])

    def test_titulo_cabe_en_90(self):
        t = item(1, titulo="A" * 200)
        self.assertLessEqual(tt.utf16_len(tt.title_of(t)), 90)

    def test_descripcion_lleva_enlace(self):
        t = item(1)
        d = tt.description_of(t)
        self.assertIn("https://tuhoy.com/nota-1/", d)
        self.assertIn("Texto de la nota 1", d)

    def test_privacidad_publica_si_existe(self):
        self.assertEqual(
            tt.privacy_of(["SELF_ONLY", "PUBLIC_TO_EVERYONE"]),
            "PUBLIC_TO_EVERYONE",
        )
        self.assertEqual(tt.privacy_of(["FOLLOWER_OF_CREATOR"]), "FOLLOWER_OF_CREATOR")


if __name__ == "__main__":
    unittest.main()
