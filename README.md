# TuHoy

Periódico digital en español en [tuhoy.com](https://tuhoy.com): noticias del mundo, inmigración y comunidad latina en EE. UU. Corre sobre **Ghost 5 + MySQL 8**, con un tema propio y una edición diaria automática que parte de fuentes reales.

Las notas las firma y redacta **Raul Garcia**. Nunca se etiquetan como generadas por IA.

## Índice

- [Arquitectura](#arquitectura)
- [Puesta en marcha](#puesta-en-marcha)
- [Variables de entorno](#variables-de-entorno)
- [Edición diaria](#edición-diaria)
- [Redacción (writer.py)](#redacción-writerpy)
- [Scripts](#scripts)
- [Tema](#tema)
- [SEO y Google News](#seo-y-google-news)
- [Correo](#correo)
- [Cloudflare](#cloudflare)
- [Copias de seguridad](#copias-de-seguridad)
- [Estructura del repo](#estructura-del-repo)

## Arquitectura

```
Lectores ──► Cloudflare (DNS, HTTPS, túnel) ──► Traefik (Coolify) ──► Ghost 5 :2368 ──► MySQL 8
                                                                          ▲
cron 06:00 America/Chicago ──► scripts/daily_edition.py ──► Admin API ────┘
                                     │
                                     └─► scripts/writer.py ──► modelo de lenguaje (OpenAI u otro)

Correo saliente:  Ghost ──► Brevo SMTP (info@tuhoy.com)
Correo entrante:  info@tuhoy.com ──► Cloudflare Email Routing ──► raulrgleon@gmail.com
```

- **Servidor:** el Dell de casa (192.168.1.100). Coolify gestiona el servicio **TuHoy Ghost** (panel en `http://192.168.1.100:8000`).
- **MySQL** no se publica a internet.
- **Admin:** https://tuhoy.com/ghost

## Puesta en marcha

En producción el stack lo despliega Coolify. El `docker-compose.yml` del repo es la referencia equivalente:

```bash
cp .env.example .env      # rellena contraseñas, claves y GHOST_URL
docker compose up -d
```

Ghost escucha en el puerto interno **2368**. No publiques 80/443 en el host si Traefik/Coolify ya los usan.

La primera visita a `/ghost` abre la pantalla de creación de cuenta; no hay credenciales de fábrica.

Para los scripts hace falta Python 3.10+ (solo biblioteca estándar) y una **integración personalizada** en Ghost → Settings → Integrations, cuya Admin API key va en `GHOST_ADMIN_API_KEY`.

## Variables de entorno

Todas viven en `.env` (permisos `600`, ignorado por git). Plantilla: [`.env.example`](.env.example).

| Variable | Uso |
| --- | --- |
| `MYSQL_*` | Base de datos de Ghost |
| `GHOST_URL` | URL pública (`https://tuhoy.com`) |
| `GHOST_ADMIN_API_KEY` | Clave `id:secret` de la integración, para los scripts |
| `MAIL_*` | SMTP de Brevo para Ghost (ver [Correo](#correo)) |
| `LLM_PROVIDER` | `openai`, `anthropic`, `gemini` u `openrouter` |
| `OPENAI_API_KEY` (u otra según proveedor) | Clave del modelo |
| `LLM_MODEL`, `LLM_BASE_URL` | Opcionales: modelo concreto y endpoint compatible con OpenAI |
| `LLM_FACTCHECK` | `1` (por defecto) activa la pasada de verificación de hechos |

En Coolify, las variables del contenedor se editan en TuHoy Ghost → Environment Variables.

## Edición diaria

[`scripts/daily_edition.py`](scripts/daily_edition.py) corre cada día a las **06:00 America/Chicago**:

1. Lee RSS reales: BBC Mundo, France 24 y Google News (inmigración y latinos).
2. Descarta duplicados por URL y título (estado en `data/edition_state.json`).
3. Extrae el texto de la fuente; si no hay texto útil, descarta la pieza. **No inventa noticias.**
4. Redacta la nota con `writer.py`. Sin clave de modelo, cae al resumen extractivo (etiqueta interna `#resumen-automatico`, no indexable hasta que se reescriba).
5. Pone la foto de la fuente con su crédito, etiquetas, extracto y meta SEO.
6. Publica en Ghost. Las piezas dudosas se publican igual con la etiqueta interna `#revisar` y se anotan en `data/review_queue.jsonl`.

Instalar o reinstalar el cron (incluye los posts de X):

```bash
bash scripts/install_daily_cron.sh
```

El servidor está en UTC; el cron se lanza a las 11:00 y 12:00 UTC y solo sigue la que coincide con las 06 locales (cubre horario de verano e invierno).

Logs: `logs/daily.log` (actividad) y `logs/daily-errors.log` (errores).

## Redacción (writer.py)

[`scripts/writer.py`](scripts/writer.py) hace tres pasadas con el modelo:

1. **Borrador** ([`prompts/draft.md`](prompts/draft.md)) a partir del texto de la fuente.
2. **Edición** ([`prompts/edit.md`](prompts/edit.md)) para estilo y claridad.
3. **Verificación de hechos** ([`prompts/factcheck.md`](prompts/factcheck.md)): compara cada dato con la fuente y marca lo que no cuadra.

La voz del periódico y las frases prohibidas están en [`prompts/voice.md`](prompts/voice.md); hay ejemplos de mala versión, buena versión y nota en [`prompts/examples/`](prompts/examples/).

Evaluar cambios en los prompts con 5 historias guardadas:

```bash
python3 scripts/eval_writer.py --build   # guarda 5 historias reales en data/eval_stories/
python3 scripts/eval_writer.py           # compara y escribe data/eval_report.md
```

## Posts diarios en X (@tuhoy_)

[`scripts/x_posts.py`](scripts/x_posts.py) corre cada día a las **07:00 America/Chicago**, después de la edición:

1. Toma las notas publicadas en las últimas 30 horas, sin `#revisar` ni `#resumen-automatico`, y sin repetir las ya usadas (historial en `data/x_queue.json`).
2. El modelo elige las **`X_POSTS` más importantes** (hoy 14) (prioridad: inmigración y latinos en EE. UU., luego política de EE. UU., luego internacional) y escribe un post por cada una con [`prompts/tweets.md`](prompts/tweets.md).
3. Asigna una hora a cada post: con 14, uno por hora de 7:00 a 20:00 (con 7: 7, 9, 11, 13, 15, 18 y 21 h; o lo que diga `X_HOURS`).
4. Lo entrega según `X_MODE`:
   - `email` (por defecto, gratis): manda un correo a `X_EMAIL_TO` con los 7 posts y un botón **Publicar en X** que abre X con el texto y el enlace listos. También se pueden programar en X a la hora sugerida.
   - `api`: los publica solos en @tuhoy_. Un cron cada 15 minutos (`--post-due`) publica los que ya tocan.

La API de X es de pago por uso desde 2026 (unos $0.015 por post sin enlace y $0.20 con enlace). Para activar el modo `api`: comprar créditos en [console.x.com](https://console.x.com) con la cuenta @tuhoy_, crear una app con permisos de lectura y escritura, poner las cuatro claves `X_*` en `.env` y cambiar `X_MODE=api`. `X_LINKS` decide cuántos posts llevan enlace (los más importantes primero).

**Estado actual:** `X_MODE=api`, publicando solo en @TuHoy_ con la app `TuHoy_` (id 33505696) de console.x.com. Si un post lleva más de 2 horas de retraso (por ejemplo, el servidor estuvo apagado) se marca como vencido y no se publica, para no soltar varios de golpe.

**Estrategia (presupuesto $20/mes):** 14 posts al día, los 2 más importantes con enlace (`X_POSTS=14`, `X_LINKS=2`): unos $0.58 al día, ~$17.40 al mes.

```bash
python3 scripts/x_posts.py --dry-run   # muestra los 7 posts sin enviarlos
python3 scripts/x_posts.py             # elige, escribe y envía (o encola)
```

Logs: `logs/daily.log` (líneas `[x]`) y `logs/x-errors.log`.

**Perfil de @TuHoy_:** nombre "TuHoy", foto [`brand/x-avatar.jpg`](brand/x-avatar.jpg) (icono TH), portada [`brand/x-banner.jpg`](brand/x-banner.jpg) (1500×500), bio "Noticias en español, claras y verificadas: inmigración, latinos en EE. UU., política y el mundo. Todos los días. 📰", ubicación Estados Unidos y web https://tuhoy.com. Es cuenta profesional (tipo Business, categoría "Media & News Company"). Tiene fijado un post de bienvenida ([2107338626678067255](https://x.com/TuHoy_/status/2107338626678067255)).

## Scripts

| Script | Qué hace |
| --- | --- |
| [`daily_edition.py`](scripts/daily_edition.py) | Edición diaria (ver arriba) |
| [`writer.py`](scripts/writer.py) | Cliente del modelo y las tres pasadas de redacción |
| [`eval_writer.py`](scripts/eval_writer.py) | Compara redacción extractiva vs. modelo |
| [`rewrite_published.py`](scripts/rewrite_published.py) | Reescribe notas ya publicadas desde su fuente; conserva URL, fecha e imagen y guarda copia (`--restore` para deshacer) |
| [`seo_repair.py`](scripts/seo_repair.py) | Repara texto residual, descripciones, títulos SEO e indexación |
| [`use_source_photos.py`](scripts/use_source_photos.py) | Pone la foto de la fuente y su crédito en cada nota |
| [`fix_story_images.py`](scripts/fix_story_images.py) | Sustituye fotos genéricas por imágenes de Wikimedia Commons |
| [`legal_pages.py`](scripts/legal_pages.py) | Crea/actualiza Contacto, Privacidad y Términos |
| [`upload_theme.py`](scripts/upload_theme.py) | Empaqueta, sube y activa el tema `themes/tuhoy` |
| [`upload_routes.py`](scripts/upload_routes.py) | Sube `routes.yaml` a Ghost con copia previa de las rutas activas |
| [`seed_inmigracion.py`](scripts/seed_inmigracion.py) | Primera tanda de notas de Inmigración (histórico) |
| [`x_posts.py`](scripts/x_posts.py) | Elige las 7 notas del día y escribe/envía los posts de X |
| [`apply_ghost_overrides.sh`](scripts/apply_ghost_overrides.sh) | Copia las plantillas de correo propias (`ghost-overrides/`) dentro del contenedor de Ghost y traduce el asunto de la invitación |
| [`install_daily_cron.sh`](scripts/install_daily_cron.sh) | Instala el cron de la edición diaria, de los posts de X y de las plantillas de correo |

Todos leen `.env` y usan la Admin API con un User-Agent de navegador (Cloudflare bloquea con error 1010 los User-Agent de script).

## Tema

El tema propio está en [`themes/tuhoy/`](themes/tuhoy/) (versión en `package.json`; súbela en cada cambio). Para publicarlo:

```bash
python3 scripts/upload_theme.py   # empaqueta, sube y activa el tema
```

También se puede subir el ZIP a mano en Ghost → Settings → Design → Change theme → Upload theme.

Incluye la plantilla `sitemap-news.hbs` para Google News, el pie con enlaces legales y a @TuHoy_ en X, la meta `twitter:site` y la meta de verificación de Search Console.

**Hook de temas:** Ghost 5 descarga los ZIP de GitHub con permisos 000 y helpers de Ghost 6, lo que rompe la instalación en Docker. El compose carga [`ghost-hooks/sanitize-github-theme.js`](ghost-hooks/sanitize-github-theme.js) para arreglarlo. No borres ese archivo y reinicia TuHoy Ghost en Coolify si lo cambias.

## SEO y Google News

- **Rutas:** [`routes.yaml`](routes.yaml) publica `/news-sitemap.xml/` con la plantilla `sitemap-news`. Ghost reserva `/sitemap-*.xml`, por eso no se llama `sitemap-news.xml`.
- **Subir rutas:** `python3 scripts/upload_routes.py`. Si Ghost responde 403/501 con la clave de integración, súbelo en Ghost → Settings → Labs → Routes.
- **Sitemaps:** `https://tuhoy.com/sitemap.xml` (de Ghost) y `https://tuhoy.com/news-sitemap.xml` (las 100 notas más recientes, sin las de resumen extractivo `#resumen-automatico`).
- **Search Console:** propiedad de prefijo de URL `https://tuhoy.com/`, verificada con meta tag en el tema. Ambos sitemaps están enviados.

## Correo

**Saliente (Ghost → lectores):** Brevo SMTP (plan gratis, 300 correos/día).

- Host `smtp-relay.brevo.com`, puerto `587`, `secure=false`.
- Remitente `TuHoy <info@tuhoy.com>` (`mail__from`).
- En Ghost → Settings → Membership, la dirección de soporte (`members_support_address`) es `info@tuhoy.com`; así los magic links salen de info@ y no de noreply@.
- Dominio autenticado en Brevo: registros `brevo-code`, DKIM `brevo1/brevo2._domainkey` y DMARC en Cloudflare.
- Logs de envío: Brevo → Transactional → Logs.
- Brevo desactiva las claves SMTP tras 90 días sin uso.

**Entrante (info@tuhoy.com):** Cloudflare Email Routing reenvía `info@tuhoy.com` → `raulrgleon@gmail.com`. El resto de direcciones se descartan (catch-all: Drop). El registro de actividad está en Cloudflare → Email Routing → Activity log.

El reenvío de Namecheap no sirve porque el dominio usa los nameservers de Cloudflare.

**Invitación al equipo (staff) en español:** Ghost no deja editar este correo desde el panel. La versión propia está en [`ghost-overrides/mail/invite-user.html`](ghost-overrides/mail/invite-user.html) (título "¡Bienvenido!", botón "Activar mi cuenta", icono de TuHoy y ayuda en info@tuhoy.com). [`scripts/apply_ghost_overrides.sh`](scripts/apply_ghost_overrides.sh) la copia sobre `invite-user.html` e `invite-user-by-api-key.html` de Ghost entrando al contenedor por `/proc/<pid>/root` (Ghost corre con el mismo usuario, uid 1000). Ghost lee la plantilla en cada envío, así que no hace falta reiniciar. El cron la vuelve a aplicar cada 10 minutos porque Coolify recrea el contenedor en cada despliegue (registro en `logs/overrides.log`). El asunto es "Te invitamos a unirte a TuHoy": el mismo script parchea `core/server/services/invites/Invites.js` y, como Ghost solo lo lee al arrancar, lo reinicia con SIGTERM (Docker lo levanta en unos segundos por `restart: unless-stopped`; el script espera a que tuhoy.com responda 200). Solo reinicia cuando el parche falta, es decir, una vez tras cada despliegue. Si Ghost se actualiza, revisa que las variables de la plantilla (`{{resetLink}}`, `{{ siteUrl }}`, `{{recipientEmail}}`) sigan existiendo.

**SPF:** `v=spf1 include:_spf.mx.cloudflare.net include:spf.brevo.com ~all`. Debe haber un solo registro SPF; si añades otro proveedor, agrégalo a este.

## Cloudflare

- DNS, HTTPS y túnel (`DNET-HOME`) para `tuhoy.com`.
- El origen recibe HTTP. Si Ghost (`url=https://tuhoy.com`) no sabe que la petición original era HTTPS, redirige en bucle (`ERR_TOO_MANY_REDIRECTS`). Las etiquetas Traefik del compose mandan `X-Forwarded-Proto: https`. Deja apagado el redirect HTTP→HTTPS de Coolify.
- Registros MX: `route1/2/3.mx.cloudflare.net` (los gestiona Email Routing; no los edites a mano).

## Copias de seguridad

1. Volumen de contenido de Ghost (`/var/lib/ghost/content`): imágenes, temas, ajustes.
2. Volumen o dump de MySQL (`/var/lib/mysql`).

En Coolify: TuHoy Ghost → Backups. Los scripts que modifican notas guardan además su propia copia en `data/backup-posts-*.json` (ignorada por git).

## Estructura del repo

```
docker-compose.yml   Stack de referencia (Ghost + MySQL + correo)
.env.example         Plantilla de variables
routes.yaml          Rutas de Ghost (sitemap de noticias)
ghost-hooks/         Parche para instalar temas de GitHub en Ghost 5
ghost-overrides/     Plantillas de correo propias que sustituyen a las de Ghost
themes/tuhoy/        Tema propio
scripts/             Edición diaria, redacción y mantenimiento
prompts/             Voz, ejemplos y prompts del redactor
brand/               Logo, icono e imágenes del perfil de X
data/                Estado y fixtures (lo sensible está en .gitignore)
public/, Dockerfile, nginx.conf   Portada estática anterior; ya no es el origen de tuhoy.com
```
