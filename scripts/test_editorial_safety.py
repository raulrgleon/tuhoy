from contextlib import ExitStack
import unittest
from unittest.mock import Mock, patch

import daily_edition as daily


class EditorialSafetyTests(unittest.TestCase):
    def submit(self, flagged, source_title="Una noticia importante de la comunidad"):
        # Explicit title parameter exercises sensitive-news gating.
        item = {"title": source_title, "url": "https://example.com/news/", "desc": "Contexto real " * 60}
        state = {"seen_titles": [], "seen_urls": []}
        ghost = Mock()
        ghost.upload_image.return_value = "https://tuhoy.com/content/images/photo.jpg"
        ghost.post_json.return_value = (201, {"posts": [{"slug": "noticia"}]})
        with ExitStack() as stack:
            for name, value in {
                "headline_es": source_title, "resolve_article_url": item["url"],
                "extract_article": "Información real " * 80, "classify": ["Mundo"],
                "source_photo": (b"image", "photo.jpg", "image/jpeg", "Foto de la fuente"),
            }.items():
                stack.enter_context(patch.object(daily, name, return_value=value))
            stack.enter_context(patch.object(daily, "DRY_RUN", False))
            stack.enter_context(patch.object(daily, "log"))
            stack.enter_context(patch.object(daily, "record_image"))
            stack.enter_context(patch.object(daily.writer, "enabled", return_value=True))
            stack.enter_context(patch.object(daily.writer, "write_article", return_value={
                "headline": source_title, "html": "<p>Texto de la noticia</p>", "deck": "Entradilla", "flagged": flagged,
            }))
            review = stack.enter_context(patch.object(daily.writer, "queue_for_review"))
            result = daily.publish_item(ghost, item, False, [], state)
            status = ghost.post_json.call_args.args[1]["posts"][0]["status"]
            return result, status, state, review.called

    def test_flagged_story_is_a_draft_and_not_counted_as_published(self):
        result, status, state, queued = self.submit(True)
        self.assertFalse(result)
        self.assertEqual(status, "draft")
        self.assertTrue(queued)
        self.assertTrue(state["seen_urls"], "held stories must not be regenerated at each edition")

    def test_sensitive_unflagged_story_is_held(self):
        result, status, _, queued = self.submit(False, "ICE detiene a una familia")
        self.assertFalse(result)
        self.assertEqual(status, "draft")
        self.assertTrue(queued)

    def test_unflagged_story_still_publishes(self):
        result, status, _, queued = self.submit(False)
        self.assertTrue(result)
        self.assertEqual(status, "published")
        self.assertFalse(queued)

    def test_held_stories_consume_edition_quota(self):
        state = {"seen_urls": [], "seen_titles": [], "runs": []}
        def hold(ghost,item,*args,**kwargs):
            state["seen_urls"].append(item["url"])
            return False
        items=[{"url":f"https://example.com/{i}","title":"Nota comunitaria"} for i in range(20)]
        with ExitStack() as stack:
            for name,value in {"load_env":{"GHOST_URL":"https://tuhoy.com","GHOST_ADMIN_API_KEY":"test"},"Ghost":Mock(),"load_state":state,"existing_titles":[],"collect":items,"ensure_tags":None,"save_state":None,"log":None}.items():
                stack.enter_context(patch.object(daily,name,return_value=value))
            stack.enter_context(patch.object(daily,"PAGINAS_INMIGRACION",[]))
            stack.enter_context(patch.object(daily,"DRY_RUN",False))
            submit=stack.enter_context(patch.object(daily,"publish_item",side_effect=hold))
            daily.run(max_general=2,max_inmig=2,max_paises=1)
            self.assertEqual(submit.call_count,5)

    def test_scheduled_edition_never_resets_editor_navigation(self):
        # Exercise an empty run, with all external work mocked.
        ghost = Mock()
        state = {"seen_urls": [], "seen_titles": [], "runs": []}
        with ExitStack() as stack:
            for name, value in {"load_env": {"GHOST_URL": "https://tuhoy.com", "GHOST_ADMIN_API_KEY": "test"}, "Ghost": ghost, "load_state": state, "existing_titles": [], "collect": [], "ensure_tags": None, "save_state": None, "log": None}.items():
                stack.enter_context(patch.object(daily, name, return_value=value))
            stack.enter_context(patch.object(daily, "PAGINAS_INMIGRACION", []))
            stack.enter_context(patch.object(daily, "DRY_RUN", False))
            navigation = stack.enter_context(patch.object(daily, "update_navigation"))
            daily.run()
            navigation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
