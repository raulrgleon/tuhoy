import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import whatsapp_channel as wa  # noqa: E402

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 14, 8, 0, tzinfo=TZ)


def item(i, hora, **extra):
    row = {
        "id": f"id{i}",
        "titulo": f"Nota {i}",
        "url": f"https://tuhoy.com/nota-{i}/",
        "texto": f"Texto de la nota {i}.",
        "hora": hora.isoformat(),
    }
    row.update(extra)
    return row


class WhatsAppChannelTest(unittest.TestCase):
    def test_elige_las_primeras_del_dia(self):
        q = {
            "pendientes": [
                item(1, NOW.replace(hour=6, minute=15)),
                item(2, NOW.replace(hour=7, minute=15)),
                item(3, NOW.replace(hour=8, minute=15)),
                item(4, NOW - timedelta(days=1)),
            ]
        }
        picked = [t["id"] for t in wa.pick_today(q, set(), NOW, 2)]
        self.assertEqual(picked, ["id1", "id2"])

    def test_omite_las_ya_enviadas(self):
        q = {"pendientes": [item(1, NOW.replace(hour=6, minute=15)), item(2, NOW.replace(hour=7, minute=15))]}
        picked = [t["id"] for t in wa.pick_today(q, {"id1"}, NOW, 2)]
        self.assertEqual(picked, ["id2"])

    def test_un_correo_por_dia(self):
        self.assertTrue(wa.ya_enviado_hoy([{"id": "x", "fecha": "2026-10-14"}], NOW))
        self.assertFalse(wa.ya_enviado_hoy([{"id": "x", "fecha": "2026-10-13"}], NOW))

    def test_pie_lleva_enlace(self):
        t = item(1, NOW)
        p = wa.pie(t)
        self.assertIn("Texto de la nota 1", p)
        self.assertIn("https://tuhoy.com/nota-1/", p)


if __name__ == "__main__":
    unittest.main()
