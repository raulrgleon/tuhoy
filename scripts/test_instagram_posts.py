import io
import json
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instagram_posts as ig

NOW = datetime(2026, 10, 22, 7, 0, tzinfo=ig.TZ)
ENV = {'IG_USER_ID': 'account', 'FB_PAGE_ID': 'page', 'FB_PAGE_TOKEN': 'test-secret'}
ITEM = {'id': 'news', 'hora': (NOW-timedelta(minutes=10)).isoformat(),
        'url': 'https://tuhoy.com/news/', 'texto': 'Public news'}
MEDIA = {'id': 'published-id', 'timestamp': NOW.isoformat(),
         'caption': ig.caption(ITEM), 'permalink': 'https://www.instagram.com/p/test/'}
QUOTA = {'data': [{'quota_usage': 0, 'config': {'quota_total': 100}}]}


class InstagramTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state_path = Path(self.tmp.name)/'ig_queue.json'
        self.patchers = [patch.object(ig, 'IG_QUEUE', self.state_path), patch.object(ig, 'log')]
        for p in self.patchers:
            p.start(); self.addCleanup(p.stop)
        self.state = {'historial': []}

    def run_worker(self, **kwargs):
        return ig.run(ENV, self.state, {'pendientes': [ITEM]}, NOW, **kwargs)

    def test_error_but_post_exists_is_confirmed_once(self):
        def api(method, path, token, fields):
            if path.endswith('content_publishing_limit'): return QUOTA
            if method == 'POST' and path.endswith('/media'): return {'id': 'container'}
            if method == 'GET' and path == 'container': return {'status_code': 'FINISHED'}
            raise ig.GraphError(403, 4, 2207051)
        with patch.object(ig, 'recent_media', side_effect=[[], [MEDIA]]), patch.object(ig, 'graph', side_effect=api) as api_mock, patch.object(ig, 'feature_image', return_value='https://tuhoy.com/photo.jpg'):
            self.assertEqual(self.run_worker(), 0)
            self.assertEqual(self.state['historial'][0]['ig_id'], MEDIA['id'])
            self.assertNotIn('pending', self.state)
            self.assertNotIn('cooldown_until', self.state)
            self.assertEqual(sum(c.args[0] == 'POST' for c in api_mock.call_args_list), 2)
        self.assertNotIn('test-secret', self.state_path.read_text())

    def test_uncertain_publish_survives_restart_and_never_resends(self):
        with patch.object(ig, 'recent_media', side_effect=[[], []]), patch.object(ig, 'graph', return_value=QUOTA), patch.object(ig, 'feature_image', return_value='image'), patch.object(ig, 'publish', side_effect=RuntimeError('uncertain')):
            self.assertEqual(self.run_worker(), 1)
        self.state = json.loads(self.state_path.read_text())
        with patch.object(ig, 'recent_media', return_value=[]), patch.object(ig, 'graph') as api, patch.object(ig, 'publish') as publish:
            self.assertEqual(self.run_worker(), 0)
            api.assert_not_called(); publish.assert_not_called()
        self.assertIn(ITEM["id"], self.state["isolated"])

    def test_uncertain_old_post_does_not_block_a_different_article(self):
        other=dict(ITEM,id='next',url='https://tuhoy.com/next/')
        self.state['pending']={'item':ITEM,'stage':'publishing'}
        with patch.object(ig,'recent_media',return_value=[]),patch.object(ig,'graph',return_value=QUOTA),patch.object(ig,'feature_image',return_value='image'),patch.object(ig,'publish',return_value='new-post') as publish:
            self.assertEqual(ig.run(ENV,self.state,{'pendientes':[ITEM,other]},NOW),0)
            self.assertIn(ITEM['id'],self.state['isolated'])
            self.assertEqual(self.state['historial'][0]['id'],'next')
            self.assertEqual(publish.call_count,1)

    def test_delayed_confirmation_after_restart(self):
        self.state['pending'] = {'item': ITEM, 'stage': 'publishing'}
        with patch.object(ig, 'recent_media', return_value=[MEDIA]), patch.object(ig, 'publish') as publish:
            self.assertEqual(self.run_worker(), 0)
            publish.assert_not_called()
        self.assertEqual(len(self.state['historial']), 1)

    def test_preflight_deduplicates_without_writes(self):
        with patch.object(ig, 'recent_media', return_value=[MEDIA, dict(MEDIA, id='copy')]), patch.object(ig, 'graph') as api:
            self.assertEqual(self.run_worker(), 0); api.assert_not_called()
        self.assertEqual(self.state['historial'][0]['duplicate_count'], 1)

    def test_global_cooldown_does_not_hide_confirmed_media(self):
        self.state['cooldown_until'] = (NOW+timedelta(hours=24)).isoformat()
        with patch.object(ig,'recent_media',return_value=[MEDIA]),patch.object(ig,'graph') as api:
            self.assertEqual(self.run_worker(),0)
            api.assert_not_called()
        self.assertEqual(self.state['historial'][0]['ig_id'],MEDIA['id'])

    def test_quota_exhausted_does_not_create_container(self):
        with patch.object(ig, 'recent_media', return_value=[]), patch.object(ig, 'graph', return_value={'data':[{'quota_usage':100,'config':{'quota_total':100}}]}), patch.object(ig, 'publish') as publish:
            self.assertEqual(self.run_worker(), 0); publish.assert_not_called()
        self.assertIn('cooldown_until', self.state)

    def test_reconciliation_read_failure_prevents_post(self):
        with patch.object(ig, 'recent_media', side_effect=RuntimeError('unavailable')), patch.object(ig, 'publish') as publish:
            with self.assertRaises(RuntimeError): self.run_worker()
            publish.assert_not_called()

    def test_dry_run_has_no_requests_or_state_write(self):
        with patch.object(ig, 'graph') as api, patch.object(ig, 'recent_media') as recent, patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(self.run_worker(dry_run=True), 0); api.assert_not_called(); recent.assert_not_called()
        self.assertFalse(self.state_path.exists())

    def test_exact_url_and_time_not_substring_or_old_post(self):
        self.assertEqual(ig.find_existing(ITEM, [dict(MEDIA, caption=ITEM['url']+'other')]), [])
        self.assertEqual(ig.find_existing(ITEM, [dict(MEDIA, timestamp=(NOW-timedelta(days=1)).isoformat())]), [])

    def test_intent_and_container_persist_before_publish(self):
        self.state['pending']={'item':ITEM}
        def api(method, path, token, fields):
            saved=json.loads(self.state_path.read_text())['pending']
            if path.endswith('/media'):
                self.assertEqual(saved['stage'], 'creating'); return {'id':'container'}
            if path == 'container': return {'status_code':'FINISHED'}
            self.assertEqual(saved['stage'], 'publishing')
            self.assertEqual(saved['creation_id'], 'container')
            return {'id': 'published'}
        with patch.object(ig, 'graph', side_effect=api):
            self.assertEqual(ig.publish(ENV,'account','image','caption',self.state),'published')

    def test_transport_failure_redacts_token_and_url(self):
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('https://example/?access_token=test-secret')):
            with self.assertRaises(RuntimeError) as error: ig.graph('GET','account',ENV['FB_PAGE_TOKEN'])
        self.assertNotIn('test-secret', str(error.exception))
        self.assertNotIn('https://example', str(error.exception))

    def test_bearer_header_and_safe_error(self):
        err=urllib.error.HTTPError('url',403,'bad',{},io.BytesIO(json.dumps({'error':{'message':'test-secret','code':4,'error_subcode':2207051}}).encode()))
        with patch('urllib.request.urlopen', side_effect=err) as request:
            with self.assertRaises(ig.GraphError) as error: ig.graph('GET','account','test-secret',{'fields':'id'})
        req=request.call_args.args[0]
        self.assertNotIn('test-secret',req.full_url)
        self.assertEqual(req.get_header('Authorization'),'Bearer test-secret')
        self.assertNotIn('test-secret',str(error.exception))
        self.assertTrue(error.exception.rate_limited)

    def test_no_due_posts_no_api(self):
        with patch.object(ig, 'graph') as api:
            self.assertEqual(ig.run(ENV,self.state,{'pendientes':[]},NOW),0);api.assert_not_called()

    def test_bounded_pagination_fails_closed(self):
        page={'data':[MEDIA], 'paging':{'next':'https://not-used/?access_token=secret','cursors':{'after':'cursor'}}}
        with patch.object(ig,'graph',return_value=page) as api:
            with self.assertRaises(RuntimeError): ig.recent_media(ENV,'account',NOW-timedelta(days=1))
        self.assertEqual(api.call_count,5)
        self.assertEqual(api.call_args.args[1],'account/media')

    def test_atomic_state_permissions_and_previous_data(self):
        self.state['historial']=[{'id':'old','ig_id':'old-media','fecha':'2026-10-19'}]
        ig.save_state(self.state)
        self.assertEqual(self.state_path.stat().st_mode & 0o777,0o600)
        self.assertEqual(json.loads(self.state_path.read_text()),self.state)

if __name__ == '__main__': unittest.main()
