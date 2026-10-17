import json
import sys
import tempfile
import unittest
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
    def test_network_timeout_leaves_uncertain_checkpoint(self):
        with patch.object(b,'video_asset',return_value='https://tuhoy.com/content/media/test.mp4'),patch.object(b.writer,'load_env',return_value={}):
            with self.assertRaises(TimeoutError): self.run_main([{'channel':self.channel},{'posts':{'edges':[]}},TimeoutError()],self.loads)
        self.assertEqual(json.loads(self.state.read_text())['items']['news']['status'],'submitting')
    def test_acceptance_is_not_marked_published(self):
        with patch.object(b,'video_asset',return_value='https://tuhoy.com/content/media/test.mp4'),patch.object(b.writer,'load_env',return_value={}):
            self.run_main([{'channel':self.channel},{'posts':{'edges':[]}},{'createPost':{'post':{'id':'buffer-job','status':'sending','externalLink':None,'schedulingType':'automatic'}}}],self.loads)
        self.assertEqual(json.loads(self.state.read_text())['items']['news']['status'],'sending')

    def test_render_failure_does_not_submit_or_checkpoint(self):
        with patch.object(b,'video_asset',side_effect=RuntimeError('missing image')):
            with self.assertRaises(RuntimeError): self.run_main([{'channel':self.channel},{'posts':{'edges':[]}}],self.loads)
        self.assertFalse(self.state.exists())

if __name__=='__main__': unittest.main()
