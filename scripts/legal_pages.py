#!/usr/bin/env python3
"""Crea o actualiza las páginas de Contacto, Privacidad y Términos de TuHoy.

  python3 scripts/legal_pages.py                       # borradores con el correo pendiente
  python3 scripts/legal_pages.py --email x@tuhoy.com --publish
  python3 scripts/legal_pages.py --email info@tuhoy.com --publish --only contacto
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_edition as daily  # noqa: E402

UPDATED = "5 de octubre de 2026"
PHONE = "(402) 824-0388"
PHONE_WA = "14028240388"

PAGES = {
    "contacto": (
        "Contacto",
        "Cómo escribir a la redacción de TuHoy, enviar una corrección o proponer una historia.",
        """
<p>En TuHoy leemos todos los mensajes. Escríbenos a <a href="mailto:{email}">{email}</a>.</p>
<p><strong>WhatsApp y teléfono:</strong> <a href="https://wa.me/{phone_wa}">{phone}</a>. Puedes escribirnos por WhatsApp, mandar fotos o llamarnos al <a href="tel:+{phone_wa}">{phone}</a>.</p>
<h2>Correcciones</h2>
<p>Si encuentras un error en una nota, cuéntanos cuál es, en qué nota está y, si puedes, la fuente que lo demuestra. Revisamos cada aviso y, cuando corresponde, corregimos la nota e indicamos al final qué cambió.</p>
<h2>Propón una historia</h2>
<p>¿Pasa algo en tu comunidad que nadie está contando? Escríbenos por correo o por <a href="https://wa.me/{phone_wa}">WhatsApp al {phone}</a> con lo que sabes, dónde ocurre y cómo podemos contactarte. Si nos pides reserva sobre tu identidad, la respetamos.</p>
<h2>Suscripción</h2>
<p>Para darte de baja del boletín, usa el enlace que aparece al pie de cada correo o entra a tu cuenta desde el botón «Entrar» del sitio.</p>
""",
    ),
    "privacidad": (
        "Política de privacidad",
        "Qué datos recoge TuHoy, para qué los usa y cómo puedes pedir que los borremos.",
        """
<p><em>Última actualización: {updated}.</em></p>
<p>TuHoy (tuhoy.com) es un periódico digital. Esta política explica qué datos personales tratamos y qué derechos tienes. Responsable: TuHoy, contacto: <a href="mailto:{email}">{email}</a>.</p>
<h2>Qué datos recogemos</h2>
<ul>
<li><strong>Si te suscribes al boletín:</strong> tu correo electrónico y, si lo das, tu nombre.</li>
<li><strong>Si nos escribes:</strong> los datos que incluyas en tu mensaje.</li>
<li><strong>Al navegar:</strong> datos técnicos básicos (dirección IP, navegador, páginas visitadas) que registran nuestro servidor y nuestro proveedor de seguridad y entrega de contenidos para que el sitio funcione y para protegerlo de abusos.</li>
</ul>
<h2>Para qué los usamos</h2>
<ul>
<li>Enviarte el boletín al que te suscribiste.</li>
<li>Responder tus mensajes y gestionar correcciones.</li>
<li>Mantener el sitio seguro y medir su funcionamiento de forma agregada.</li>
</ul>
<p>No vendemos ni alquilamos tus datos.</p>
<h2>Cookies</h2>
<p>Usamos solo las cookies necesarias para que funcionen el inicio de sesión de suscriptores y la seguridad del sitio. No usamos cookies publicitarias.</p>
<h2>Con quién se comparten</h2>
<p>Con los proveedores que nos ayudan a operar el sitio (alojamiento, entrega de contenidos y envío de correos), solo en la medida necesaria y con obligación de confidencialidad, o cuando lo exija la ley.</p>
<h2>Cuánto tiempo los guardamos</h2>
<p>Los datos de suscripción, mientras sigas suscrito. Si te das de baja, los borramos o anonimizamos en un plazo razonable. Los mensajes, el tiempo necesario para atenderlos.</p>
<h2>Tus derechos</h2>
<p>Puedes pedirnos acceso, corrección o eliminación de tus datos, u oponerte a su uso, escribiendo a <a href="mailto:{email}">{email}</a>. También puedes darte de baja del boletín en cualquier momento desde el enlace de cada correo. Si vives en California, tienes además los derechos que te reconoce la ley de privacidad del consumidor de ese estado.</p>
<h2>Menores</h2>
<p>TuHoy no está dirigido a menores de 13 años y no recoge datos de ellos a sabiendas.</p>
<h2>Cambios</h2>
<p>Si cambiamos esta política, actualizaremos la fecha de arriba.</p>
""",
    ),
    "terminos": (
        "Términos de uso",
        "Condiciones para usar tuhoy.com y reproducir sus contenidos.",
        """
<p><em>Última actualización: {updated}.</em></p>
<p>Al usar tuhoy.com aceptas estos términos. Si no estás de acuerdo, por favor no uses el sitio.</p>
<h2>Contenido</h2>
<p>TuHoy publica información periodística elaborada a partir de fuentes que citamos y enlazamos en cada nota. Trabajamos para que sea exacta y actual, pero la información puede cambiar después de publicada. Nada de lo publicado constituye asesoría legal, migratoria, médica ni financiera: para decisiones personales, consulta a un profesional.</p>
<h2>Propiedad intelectual</h2>
<p>Los textos, el diseño y la marca TuHoy pertenecen a TuHoy. Puedes compartir enlaces y citar fragmentos breves con mención y enlace a la nota original. Para reproducir notas completas, escríbenos. Las fotografías llevan su crédito y pertenecen a sus autores o agencias.</p>
<h2>Enlaces a otros sitios</h2>
<p>Enlazamos a las fuentes de cada nota. No controlamos esos sitios ni respondemos por su contenido o sus políticas.</p>
<h2>Suscripciones</h2>
<p>Para suscribirte debes dar un correo válido. Puedes darte de baja cuando quieras. Podemos cancelar cuentas usadas de forma abusiva.</p>
<h2>Correcciones</h2>
<p>Si detectas un error, escríbenos a <a href="mailto:{email}">{email}</a>. Corregimos con transparencia.</p>
<h2>Responsabilidad</h2>
<p>El sitio se ofrece «tal cual». En la medida que permita la ley, TuHoy no responde por daños derivados del uso del sitio o de la información publicada.</p>
<h2>Cambios</h2>
<p>Podemos actualizar estos términos; la fecha de arriba indica la versión vigente.</p>
""",
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--only", choices=sorted(PAGES), help="actualiza solo esta página")
    args = parser.parse_args()
    if args.publish and not args.email:
        print("Para publicar hace falta --email")
        return 1
    email = args.email or "CORREO-PENDIENTE@tuhoy.com"

    env = daily.load_env()
    ghost = daily.Ghost(env["GHOST_URL"], env["GHOST_ADMIN_API_KEY"])
    code, resp = ghost.get("/pages/?limit=all&fields=id,slug,updated_at")
    existing = {p["slug"]: p for p in resp.get("pages") or []}

    for slug, (title, excerpt, body) in PAGES.items():
        if args.only and slug != args.only:
            continue
        page = {
            "title": title,
            "slug": slug,
            "html": body.strip().format(email=email, updated=UPDATED, phone=PHONE, phone_wa=PHONE_WA),
            "custom_excerpt": excerpt,
            "meta_description": excerpt,
            "status": "published" if args.publish else "draft",
        }
        if slug in existing:
            page["updated_at"] = existing[slug]["updated_at"]
            status, out = ghost.put_json(f"/pages/{existing[slug]['id']}/?source=html", {"pages": [page]})
        else:
            status, out = ghost.post_json("/pages/?source=html", {"pages": [page]})
        print(slug, page["status"], status, "" if status < 300 else str(out)[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
