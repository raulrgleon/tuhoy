import hashlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from email_articles import Intake,intake_folders,poll_mailbox
from test_email_articles import Ghost,user,message

class Mailbox:
 def __init__(self):
  self.folder=None;self.messages={'INBOX':{},'"[Gmail]/Spam"':{},'Junk':{}}
  self.validity={'INBOX':b'10','"[Gmail]/Spam"':b'20','Junk':b'30'};self.fail=None;self.readonly=[]
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def login(self,*args):pass
 def list(self):return 'OK',[b'(\\HasNoChildren) "/" "INBOX"',b'(\\Junk) "/" "[Gmail]/Spam"',b'(\\HasNoChildren) "/" Junk',b'(\\Noselect \\Junk) "/" Container']
 def select(self,folder,readonly=False):
  self.folder=folder;self.readonly.append(readonly);return ('NO',[]) if folder==self.fail else ('OK',[b'1'])
 def response(self,key):return key,[self.validity[self.folder] if key=='UIDVALIDITY' else str(max(self.messages[self.folder],default=0)+1).encode()]
 def uid(self,op,*args):
  if op=='search':return 'OK',[b' '.join(str(k).encode() for k in self.messages[self.folder])]
  raw=self.messages[self.folder][int(args[0])]
  if args[1]=='(RFC822.SIZE)':return 'OK',[b'1 (RFC822.SIZE '+str(len(raw)).encode()+b')']
  return 'OK',[(b'1 BODY[]',raw)]

class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.app=Intake(Path(self.temp.name),Ghost(),[user()]);self.mail=Mailbox()
  self.env=patch.dict(os.environ,TUHOY_IMAP_USER='test',TUHOY_IMAP_PASSWORD='test');self.env.start()
 def tearDown(self):self.env.stop();self.app.db.close();self.temp.cleanup()
 def poll(self):
  with patch('email_articles.imaplib.IMAP4_SSL',return_value=self.mail):return poll_mailbox(self.app)
 def test_discovery_special_use_and_named_junk(self):self.assertEqual(intake_folders(self.mail),list(self.mail.messages))
 def test_baseline_preserves_existing_inbox_and_skips_historic_spam(self):
  self.app.db.executemany('insert into meta values (?,?)',[('validity','10'),('last_uid','5')]);self.app.db.commit()
  self.mail.messages['INBOX'][6]=message(identity='new-inbox');self.mail.messages['"[Gmail]/Spam"'][7]=message(identity='old-spam')
  self.poll();self.assertEqual(self.app.db.execute('select count(*) from submissions').fetchone()[0],1)
  self.assertEqual(self.app.db.execute("select v from meta where k='last_uid'").fetchone()[0],'6')
 def test_new_spam_and_junk_processed_with_independent_uids_and_dedup(self):
  self.poll();raw=message(identity='same')
  self.mail.messages['INBOX'][101]=raw;self.mail.messages['"[Gmail]/Spam"'][1]=raw;self.mail.messages['Junk'][1]=message(identity='junk')
  self.poll();self.poll()
  self.assertEqual(self.app.db.execute('select count(*) from submissions').fetchone()[0],2)
  self.assertEqual(self.app.db.execute("select count(*) from submissions where stage='pending'").fetchone()[0],2)
  self.assertTrue(all(self.mail.readonly))
 def test_selection_failure_does_not_advance_spam_cursor(self):
  self.poll();self.mail.fail='"[Gmail]/Spam"'
  with self.assertRaisesRegex(RuntimeError,'selection'):self.poll()
  key='last_uid:'+hashlib.sha256(self.mail.fail.encode()).hexdigest()
  self.assertEqual(self.app.db.execute('select v from meta where k=?',(key,)).fetchone()[0],'0')
 def test_validity_change_refuses_replay(self):
  self.poll();self.mail.validity['Junk']=b'999'
  with self.assertRaisesRegex(RuntimeError,'UIDVALIDITY'):self.poll()
 def test_unknown_sender_in_spam_remains_unprocessed(self):
  self.poll();self.mail.messages['Junk'][1]=message(who='unknown@example.com');self.poll()
  self.assertEqual(self.app.db.execute('select count(*) from outbox').fetchone()[0],0)
 def test_discovery_failure_is_not_silent_success(self):
  with patch.object(self.mail,'list',return_value=('NO',[])),self.assertRaises(RuntimeError):intake_folders(self.mail)
if __name__=='__main__':unittest.main()
