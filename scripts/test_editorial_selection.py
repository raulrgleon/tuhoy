import json
import unittest
from unittest.mock import patch
import editorial_selection as e
class SelectionTests(unittest.TestCase):
    def test_invalid_ids_duplicates_and_topic_limits(self):
        rows=[{'id':i,'topic':'economia','immigration':False,'cuba':False,'reason':'dato nuevo'} for i in [99,True,0,0,1,2]]
        with patch.object(e.writer,'config',return_value={'model':'test'}),patch.object(e.writer,'chat',return_value=json.dumps({'selected':rows})):
            self.assertEqual(e.select([{'title':str(i)} for i in range(3)],[]),[{'title':'0'},{'title':'1'}])
    def test_cuba_and_immigration_caps(self):
        rows=[{'id':i,'topic':t,'immigration':i<2,'cuba':i>=2,'reason':'dato nuevo'} for i,t in enumerate(['politica','servicios','cultura','comunidad'])]
        with patch.object(e.writer,'config',return_value={'model':'test'}),patch.object(e.writer,'chat',return_value=json.dumps({'selected':rows})):
            self.assertEqual(len(e.select([{'title':str(i)} for i in range(4)],[])),2)
    def test_malformed_selection_fails_closed(self):
        with patch.object(e.writer,'config',return_value={'model':'test'}),patch.object(e.writer,'chat',return_value='{}'):
            with self.assertRaises(e.writer.WriterError):e.select([{"title":"nota"}],[])
