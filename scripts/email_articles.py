#!/usr/bin/env python3
"""TuHoy mail intake. Read-only IMAP; Ghost roles checked on every submission/publish."""
import argparse, email, email.policy, fcntl, hashlib, html, imaplib, json, os, re
import secrets, smtplib, sqlite3, ssl, time
from email.message import EmailMessage
from email.utils import getaddresses
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
import daily_edition as d

ADDRESS='articulos@tuhoy.com'
ROLES={'Contributor':'draft','Author':'published','Editor':'published','Administrator':'published','Owner':'published'}
MAX_BYTES=10*1024*1024
class Rejected(Exception): pass

def message_text(msg):
 """Read body text without evaluating HTML; confirmations never use attachments."""
 plain=[];rich=[]
 for part in msg.walk():
  if part.is_multipart() or part.get_content_disposition()=='attachment':continue
  if part.get_content_type() not in ('text/plain','text/html'):continue
  try:value=(part.get_payload(decode=True) or b'').decode(part.get_content_charset() or 'utf-8','replace')
  except LookupError:continue
  (plain if part.get_content_type()=='text/plain' else rich).append(value)
 if plain:return '\n'.join(plain).strip()
 parser=Text();parser.feed('\n'.join(rich));return ''.join(parser.parts).strip()

def confirmation_token(msg):
 subject=str(msg.get('Subject','')).strip()
 # Common mail clients prepend several localized reply prefixes.
 subject=re.sub(r'^(?:(?:re|aw|rv|fw|fwd):\s*)+','',subject,flags=re.I)
 match=re.fullmatch(r'CONFIRMAR ([a-f0-9]{48})',subject,re.I)
 if match:return match[1].lower(),True
 if subject.casefold()!='confirma tu artículo en tuhoy':return None,False
 text=message_text(msg)
 first=next((line.strip() for line in text.splitlines() if line.strip()),'')
 # A quoted token alone is insufficient: the reply must explicitly confirm.
 explicit=re.fullmatch(r'(?:sí[, ]+)?(?:confirmo|confirmar|confirmado|confirm)(?:[.!])?',first,re.I)
 tokens=set(re.findall(r'\bCONFIRMAR\s+([a-f0-9]{48})\b',text,re.I))
 return (next(iter(tokens)).lower() if explicit and len(tokens)==1 else None),True

def confirmation_link(token):
 return 'mailto:'+ADDRESS+'?'+urlencode({'subject':'CONFIRMAR '+token,'body':'Confirmo la autoría y el envío de mi artículo.'})

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
  token,is_confirmation=confirmation_token(msg)
  if is_confirmation:
   row=self.db.execute('SELECT * FROM submissions WHERE token=?',(token,)).fetchone() if token else None
   if row and row['sender']==who and row['expires']>=time.time() and row['stage']=='pending':
    self.db.execute("UPDATE submissions SET stage='approved' WHERE k=?",(row['k'],));self.db.commit()
   elif row and row['sender']==who:
    self.db.execute('INSERT INTO outbox(recipient,subject,body) VALUES(?,?,?)',(who,'TuHoy: confirmación no completada','No se confirmó ningún artículo. Usa el enlace del correo original y envía el mensaje que se abre. La confirmación vence en 48 horas; si venció, vuelve a enviar tu artículo. No cambies el asunto ni lo pegues como título de la noticia.'))
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
    self.db.execute('INSERT INTO outbox(recipient,subject,body) VALUES(?,?,?)',(who,'Confirma tu artículo en TuHoy',f'Artículo: {title}\nCon tu permiso actual será {outcome}.\n\nPulsa este enlace y ENVÍA el correo que se abre para confirmar:\n{confirmation_link(token)}\n\nTambién puedes responder a este correo escribiendo CONFIRMAR en la primera línea y conservando el mensaje original debajo.\n\nAlternativa manual: envía un NUEVO correo a {ADDRESS} con este asunto exacto:\nCONFIRMAR {token}\n\nLa confirmación vence en 48 horas. Si no enviaste este artículo, ignora el mensaje.'))
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
    cover=None
    for n,(typ,b64) in enumerate(json.loads(row['images'])):
     extension={'image/jpeg':'jpg','image/png':'png','image/webp':'webp'}[typ]
     url=self.ghost.upload_image(base64.b64decode(b64),'articulo-'+str(n)+'.'+extension,typ)
     if not url:raise RuntimeError('Image upload unavailable')
     if cover is None:cover=url
     body+='<figure><img src="'+html.escape(url,quote=True)+'" alt="'+html.escape(row['title'],quote=True)+'"></figure>'
    draft={'title':row['title'],'slug':slug,'html':body,'status':'draft','authors':[{'id':permit[0]}],'tags':[{'name':'#correo-colaboradores'}]}
    if cover:draft.update(feature_image=cover,feature_image_alt=row['title'])
    code,result=self.ghost.post_json('/posts/?source=html',{'posts':[draft]})
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
    if r['subject']=='Confirma tu artículo en TuHoy':
     tokens=re.findall(r'^CONFIRMAR ([a-f0-9]{48})$',r['body'],re.M)
     if len(tokens)==1:
      link=confirmation_link(tokens[0])
      msg.add_alternative('<html><body><p>'+html.escape(r['body']).replace('\n','<br>')+'</p><p><a href="'+html.escape(link,quote=True)+'">Confirmar artículo: abrir correo</a></p><p>Envía el mensaje que se abre. El enlace por sí solo no publica nada.</p></body></html>',subtype='html')
    server.send_message(msg);self.db.execute('UPDATE outbox SET sent=1 WHERE id=?',(r['id'],));self.db.commit()
def intake_folders(client):
 typ,entries=client.list()
 if typ!='OK':raise RuntimeError('IMAP folder discovery failed')
 folders=['INBOX']
 for entry in entries or []:
  if not isinstance(entry,bytes):continue
  match=re.fullmatch(rb'\((.*?)\) (?:"(?:[^"\\]|\\.)*"|NIL) (.+)',entry)
  if not match:continue
  flags=match[1].lower().split();wire=match[2].decode('ascii')
  name=wire.strip('"').lower().split('/')[-1]
  if b'\\noselect' in flags:continue
  if b'\\junk' in flags or name in ('spam','junk','junk email','junk e-mail'):
   if wire not in folders:folders.append(wire)
 if len(folders)==1:raise RuntimeError('No spam/junk mailbox discovered')
 return folders

def poll_mailbox(app,initialize=False):
 with imaplib.IMAP4_SSL('imap.gmail.com',timeout=25) as client:
  client.login(os.environ['TUHOY_IMAP_USER'],os.environ['TUHOY_IMAP_PASSWORD'])
  folders=intake_folders(client)
  for folder in folders:
   typ,_=client.select(folder,readonly=True)
   if typ!='OK':raise RuntimeError('IMAP mailbox selection failed')
   validity=client.response('UIDVALIDITY')[1][0].decode();nextuid=int(client.response('UIDNEXT')[1][0])
   # Keep the existing INBOX cursor; other folders have independent UID spaces.
   suffix='' if folder=='INBOX' else ':'+hashlib.sha256(folder.encode()).hexdigest()
   validity_key='validity'+suffix;cursor_key='last_uid'+suffix
   old=app.db.execute('SELECT v FROM meta WHERE k=?',(validity_key,)).fetchone()
   if initialize and old:raise RuntimeError('Already initialized; refusing to reset cursor')
   if not old:
    app.db.executemany('INSERT INTO meta VALUES(?,?)',[(validity_key,validity),(cursor_key,str(nextuid-1))]);app.db.commit()
    print('Mailbox baseline initialized; historical mail untouched')
    continue
   if old[0]!=validity:raise RuntimeError('Mailbox UIDVALIDITY changed; manual reconciliation required')
   last=int(app.db.execute('SELECT v FROM meta WHERE k=?',(cursor_key,)).fetchone()[0])
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
    app.db.execute('UPDATE meta SET v=? WHERE k=?',(uid.decode(),cursor_key));app.db.commit()
 return not initialize

def run_cycle(app,env,poll=poll_mailbox):
 failure=None
 try:
  if poll(app) is False:return
 except (TimeoutError,OSError,imaplib.IMAP4.abort) as ex:failure=ex
 # A transient IMAP outage must not block already-confirmed work or receipts.
 app.process();app.deliver(env)
 app.db.execute("UPDATE submissions SET stage='expired',body='',images='[]',token=NULL WHERE stage='pending' AND expires<?",(int(time.time()),));app.db.commit()
 if failure:raise failure
 print('Intake completed')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--initialize',action='store_true');args=parser.parse_args()
 state=Path(os.environ.get('TUHOY_MAIL_STATE','/home/raul/tuhoy/data/mail-private'))
 state.mkdir(parents=True,exist_ok=True);os.chmod(state,0o700)
 with (state/'lock').open('w') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  env=d.load_env();app=Intake(state,d.Ghost(env['GHOST_URL'],env['GHOST_ADMIN_API_KEY']))
  if args.initialize:poll_mailbox(app,initialize=True)
  else:run_cycle(app,env)
if __name__=='__main__':
 try:main()
 except Exception as ex:
  print('Intake failed:',type(ex).__name__,flush=True);raise SystemExit(1)
