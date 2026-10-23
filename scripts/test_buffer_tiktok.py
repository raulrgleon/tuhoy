import json
import sys
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import buffer_tiktok as b

class BufferSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)/'state.json'
        self.channel={'name':'tuhoynoticias','service':'tiktok','isDisconnected':False,'isQueuePaused':False}
    def run_main(self, api, load):
        with patch.object(b,'STATE',self.state), patch.object(b,'api',side_effect=api), patch.object(b.tt,'load',side_effect=load), patch.object(sys,'argv',['buffer_tiktok.py','--post-id','news']): b.main()
    def loads(self,path,default):
        if path==self.state: return {'items':{}}
        if path==b.tt.TT_QUEUE: return {'historial':[]}
        return {'pendientes':[{'id':'news','hora':'2026-10-17T12:00:00+00:00','titulo':'Test','texto':'Test','url':'https://tuhoy.com/test/'}]}
    def test_wrong_account_rejected(self):
        self.channel['name']='other'
        with self.assertRaises(RuntimeError): self.run_main([{'channel':self.channel}],self.loads)
        self.assertFalse(self.state.exists())
    def test_uncertain_job_blocks_new_submission(self):
        def loads(p,d): return {'items':{'old':{'status':'submitting'}}} if p==self.state else self.loads(p,d)
        with patch.object(b,'api',return_value={'channel':self.channel}) as api:
            self.run_main(api,self.loads if False else loads)
            self.assertEqual(api.call_count,1)
    def test_remote_duplicate_is_not_republished(self):
        self.run_main([{'channel':self.channel},{'posts':{'edges':[{'node':{'text':'https://tuhoy.com/test/'}}]}}],self.loads)
        self.assertFalse(self.state.exists())
    def test_failed_remote_post_is_visible_as_failure_without_resending(self):
        def loads(p,d):
            return {'items':{'old':{'status':'error','buffer_id':'old-job'}}} if p==self.state else self.loads(p,d)
        with self.assertRaisesRegex(RuntimeError,'operator review required'):
            self.run_main([{'channel':self.channel},{'post':{'id':'old-job','status':'error','externalLink':None}}],loads)
        self.assertEqual(json.loads(self.state.read_text())['items']['old']['status'],'error')
    def test_network_timeout_leaves_uncertain_checkpoint(self):
        with patch.object(b,'video_asset',return_value='https://tuhoy.com/content/media/test.mp4'),patch.object(b.writer,'load_env',return_value={}):
            with self.assertRaises(TimeoutError): self.run_main([{'channel':self.channel},{'posts':{'edges':[]}},TimeoutError()],self.loads)
        self.assertEqual(json.loads(self.state.read_text())['items']['news']['status'],'submitting')
    def test_acceptance_is_not_marked_published(self):
        with patch.object(b,'video_asset',return_value='https://tuhoy.com/content/media/test.mp4'),patch.object(b.writer,'load_env',return_value={}):
            self.run_main([{'channel':self.channel},{'posts':{'edges':[]}},{'createPost':{'post':{'id':'buffer-job','status':'sending','externalLink':None,'schedulingType':'automatic'}}}],self.loads)
        self.assertEqual(json.loads(self.state.read_text())['items']['news']['status'],'sending')

    def test_app_does_not_enable_tiktok_ai_generated_toggle(self):
        with patch.object(b,'video_asset',return_value='https://tuhoy.com/content/media/test.mp4'),patch.object(b.writer,'load_env',return_value={}),patch.object(b,'api',side_effect=[{'channel':self.channel},{'posts':{'edges':[]}},{'createPost':{'post':{'id':'job','status':'sending','externalLink':None,'schedulingType':'automatic'}}}]) as api:
            self.run_main(api,self.loads)
            payload=api.call_args.args[1]['input']
            self.assertIs(payload['metadata']['tiktok']['isAiGenerated'],False)
            self.assertEqual(payload['channelId'],b.CHANNEL)
            self.assertTrue(payload['assets'][0]['video']['url'].endswith('.mp4'))

    def test_render_failure_does_not_submit_or_checkpoint(self):
        with patch.object(b,'video_asset',side_effect=RuntimeError('missing image')):
            with self.assertRaises(RuntimeError): self.run_main([{'channel':self.channel},{'posts':{'edges':[]}}],self.loads)
        self.assertFalse(self.state.exists())
    def test_provider_quota_sets_cooldown_and_records_failed_news_without_retry(self):
        def loads(p,d):
            return {'items':{'old':{'status':'error','buffer_id':'old-job','created_at':datetime.now(timezone.utc).isoformat()}}} if p==self.state else self.loads(p,d)
        message='TikTok has detected a large number of posts. Wait 24 hours before trying again.'
        with self.assertRaisesRegex(RuntimeError,'cooldown saved'):
            self.run_main([{'channel':self.channel},{'post':{'id':'old-job','status':'error','externalLink':None,'error':{'message':message}}}],loads)
        state=json.loads(self.state.read_text())
        self.assertEqual(state['items']['old']['status'],'rate_limited')
        self.assertTrue(b.cooling_down(state,datetime.now(timezone.utc)))
    def test_cooldown_makes_zero_provider_calls(self):
        def loads(p,d):
            return {'items':{},'paused_until':(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()} if p==self.state else self.loads(p,d)
        with patch.object(b,'api') as api:
            self.run_main(api,loads);api.assert_not_called()
    def test_rolling_daily_limit_stops_before_render_or_submit(self):
        def loads(p,d):
            return {'items':{str(i):{'status':'sent','created_at':datetime.now(timezone.utc).isoformat()} for i in range(10)}} if p==self.state else self.loads(p,d)
        with patch.object(b,'writer') as writer,patch.object(b,'video_asset') as video:
            writer.load_env.return_value={}
            self.run_main([{'channel':self.channel}],loads)
            video.assert_not_called()
    def test_expired_cooldown_and_old_attempts_allow_new_news(self):
        now=datetime.now(timezone.utc)
        state={'paused_until':(now-timedelta(minutes=1)).isoformat(),'items':{'old':{'status':'rate_limited','created_at':(now-timedelta(hours=25)).isoformat()}}}
        self.assertFalse(b.cooling_down(state,now))
        self.assertEqual(b.recent_attempts(state,now),0)

if __name__=='__main__': unittest.main()
