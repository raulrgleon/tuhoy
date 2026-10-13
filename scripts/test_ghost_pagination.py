import unittest
from urllib.parse import parse_qs, urlsplit

from scripts import daily_edition as daily


class GhostPaginationTests(unittest.TestCase):
    def test_limit_all_fetches_every_page_and_preserves_filters(self):
        ghost = daily.Ghost("https://example.test", "unused")
        responses = [
            (200, {"posts": [{"id": "1"}, {"id": "2"}], "meta": {"pagination": {"page": 1, "pages": 2, "total": 3}}}),
            (200, {"posts": [{"id": "3"}], "meta": {"pagination": {"page": 2, "pages": 2, "total": 3}}}),
        ]
        requests = []

        def fake_request(method, path, data=None, content_type="application/json"):
            requests.append((method, path))
            return responses.pop(0)

        ghost._req = fake_request
        status, result = ghost.get("/posts/?limit=all&formats=html&include=tags")

        self.assertEqual(status, 200)
        self.assertEqual([post["id"] for post in result["posts"]], ["1", "2", "3"])
        self.assertEqual(len(requests), 2)
        for page, (method, path) in enumerate(requests, start=1):
            query = parse_qs(urlsplit(path).query)
            self.assertEqual(method, "GET")
            self.assertEqual(query["limit"], ["100"])
            self.assertEqual(query["page"], [str(page)])
            self.assertEqual(query["formats"], ["html"])
            self.assertEqual(query["include"], ["tags"])

    def test_non_limit_all_requests_keep_existing_behavior(self):
        ghost = daily.Ghost("https://example.test", "unused")
        expected = (200, {"posts": []})
        calls = []
        ghost._req = lambda method, path, data=None, content_type="application/json": calls.append((method, path)) or expected

        self.assertEqual(ghost.get("/posts/?limit=10&page=2"), expected)
        self.assertEqual(calls, [("GET", "/posts/?limit=10&page=2")])

    def test_page_failure_is_not_silently_returned_as_partial_success(self):
        ghost = daily.Ghost("https://example.test", "unused")
        responses = [
            (200, {"posts": [{"id": "1"}], "meta": {"pagination": {"pages": 2}}}),
            (503, {"errors": [{"message": "unavailable"}]}),
        ]
        ghost._req = lambda *args, **kwargs: responses.pop(0)

        status, result = ghost.get("/posts/?limit=all")
        self.assertEqual(status, 503)
        self.assertIn("errors", result)


if __name__ == "__main__":
    unittest.main()
