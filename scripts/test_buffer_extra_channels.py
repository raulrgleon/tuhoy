import unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import buffer_extra_channels as worker

class ExtraChannelTests(unittest.TestCase):
    def test_pins_correct_account_and_service(self):
        for platform in worker.PLATFORMS:
            worker.validate_channel({'name':'TuHoyNoticias','service':platform,'serviceId':'UCPvMwculzE04EAjeSPpilVw'},platform)
            for bad in [{'name':'another','service':platform},{'name':'TuHoyNoticias','service':'facebook'},{'name':'TuHoyNoticias','service':platform,'isDisconnected':True}]:
                with self.assertRaises(RuntimeError):worker.validate_channel(bad,platform)
    def test_no_backfill_or_duplicates(self):
        now=datetime.now(timezone.utc);start=now-timedelta(minutes=30)
        queue=[{'id':'old','hora':(now-timedelta(hours=1)).isoformat()},{'id':'new','hora':now.isoformat()},{'id':'future','hora':(now+timedelta(hours=1)).isoformat()}]
        self.assertEqual([x['id'] for x in worker.due(queue,{},start.isoformat(),now)],['new'])
        self.assertEqual(worker.due(queue,{'new':{}},start.isoformat(),now),[])
    def test_destination_payloads(self):
        item={'titulo':'Una noticia','url':'https://tuhoy.com/noticia/'}
        data=worker.payload('threads','pinned',item);self.assertEqual(data['metadata']['threads']['linkAttachment']['url'],item['url']);self.assertLessEqual(len(data['text']),500)
        video='https://tuhoy.com/content/media/clip.mp4';data=worker.payload('youtube','pinned',item,video);self.assertEqual(data['metadata']['youtube']['categoryId'],'25');self.assertTrue(data['metadata']['youtube']['isAiGenerated'])
        for bad in ['https://other.example/a.mp4',None]:
            with self.assertRaises(ValueError):worker.payload('youtube','pinned',item,bad)
    def test_disabled_destination_never_contacts_api(self):
        with patch.object(worker.tt,'load',return_value={}),patch.object(worker.buffer,'api') as api:
            worker.run('threads');api.assert_not_called()
    def test_uncertain_submission_is_not_retried(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'data').mkdir();now=datetime.now(timezone.utc)
            config=root/'data/config.json';config.write_text(json.dumps({'threads':{'enabled':True,'enabled_at':(now-timedelta(minutes=5)).isoformat(),'id':'pinned'}}))
            queue=root/'data/queue.json';queue.write_text(json.dumps({'pendientes':[{'id':'one','hora':now.isoformat(),'titulo':'Noticia','url':'https://tuhoy.com/news/'}]}))
            channel={'name':'tuhoynoticias','service':'threads'}
            with patch.object(worker,'ROOT',root),patch.object(worker,'CONFIG',config),patch.object(worker.tt,'X_QUEUE',queue),patch.object(worker.buffer,'api',side_effect=[{'channel':channel},{'posts':{'edges':[]}},RuntimeError('lost response')]):
                with self.assertRaises(RuntimeError):worker.run('threads')
            self.assertEqual(json.loads((root/'data/buffer-threads.json').read_text())['items']['one']['status'],'submitting')
            with patch.object(worker,'ROOT',root),patch.object(worker,'CONFIG',config),patch.object(worker.tt,'X_QUEUE',queue),patch.object(worker.buffer,'api',return_value={'channel':channel}) as api:
                worker.run('threads');self.assertEqual(api.call_count,1)

    def test_private_atomic_state(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';worker.save(p,{'items':{}});self.assertEqual(p.stat().st_mode&0o777,0o600);self.assertEqual(json.loads(p.read_text()),{'items':{}})
if __name__=='__main__':unittest.main()
