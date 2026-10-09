import sys,unittest,tempfile,time
from pathlib import Path
from email.message import EmailMessage
sys.path.insert(0,str(Path(__file__).parent))
from email_articles import Intake,article,Rejected
class Ghost:
 def __init__(self):self.posts=[];self.published=0
 def get(self,path):return 200,{'posts':self.posts}
 def post_json(self,path,body):
  p=dict(body['posts'][0],id='post1',updated_at='now',url='https://tuhoy.com/test/');self.posts=[p];return 201,{'posts':[p]}
 def put_json(self,path,body):self.published+=1;self.posts[0]['status']='published';return 200,{'posts':self.posts}
def user(role='Contributor',status='active'):return {'id':'u1','email':'author@example.com','status':status,'roles':[{'name':role}]}
def message(title='Un artículo real',who='author@example.com',identity='id1',body='Este es un artículo de prueba suficientemente largo.'):
 m=EmailMessage();m['From']=who;m['To']='articulos@tuhoy.com';m['Subject']=title;m['Message-ID']='<'+identity+'>';m.set_content(body);return m.as_bytes()
class Tests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.g=Ghost();self.app=Intake(Path(self.temp.name),self.g,[user()])
 def tearDown(self):self.app.db.close();self.temp.cleanup()
 def approve(self):
  token=self.app.db.execute('select token from submissions').fetchone()[0]
  self.app.receive(message('CONFIRMAR '+token,identity='reply'));self.app.process()
 def test_contributor_draft(self):
  self.app.receive(message());self.approve();self.assertEqual(self.g.posts[0]['status'],'draft');self.assertEqual(self.g.posts[0]['authors'],[{'id':'u1'}])
 def test_author_publish(self):
  self.app.fixed_users=[user('Author')];self.app.receive(message());self.approve();self.assertEqual(self.g.published,1)
 def test_downgrade_respected(self):
  self.app.fixed_users=[user('Author')];self.app.receive(message());self.app.fixed_users=[user()];self.approve();self.assertEqual(self.g.published,0)
 def test_revoked(self):
  self.app.receive(message());self.app.fixed_users=[user(status='inactive')];self.approve();self.assertFalse(self.g.posts)
 def test_unknown_rejected(self):self.app.receive(message(who='stranger@example.com'));self.assertEqual(self.app.db.execute('select count(*) from outbox').fetchone()[0],0)
 def test_no_confirm_no_post(self):self.app.receive(message());self.app.process();self.assertFalse(self.g.posts)
 def test_duplicate(self):self.app.receive(message());self.app.receive(message());self.assertEqual(self.app.db.execute('select count(*) from submissions').fetchone()[0],1)
 def test_bad_confirmation(self):self.app.receive(message());self.app.receive(message('CONFIRMAR '+'0'*48,identity='reply'));self.app.process();self.assertFalse(self.g.posts)
 def test_wrong_sender(self):
  self.app.receive(message());self.app.fixed_users.append(dict(user('Author'),email='other@example.com',id='u2'))
  t=self.app.db.execute('select token from submissions').fetchone()[0];self.app.receive(message('CONFIRMAR '+t,who='other@example.com',identity='reply'));self.app.process();self.assertFalse(self.g.posts)
 def test_expired(self):
  self.app.receive(message());self.app.db.execute('update submissions set expires=0');self.app.db.commit();self.approve();self.assertFalse(self.g.posts)
 def test_repeat_processing(self):self.app.fixed_users=[user('Author')];self.app.receive(message());self.approve();self.app.process();self.assertEqual(len(self.g.posts),1);self.assertEqual(self.g.published,1)
 def test_crash_recovery(self):
  self.app.fixed_users=[user('Author')];self.app.receive(message());self.approve();self.app.db.execute("update submissions set stage='draft-created'");self.app.db.commit();self.app.process();self.assertEqual(self.g.published,1)
 def test_markup_escaped(self):
  m=EmailMessage();m['Subject']='Título';m.set_content('<script>alert(1)</script> texto suficientemente largo');_,body,_=article(m);self.assertNotIn('<script>',body)
 def test_html_script_removed(self):
  m=EmailMessage();m['Subject']='Título';m.set_content('<script>malicioso</script><p>Contenido seguro suficientemente largo.</p>',subtype='html');_,body,_=article(m);self.assertNotIn('malicioso',body)
 def test_fake_image(self):
  m=EmailMessage();m['Subject']='Título';m.set_content('Contenido suficientemente largo aquí.');m.add_attachment(b'<script/>',maintype='image',subtype='png',filename='evil.png')
  with self.assertRaises(Rejected):article(m)
 def test_document_rejected(self):
  m=EmailMessage();m['Subject']='Título';m.set_content('Contenido suficientemente largo aquí.');m.add_attachment(b'pdf',maintype='application',subtype='pdf',filename='a.pdf')
  with self.assertRaises(Rejected):article(m)
if __name__=='__main__':unittest.main()
