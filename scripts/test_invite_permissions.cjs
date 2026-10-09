const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const source=fs.readFileSync(process.argv[2],'utf8');
(async()=>{
for(const role of ['Contributor','Author','Editor','Administrator']){
 for(const byName of [true,false]){
  const module={exports:{}};
  const sandbox={module,require(name){
   if(name==='@tryghost/security')return {url:{encodeBase64:x=>x}};
   if(name==='@tryghost/tpl')return s=>s;
   if(name==='@tryghost/logging')return {warn(){}};
   if(name==='../../models/base')return {model(){return {findOne:async()=>({get:()=>role})}}};
   throw Error(name);
  }};
  vm.runInNewContext(source,sandbox);
  const Invites=module.exports;
  let sent=false;
  const service=new Invites({settingsCache:{get:()=> 'TuHoy'},settingsHelpers:{getDefaultEmailDomain:()=> 'tuhoy.com'},urlUtils:{urlFor:()=> 'https://tuhoy.com/ghost/',urlJoin:(...args)=>args.join('/')},mailService:{utils:{generateContent:async({data})=>{
   assert(data.invitedPermissions);assert(data.recipientEmail==='test@example.com');
   assert(data.invitedPermissions.startsWith({Contributor:'Colaborador:',Author:'Autor:',Editor:'Editor:',Administrator:'Administrador:'}[role]));return {html:'ok',text:'ok'};
  }}}});
  await service.add({api:{mail:{send:async()=>{sent=true;}}},InviteModel:{findOne:async()=>null,add:async()=>({id:'i',get:k=>({role_id:'r',token:'t',email:'test@example.com'})[k]}),edit:async()=>({})},invites:[{email:'test@example.com'}],options:{},user:byName?{name:'Raul',email:'owner@example.com'}:{}});
  assert(sent);
 }
}
console.log('8 invitation role paths passed; no emails sent');
})().catch(e=>{console.error(e);process.exit(1)});
