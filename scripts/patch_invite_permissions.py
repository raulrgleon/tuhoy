#!/usr/bin/env python3
"""Idempotent, guarded Ghost 5/6 patch: expose existing invited role to mail template."""
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
s = p.read_text()
marker = '// TUHOY_EMAIL_ROLE_V1'
if marker in s:
    raise SystemExit(0)

anchor = re.compile(r"\.then\(\(createdInvite\) => \{\n(?P<indent>[ ]+)invite = createdInvite;")
recipient = re.compile(r"(?P<indent>[ ]+)recipientEmail: invite\.get\('email'\),?")
m = anchor.search(s)
if len(anchor.findall(s)) != 1 or len(recipient.findall(s)) != 2:
    raise SystemExit('Unsupported Ghost version; left unchanged')

i = m.group('indent')
replacement = f""".then(async (createdInvite) => {{
{i}invite = createdInvite;
{i}{marker}: informational only; native Ghost ACL stays intact.
{i}const role = await require('../../models/base').model('Role').findOne({{id: invite.get('role_id')}});
{i}const labels = {{
{i}    Contributor: 'Colaborador: tus artículos quedan como borradores para revisión.',
{i}    Author: 'Autor: puedes publicar tus propios artículos.',
{i}    Editor: 'Editor: puedes publicar y revisar artículos del equipo.',
{i}    Administrator: 'Administrador: puedes publicar y gestionar TuHoy.'
{i}}};
{i}const invitedPermissions = labels[role && role.get('name')] || 'Consulta tus permisos en el panel de TuHoy.';"""
patched = s[:m.start()] + replacement + s[m.end():]
patched = recipient.sub(
    lambda r: f"{r.group('indent')}recipientEmail: invite.get('email'),\n{r.group('indent')}invitedPermissions,",
    patched,
)
p.with_suffix('.js.tuhoy-before-role').write_text(s)
p.write_text(patched)
print('patched')
