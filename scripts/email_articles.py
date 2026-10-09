#!/usr/bin/env python3
"""TuHoy mail intake. Read-only IMAP; Ghost roles checked on every submission/publish."""
import argparse, email, email.policy, fcntl, hashlib, html, imaplib, json, os, re
import secrets, smtplib, sqlite3, ssl, time
from email.message import EmailMessage
from email.utils import getaddresses
from html.parser import HTMLParser
from pathlib import Path
import daily_edition as d

ADDRESS='articulos@tuhoy.com'
ROLES={'Contributor':'draft','Author':'published','Editor':'published','Administrator':'published','Owner':'published'}
MAX_BYTES=10*1024*1024
class Rejected(Exception): pass
class Text(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]; self.blocked=0
 def handle_starttag(self,t,a):
  if t in ('script','style'):self.blocked+=1
  if t in ('p','div','br','li','h1','h2','h3'):self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ('script','style'):self.blocked=max(0,self.blocked-1)
 def handle_data(self,s):
  if not self.blocked:self.parts.append(s)
def sender(msg):
 a=getaddresses(msg.get_all('From',[]))
 if len(a)!=1 or not re.fullmatch(r'[^\s@]+@[^\s@]+',a[0][1]): raise Rejected('Remitente inválido')
 return a[0][1].lower()
def addressed(msg):
 fields=['To','Cc','Delivered-To','X-Original-To','X-Forwarded-To']
 return ADDRESS in {a.lower() for _,a in getaddresses([v for k in fields for v in msg.get_all(k,[])])}
def article(msg):
 title=str(msg.get('Subject','')).strip()
 if not title or len(title)>200:raise Rejected('El asunto debe contener un título de hasta 200 caracteres.')
 parts=list(msg.walk()); plain=[]; rich=[]; images=[]
 for p in parts:
  if p.is_multipart():continue
  typ=p.get_content_type(); raw=p.get_payload(decode=True) or b''
  if typ.startswith('image/'):
   valid=(typ=='image/jpeg' and raw.startswith(b'\xff\xd8\xff')) or (typ=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (typ=='image/webp' and raw[:4]==b'RIFF' and raw[8:12]==b'WEBP')
   if not valid or len(raw)>3*1024*1024:raise Rejected('Las imágenes deben ser JPG, PNG o WebP de hasta 3 MB.')
   images.append((typ,raw))
  elif p.get_content_disposition()=='attachment':raise Rejected('Pega el artículo en el cuerpo del correo; no se admiten documentos adjuntos.')
  elif typ in ('text/plain','text/html'):
   try:value=raw.decode(p.get_content_charset() or 'utf-8','replace')
   except LookupError:raise Rejected('Codificación de texto no compatible; envía texto UTF-8.')
   (plain if typ=='text/plain' else rich).append(value)
 if len(images)>5:raise Rejected('Máximo cinco imágenes por artículo.')
 if plain: text='\n'.join(plain).strip()
 else:
  parser=Text();parser.feed('\n'.join(rich));text=''.join(parser.parts).strip()
 if len(text)<20 or len(text)>100000:raise Rejected('El cuerpo debe contener entre 20 y 100.000 caracteres.')
 body=''.join('<p>'+html.escape(p).replace('\n','<br>')+'</p>' for p in re.split(r'\n\s*\n',text) if p.strip())
 return title,body,images
class Intake:
 def __init__(self,state,ghost,users=None):
  state.mkdir(parents=True,exist_ok=True);os.chmod(state,0o700)
  self.db=sqlite3.connect(state/'intake.sqlite');self.db.row_factory=sqlite3.Row;self.ghost=ghost;self.fixed_users=users
  self.db.executescript('''CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT);
CREATE TABLE IF NOT EXISTS seen(k TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS submissions(k TEXT PRIMARY KEY,sender TEXT,title TEXT,body TEXT,images TEXT,token TEXT UNIQUE,expires INTEGER,stage TEXT,post_id TEXT,url TEXT);
CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY,recipient TEXT,subject TEXT,body TEXT,sent INTEGER DEFAULT 0);
''');self.db.commit()
 def users(self):
  if self.fixed_users is not None:return self.fixed_users
  code,data=self.ghost.get('/users/?include=roles&limit=all')
  if code!=200:raise RuntimeError('Ghost users unavailable')
  return data['users']
 def permission(self,address):
  matches=[u for u in self.users() if u.get('email','').lower()==address and u.get('status')=='active']
  if len(matches)!=1:return None
  roles=[r['name'] for r in matches[0].get('roles',[])]
  if len(roles)!=1 or roles[0] not in ROLES:return None
  return matches[0]['id'],ROLES[roles[0]]
 def mail(self,to,subject,body):
  self.db.execute('INSERT INTO outbox(recipient,subject,body) VALUES(?,?,?)',(to,subject,body));self.db.commit()
 def receive(self,raw):
  msg=email.message_from_bytes(raw,policy=email.policy.default)
  if not addressed(msg) or msg.get('Auto-Submitted','no').lower()!='no':return
  try:who=sender(msg)
  except Rejected:return
  permit=self.permission(who)
  if not permit:return
  if len(raw)>MAX_BYTES: self.mail(who,'TuHoy: artículo rechazado','El correo supera 10 MB.');return
  identity=str(msg.get('Message-ID','')).strip()
  key=hashlib.sha256((who+'\0'+identity).encode() if identity else raw).hexdigest()
  if self.db.execute('SELECT 1 FROM seen WHERE k=?',(key,)).fetchone():return
  subject=str(msg.get('Subject','')).strip()
  confirm=re.fullmatch(r'(?:Re:\s*)?CONFIRMAR ([a-f0-9]{48})',subject,re.I)
  if confirm:
   row=self.db.execute('SELECT * FROM submissions WHERE token=?',(confirm[1].lower(),)).fetchone()
   if row and row['sender']==who and row['expires']>=time.time() and row['stage']=='pending':
    self.db.execute("UPDATE submissions SET stage='approved' WHERE k=?",(row['k'],));self.db.commit()
  else:
   try:
    pending=self.db.execute("SELECT count(*) FROM submissions WHERE sender=? AND stage='pending' AND expires>?",(who,int(time.time()))).fetchone()[0]
    if pending>=5:
     self.db.execute('INSERT INTO seen VALUES(?)',(key,));self.db.commit();return
    title,body,images=article(msg)
    import base64
    encoded=json.dumps([(typ,base64.b64encode(blob).decode()) for typ,blob in images])
    token=secrets.token_hex(24)
    # Submission and confirmation are persisted atomically before sending.
    self.db.execute('INSERT OR IGNORE INTO submissions VALUES(?,?,?,?,?,?,?,?,?,?)',(key,who,title,body,encoded,token,int(time.time()+172800),'pending',None,None))
    token=self.db.execute('SELECT token FROM submissions WHERE k=?',(key,)).fetchone()[0]
    outcome='publicado' if permit[1]=='published' else 'guardado como borrador para revisión'
    self.db.execute('INSERT INTO outbox(recipient,subject,body) VALUES(?,?,?)',(who,'Confirma tu artículo en TuHoy',f'Artículo: {title}\nCon tu permiso actual será {outcome}.\n\nPara confirmar la autoría, envía un NUEVO correo a {ADDRESS} con este asunto exacto:\nCONFIRMAR {token}\n\nLa confirmación vence en 48 horas. Si no enviaste este artículo, ignora el mensaje.'))
   except Rejected as ex:self.db.execute('INSERT INTO outbox(recipient,subject,body) VALUES(?,?,?)',(who,'TuHoy: revisa tu artículo',str(ex)))
  self.db.execute('INSERT INTO seen VALUES(?)',(key,));self.db.commit()
 def process(self):
  import base64
  for row in self.db.execute("SELECT * FROM submissions WHERE stage IN ('approved','draft-created')").fetchall():
   permit=self.permission(row['sender'])
   if not permit:
    self.db.execute("UPDATE submissions SET stage='revoked' WHERE k=?",(row['k'],));self.db.commit();continue
   slug='correo-'+row['k'][:40]
   code,result=self.ghost.get('/posts/?filter=slug:'+slug+'&formats=html&limit=1')
   if code!=200:raise RuntimeError('Ghost lookup unavailable')
   posts=result.get('posts',[])
   if posts:post=posts[0]
   else:
    body=row['body']
    for n,(typ,b64) in enumerate(json.loads(row['images'])):
     extension={'image/jpeg':'jpg','image/png':'png','image/webp':'webp'}[typ]
     url=self.ghost.upload_image(base64.b64decode(b64),'articulo-'+str(n)+'.'+extension,typ)
     if not url:raise RuntimeError('Image upload unavailable')
     body+='<figure><img src="'+html.escape(url,quote=True)+'" alt="'+html.escape(row['title'],quote=True)+'"></figure>'
    code,result=self.ghost.post_json('/posts/?source=html',{'posts':[{'title':row['title'],'slug':slug,'html':body,'status':'draft','authors':[{'id':permit[0]}],'tags':[{'name':'#correo-colaboradores'}]}]})
    if code not in (200,201):raise RuntimeError('Ghost draft creation failed')
    post=result['posts'][0]
   # Prevent edits/duplicate publication if a crash happened after finalizing.
   if not any(a['id']==permit[0] for a in post.get('authors',[])):raise RuntimeError('Post author mismatch')
   self.db.execute("UPDATE submissions SET stage='draft-created',post_id=? WHERE k=?",(post['id'],row['k']));self.db.commit()
   permit=self.permission(row['sender'])
   if not permit:
    self.db.execute("UPDATE submissions SET stage='revoked' WHERE k=?",(row['k'],));self.db.commit();continue
   if permit[1]=='published' and post['status']=='draft':
    code,result=self.ghost.put_json('/posts/'+post['id']+'/',{'posts':[{'id':post['id'],'updated_at':post['updated_at'],'status':'published'}]})
    if code!=200:raise RuntimeError('Ghost publishing failed')
    post=result['posts'][0]
   status='published' if post['status']=='published' else 'draft'
   link=post['url'] if status=='published' else 'https://tuhoy.com/ghost/#/editor/post/'+post['id']
   self.db.execute('UPDATE submissions SET stage=?,url=?,body=?,images=?,token=NULL WHERE k=?',(status,link,'','[]',row['k']))
   self.db.execute('INSERT INTO outbox(recipient,subject,body) VALUES(?,?,?)',(row['sender'],'TuHoy: artículo '+('publicado' if status=='published' else 'recibido para revisión'),row['title']+'\n'+link))
   if status=='draft':self.db.execute('INSERT INTO outbox(recipient,subject,body) VALUES(?,?,?)',('raulrgleon@gmail.com','TuHoy: artículo pendiente de revisión',row['title']+'\n'+link))
   self.db.commit()
 def deliver(self,env):
  rows=self.db.execute('SELECT * FROM outbox WHERE sent=0').fetchall()
  if not rows:return
  with smtplib.SMTP('smtp-relay.brevo.com',587,timeout=25) as server:
   server.starttls(context=ssl.create_default_context());server.login(env['BREVO_SMTP_LOGIN'],env['BREVO_SMTP_KEY'])
   for r in rows:
    msg=EmailMessage();msg['From']='TuHoy <info@tuhoy.com>';msg['To']=r['recipient'];msg['Reply-To']=ADDRESS;msg['Subject']=r['subject'];msg['Auto-Submitted']='auto-generated';msg['Message-ID']=f'<tuhoy-mail-{r["id"]}@tuhoy.com>';msg.set_content(r['body'])
    server.send_message(msg);self.db.execute('UPDATE outbox SET sent=1 WHERE id=?',(r['id'],));self.db.commit()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--initialize',action='store_true');args=parser.parse_args()
 state=Path(os.environ.get('TUHOY_MAIL_STATE','/home/raul/tuhoy/data/mail-private'))
 state.mkdir(parents=True,exist_ok=True);os.chmod(state,0o700)
 with (state/'lock').open('w') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  env=d.load_env();app=Intake(state,d.Ghost(env['GHOST_URL'],env['GHOST_ADMIN_API_KEY']))
  with imaplib.IMAP4_SSL('imap.gmail.com',timeout=25) as client:
   client.login(os.environ['TUHOY_IMAP_USER'],os.environ['TUHOY_IMAP_PASSWORD']);client.select('INBOX',readonly=True)
   validity=client.response('UIDVALIDITY')[1][0].decode();nextuid=int(client.response('UIDNEXT')[1][0])
   old=app.db.execute("SELECT v FROM meta WHERE k='validity'").fetchone()
   if args.initialize or not old:
    if old:raise RuntimeError('Already initialized; refusing to reset cursor')
    app.db.executemany('INSERT INTO meta VALUES(?,?)',[('validity',validity),('last_uid',str(nextuid-1))]);app.db.commit();print('Mailbox baseline initialized; old mail untouched');return
   if old[0]!=validity:raise RuntimeError('Mailbox UIDVALIDITY changed; manual reconciliation required')
   last=int(app.db.execute("SELECT v FROM meta WHERE k='last_uid'").fetchone()[0])
   typ,ids=client.uid('search',None,'UID',str(last+1)+':*')
   if typ!='OK':raise RuntimeError('IMAP search failed')
   for uid in [u for u in ids[0].split() if int(u)>last][:100]:
    typ,items=client.uid('fetch',uid,'(RFC822.SIZE)')
    if typ!='OK':raise RuntimeError('IMAP size failed')
    match=re.search(rb'RFC822.SIZE (\d+)',b' '.join(x for x in items if isinstance(x,bytes)))
    if not match:raise RuntimeError('Missing size')
    if int(match[1])<=MAX_BYTES:
     typ,items=client.uid('fetch',uid,'(BODY.PEEK[])')
     if typ!='OK':raise RuntimeError('IMAP fetch failed')
     raw=next(x[1] for x in items if isinstance(x,tuple));app.receive(raw)
    app.db.execute("UPDATE meta SET v=? WHERE k='last_uid'",(uid.decode(),));app.db.commit()
  app.process();app.deliver(env)
  # Expired unconfirmed articles retain only audit metadata, never publish.
  app.db.execute("UPDATE submissions SET stage='expired',body='',images='[]',token=NULL WHERE stage='pending' AND expires<?",(int(time.time()),));app.db.commit()
  print('Intake completed')
if __name__=='__main__':
 try:main()
 except Exception as ex:
  print('Intake failed:',type(ex).__name__,flush=True);raise SystemExit(1)
