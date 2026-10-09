#!/usr/bin/env python3
"""Idempotent, guarded Ghost 5 patch: expose existing invited role to mail template."""
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text();marker='// TUHOY_EMAIL_ROLE_V1'
if marker in s:raise SystemExit(0)
anchor='''            .then((createdInvite) => {
                invite = createdInvite;'''
replacement='''            .then(async (createdInvite) => {
                invite = createdInvite;
                // TUHOY_EMAIL_ROLE_V1: informational only; native Ghost ACL stays intact.
                const role = await require('../../models/base').model('Role').findOne({id: invite.get('role_id')});
                const labels = {
                    Contributor: 'Colaborador: tus artículos quedan como borradores para revisión.',
                    Author: 'Autor: puedes publicar tus propios artículos.',
                    Editor: 'Editor: puedes publicar y revisar artículos del equipo.',
                    Administrator: 'Administrador: puedes publicar y gestionar TuHoy.'
                };
                const invitedPermissions = labels[role && role.get('name')] || 'Consulta tus permisos en el panel de TuHoy.';'''
if s.count(anchor)!=1 or s.count("recipientEmail: invite.get('email')")!=2:raise SystemExit('Unsupported Ghost version; left unchanged')
s=s.replace(anchor,replacement).replace("recipientEmail: invite.get('email')","recipientEmail: invite.get('email'),\n                        invitedPermissions")
p.with_suffix('.js.tuhoy-before-role').write_text(p.read_text());p.write_text(s)
print('patched')
