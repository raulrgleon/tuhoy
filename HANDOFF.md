## Checkpoint TikTok posts públicos (2026-10-14 ~11:20 Chicago · Cursor)
- Raul: los posts no deben salir privados. Hecho en la cuenta y en Studio:
  - Cuenta **https://www.tiktok.com/@tuhoynoticias** ya no es privada (Private account off).
  - La Guaira photo `7696547300822224141` y joyas photo `7696546868259491086` → privacidad **Everyone** (globo, sin candado).
- TikTok **no deja** que una app sin auditar publique público. Hasta que aprueben Production, los posts **nuevos por API fallarán** mientras la cuenta esté pública. Los dos de ahora sí se ven.
- Production **TuHoy Publicador** `7696499756253153286` sigue en Draft: Login Kit + Content Posting Direct Post añadidos; falta vídeo demo + Submit for review.

## Checkpoint canal WhatsApp (2026-10-14 ~10:40 Chicago · Cursor)
- Raul pidió publicar las notas **automático** en el canal. **No se puede:** Meta no tiene API para canales. No usamos pasarelas no oficiales (riesgo de bloquear el 402).
- Alternativa segura en marcha: `scripts/whatsapp_channel.py`, `WA_MODE=email`, cron 08:00 Chicago, 2 notas de la mañana listas para pegar. Un correo por día a `WA_EMAIL_TO`. Canal: https://www.whatsapp.com/channel/0029Vb9BtwBA89MgSh7P3a45

## Checkpoint TikTok en marcha (2026-10-14 ~10:32 Chicago · Cursor)
- Pipeline **encendido**: `TT_MODE=api`, cron `*/15`, OAuth @tuhoynoticias (sandbox), dominio sandbox **tuhoy.com** verificado (TXT Cloudflare `c8c01520aca31860ee34b9b31f2a1e4c`; el TXT de Production `ac11199af2001dd305dd43c0edd1419a` sigue).
- Primeros posts reales (privados, app sin auditar; cuenta TikTok en privado): joyas/ancianas `6acf60daaea50d00012a981c` (`p_pub_url~v2.7696546775800825869`) y La Guaira `6acf619aaea50d00012a983d` (`p_pub_url~v2.7696547254538422285`). PNG se convierte a JPEG porque TikTok no tira de PNG.
- Siguiente nota automática: la de las **12:00 Chicago** (misma cola que X; 1 cada 15 min).
- Claves activas = sandbox (`TT_CLIENT_KEY` prefijo `sb`). Production en `.env` como `TT_PROD_*` (app Production sin Guardar: falta vídeo demo). Tokens en `data/tt_auth.json` (gitignore). No hay secretos en git.

## Checkpoint TikTok target user (2026-10-14 ~10:20 Chicago · Cursor)
- El texto de TikTok tras Continue era **éxito**: «Target user was successfully added. Navigating back to TikTok for Developers».
- **@tuhoynoticias** quedó como target user del sandbox (añadido 14-oct 10:19 AM). No es un error.
- Sandbox **TuHoy sandbox** `7696490949345773586`: Login Kit + Content Posting API, Direct Post **on**, redirect `https://tuhoy.com/`, categoría News, TOS/privacidad/web tuhoy.com, icono 1024. Ámbitos incluidos: `user.info.basic` (Login Kit) y `video.upload` (Content Posting). TikTok no lista `video.publish` en el portal.
- Hecho después: OAuth sandbox, `TT_MODE=api`, dominio sandbox verificado y primer post. Hasta la auditoría los posts salen **privados**.

## Checkpoint TikTok developer app (2026-10-14 ~10:20 Chicago · Cursor)
- App **TuHoy Publicador** en developers.tiktok.com: id `7696499756253153286`, tipo Other, dueño Individual, categoría News.
- Dominio **tuhoy.com** verificado (TXT Cloudflare `tiktok-developers-site-verification=…`, record `ac11199af2001dd305dd43c0edd1419a`). SPF/Brevo TXT intactos.
- En Production (borrador, sin Guardar: TikTok exige vídeo demo): Login Kit + Content Posting API, redirect `https://tuhoy.com/`, TOS/privacidad/web tuhoy.com, icono 1024.
- Claves de Production en `.env` (`TT_CLIENT_KEY`/`TT_CLIENT_SECRET`); `TT_MODE` sigue `off`. No están en git.

## Checkpoint TikTok automático (2026-10-14 ~10:05 Chicago · Cursor)
- Raul pidió el mismo ritmo que X/Facebook/Instagram: **un post por nota**. `scripts/tiktok_posts.py` lee `x_queue.json`, sube la foto + pie, cron */15, `TT_MODE` (ahora `off` hasta OAuth). Tests 4/4. GitHub `34996b7`.

## Checkpoint TikTok @tuhoynoticias (2026-10-14 ~09:57 Chicago · Cursor)
- Cuenta **https://www.tiktok.com/@tuhoynoticias**. Bio: «Las noticias que importan, en español.» Tema 1.5.4 (pie, notas, boletín). No es el TikTok personal.

## Checkpoint canal de WhatsApp (2026-10-14 ~09:40 Chicago · Cursor)
- Raul creó el canal **TuHoy**: https://www.whatsapp.com/channel/0029Vb9BtwBA89MgSh7P3a45
- Tema 1.5.3: pie y final de cada nota. `/contacto/` y el boletín también. El chat `wa.me/14028240388` sigue para avisos; el canal no es un chat.
- No invitar contactos personales. Publicar 1–2 notas al día en el canal (se pega a mano hasta que haya automatización).

## Checkpoint docs alineados al vivo (2026-10-13 ~15:15 Chicago · Cursor)
- Rechequeo: `/noticias-google/` 200 (100 notas), `/news-sitemap.xml` → 301 a esa ruta, `facebook.com/tuhoynoticias` 200, tuhoy.com enlaza esa URL, `/venezuela/` 200.
- HANDOFF del estudio, README ya en `64aec40`, `.env.example` (URL pública de Facebook) y canvas `tuhoy-estudio.canvas.tsx` coinciden con eso. Search Console: enviado `https://tuhoy.com/noticias-google/` el 13-oct ~15:16 (lectura de Google aún pendiente).
- Workspace repo-tuhoy no se pudo actualizar: workspace.dnet.llc pide login y no hay sesión ni acceso a Postgres.

## Checkpoint Facebook tuhoynoticias + sitemap Google News (2026-10-13 ~15:10 Chicago · Cursor)
- Página de Facebook: usuario **tuhoynoticias**. Pública: https://www.facebook.com/tuhoynoticias (Graph `username` confirmado). Tema 1.5.2 y boletín apuntan ahí. No guardar la contraseña de Facebook en el repo ni en memoria.
- Mapa Google News: Ghost 6 intercepta `*.xml` como archivo estático (`File not found`). Ruta nueva **`/noticias-google/`** (XML, 100 notas). Cloudflare 301 desde `/news-sitemap.xml` y `/news-sitemap.xml/` (ruleset `6e2b45f196854712b208b16e9c8e8392`). `/venezuela/` sigue 200.

## Checkpoint estudio completo (2026-10-13 ~15:00 Chicago · Cursor)
- Pedido de Raul: revisar sitio, publicaciones, envíos, recibos y colaboradores. Canvas: `tuhoy-estudio.canvas.tsx`.
- **En marcha:** Ghost 6.69.0 200; ediciones 06 y 12 de hoy con 5 notas y foto cada una; `X_MODE`/`FB_MODE`/`IG_MODE`=api publicando 1/pasada; Brevo transaccional; Mailgun `mg.tuhoy.com` listo; articulos@ timer activo; invitaciones ES aplicadas; 22 tests OK.
- **Resuelto 15:10:** `/news-sitemap.xml/` 404 → **`/noticias-google/`** 200 (100 notas, text/xml) + Cloudflare 301. Facebook vanity **https://www.facebook.com/tuhoynoticias**.
- **Medio (sigue):** Ghost timezone `America/New_York` vs cron Chicago; 60 notas `#revisar`; primer boletín real 14-oct 07:00 a 2 suscriptores.
- **Bajo (sigue):** IMAP TimeoutError esporádico; `pendientes` de X no se limpian tras `tweet_id`.
- Colaboradores: Raul Owner; Kastle/Tatiana/Richard Contributor. Kastle publicó (vía correo + confirmación) el ciberataque en Francia. YouTube aplazado.

## Checkpoint Instagram @tuhoynoticias (2026-10-13 · Cursor)
- Cuenta nueva profesional (Business), usuario **@tuhoynoticias**, nombre TuHoy, correo info@tuhoy.com, teléfono 4028240388, categoría News & media website, bio «Las noticias que importan, en español.» + tuhoy.com. No se usó @raul_garcia_us ni @rgcar.run. Sin publicaciones ni invitaciones.
- Enlace público en el tema 1.5.1 (pie y final de cada nota) y en el boletín. El sitio web del perfil de Instagram solo se edita desde la app.
- `scripts/instagram_posts.py`: mismos posts que X (foto de Ghost + pie con URL). **`IG_MODE=api`** (Raul lo pidió el 13-oct ~14:28 Chicago). Cron cada 15 min. `data/ig_queue.json` en gitignore.
- Raul ligó @tuhoynoticias a la página Facebook TuHoy. Graph confirma `instagram_business_account` id **17841472487834968** / username tuhoynoticias. App TuHoy Publicador: caso de uso «Administrar mensajes y contenido en Instagram». Token de página renovado (sin caducidad) con `instagram_basic` + `instagram_content_publish` además de los de Facebook, autorizado solo a página TuHoy, BM TuHoy y cuenta tuhoynoticias.
- Primer post 13-oct 14:29 Chicago: id Graph `18113286848606782`, permalink https://www.instagram.com/p/Decj_SNjrUU/ (nota del campo / inmigrantes). Una por pasada, nada con más de 2 h de retraso.
- Foto de perfil de Instagram: el navegador no puede subir archivos; Raul puede ponerla desde el móvil.
- Enlace social en la página de Facebook TuHoy: Instagram **tuhoynoticias**. URL de Facebook: **facebook.com/tuhoynoticias**. Dirección física vacía.

## Checkpoint plan para llegar a más personas, semana 1 (2026-10-13 · Cursor/Claude)
- Raul pidió un plan para llegar a más gente y eligió hacer «todo lo de esta semana». Punto de partida: 2 suscriptores (Raul y un lector), Facebook con 0 seguidores y 10–50 visitas reales al día (Cloudflare Web Analytics, que ya estaba activa desde el 29-sep).
- Tema 1.5.0: botones de WhatsApp, Facebook y X en cada nota; caja de suscripción `data-members-form="signup"` al final (oculta para miembros); enlaces a la página de Facebook en la nota y el pie.
- `scripts/daily_digest.py`: boletín «Lo que importa hoy» a las 07:00 Chicago como post de solo correo (`#boletin`) por Ghost + Mailgun. `DIGEST_MODE=on` en `.env`. Prueba enviada y entregada solo a Raul (post `6ace6f25099bf60001e24501`, segmento `label:prueba-boletin`). El primer envío real sale el 14-oct a las 07:00.
- `scripts/indexnow.py` + Worker de Cloudflare `tuhoy-indexnow` (ruta `tuhoy.com/<clave>.txt`, id de ruta `21fe2733dff04632b0c148828397028a`). Se avisaron las 139 notas (202). Cron cada hora a los :05.
- No se pudo: activar Crawler Hints (la API no lo permite con la clave global y el panel pide iniciar sesión) ni dar de alta en Bing Webmaster (pide iniciar sesión; IndexNow cubre la indexación). Google News ya no admite altas manuales.
- Pendiente de los pasos siguientes del plan: guías propias de inmigración, noticias locales y promoción pagada opcional. Canal de WhatsApp hecho el 14-oct.

## Checkpoint notas sin foto (2026-10-13 · Cursor/Claude)
- Problema: 4 notas publicadas sin portada, así que Facebook (y X) mostraban el logo. Tres eran de Univision, que sirve sus fotos en AVIF: Ghost 6 las rechaza (415) y `source_photo` las etiquetaba como JPEG. La cuarta (`voz-baja-...`) tenía como fuente businesswire, que da 403.
- Pillow 12.3.0 instalado para raul en `~/.local/lib/python3.14/site-packages` (wheel descomprimido, sin pip en el servidor). El cron usa `/usr/bin/python3` como raul, así que lo ve.
- `daily_edition.py`: nueva `ghost_image()`, que deja pasar JPEG, PNG y WebP y convierte el resto a JPEG. En `publish_item`, si la foto de la fuente no sube se prueba Commons, y **sin foto no se publica** (`skip sin foto`).
- `use_source_photos.py --sin-foto [--dry-run]`: rellena solo las notas publicadas sin portada. Aplicado: 3 de Univision con su foto («Foto: Univision.») y `voz-baja-...` con una foto de dominio público de campos de lechuga (Charles O'Rear, NARA).
- Tema 1.4.9: `og:locale` cambió de `es_US` a `es_LA`, porque Facebook rechazaba el scrape por ese valor. Se volvieron a leer las 4 URL en Facebook; el post del ICE ya muestra su foto.

## Checkpoint página de Facebook (2026-10-13 · Cursor/Claude)
- Pedido de Raul: publicar en Facebook como en X. No había página; se eligió la configuración guiada en el navegador con su sesión.
- Página "TuHoy" creada (ID `1408807572318535`): categoría "Sitio web de noticias y medios de comunicación", web, teléfono +1 4028240388 e info@tuhoy.com. Sin foto de perfil ni portada todavía (el navegador no puede subir archivos). No se invitó a amigos ni se conectó WhatsApp.
- App de Meta "TuHoy Publicador" (App ID `1625626036013171`, sin portafolio comercial) con `pages_show_list`, `pages_read_engagement` y `pages_manage_posts`, autorizada solo para la página TuHoy (no para Cheap Energy, Truckwls, De To' ni RG Motors).
- Token de usuario ampliado (caduca el 12-dic-2026), del que sale el token de página sin caducidad (`debug_token`: tipo PAGE, `expires_at` 0). Guardado solo en `.env` como `FB_PAGE_TOKEN`, junto a `FB_PAGE_ID`. Raul aprobó activarlo: `FB_MODE=api`. Primer post: 1408807572318535_122104668867504854 (12:15 Chicago, nota de ICE en Houston), público y con vista previa con foto.
- `scripts/facebook_posts.py` nuevo: lee `data/x_queue.json` (solo lectura) y publica a su hora el mismo texto con el enlace en `/{page}/feed`. Un post por pasada como máximo y ninguno con más de 2 h de retraso. Registro en `data/fb_queue.json` (ignorado por git). Cron cada 15 min en `install_daily_cron.sh`.

## Checkpoint portada, notas sin desarrollo y ajustes en Ghost 6 (2026-10-13 · Cursor/Claude)
- Pedido de Raul: "Feature this post" no cambiaba la portada; notas sin desarrollo; revisar todo tras su actualización a Ghost 6. Diagnóstico entregado primero; Raul aprobó todos los arreglos.
- Portada (tema 1.4.9): `home.hbs` ordena las destacadas por `updated_at desc`; la última que se destaca abre la portada. Antes eran las 4 más recientes por fecha de publicación, y la edición autodestacaba 3 al día.
- `daily_edition.py`: ya no destaca; si el redactor falla, no publica (`skip sin desarrollo`), sin respaldo extractivo. France 24 sale de las fuentes (403). La etiqueta Inmigración solo se pone por el titular o por términos fuertes en el texto (`INMIG_TEXT_RE`).
- `writer.py`: `MIN_WORDS = 200`. `flagged` solo por afirmaciones sin sustento (`thin_sources` ya no pone `#revisar`). `x_posts.py`: las `#revisar` también salen en X.
- Ghost 6: `apply_ghost_overrides.sh` usa `core/server/lib/mail/templates/` y `services/invites/invites.js`, con alternativa para Ghost 5. Explore solo se parchea si existe `openExploreWindow`, que ya no existe en Ghost 6. `patch_invite_permissions.py` se basa en regex y funciona en 5 y 6. Aplicado por el cron a las 16:40 UTC (reinicio de unos 8 s). `test_invite_permissions.cjs`: 8/8 en la copia de Ghost 6.
- Contenido: 4 notas `#resumen-automatico` reescritas con fuentes alternativas mediante `rewrite_published.py --slug … --source URL` (opción nueva; copias en `data/backup-posts-17919097*.json`). La de Gaza (BBC) pasó a borrador por falta de fuente. La de Corea quedó con la etiqueta Mundo.
- Verificado: 19 pruebas unitarias OK; dry-run de 5 notas sin ★; web, /ghost/, /venezuela/ y /cuba/ responden 200; el asunto y la plantilla de la invitación están en español.
- Se incluyen en el commit los cambios de Codex del 12-oct que estaban sin commit (`ghost:6.69.0` y paginación de `limit=all`).
- Pendiente: las 5 notas `#revisar` breves de 177 a 237 palabras siguen igual; no se ha probado el envío de una invitación real.

## Checkpoint Ghost 6.69.0 (2026-10-12 - Codex)
- Objetivo completado: actualizar TuHoy de Ghost 5.130.6 a Ghost 6.69.0 tras validar compatibilidad, respaldo restaurable y migracion sobre una copia.
- Fuente viva: Dell /home/raul/tuhoy, rama main, commit fdb667d76772a6169b9b884bf2a216096c41046c. El arbol ya tenia cambios sin commit unicamente en HANDOFF.md al iniciar; se conservaron.
- Estado comprobado: Ghost 5.130.6, MySQL 8.0, ambos contenedores healthy; volumenes separados y persistentes. Sitio y /ghost/ devolvieron HTTP 200.
- Ghost Admin API informa 131 posts, 4 paginas, 4 usuarios y 16 tags. Ghost 6 limita las respuestas API a 100 elementos por pagina; las seis solicitudes limit=all encontradas en automatizaciones/scripts ahora recorren todas las paginas.
- Tema tuhoy declara Ghost >=5.0.0; GScan 6.6.1 termino con una advertencia no fatal por falta de soporte de fuentes personalizadas. Pruebas existentes scripts.test_email_articles: 16 OK.
- Fuente primaria consultada: Ghost 6.69.0 es la release estable mas reciente y aparece en el indice oficial de Docker; requiere Node 22 y sigue con MySQL 8. Se actualizo el cliente API antes de subir la imagen.
- Codigo actualizado en scripts/daily_edition.py: las consultas limit=all ahora recorren todas las paginas de 100 y fallan si una pagina posterior falla, evitando resultados parciales silenciosos en Ghost 6.
- Archivo nuevo scripts/test_ghost_pagination.py: tres pruebas de filtros/paginacion, compatibilidad con llamadas existentes y error en paginas posteriores. Resultado real: unittest discover -s scripts -p test_*.py, 19 OK; compileall y git diff --check sin errores. Prueba contra Admin API de produccion: 131/131 posts leidos, total informado 131.
- Respaldo R2/restic cifrado creado: snapshot 34d51513, host tuhoy-pre-upgrade, tag tuhoy-pre-ghost-6.69.0-20261012. Incluye repo con cambios locales, dump MySQL (75 tablas), archivo de contenido Ghost (229,698,977 bytes), docker-compose de Coolify y .env de Coolify; los archivos sensibles viajan cifrados por Restic.
- Integridad real: gzip/tar y SHA-256 verificados antes y despues; restic check --read-data reviso 23/23 packs y no encontro errores; se restauraron 737 archivos/dirs (229.449 MiB) a una carpeta temporal y se verificaron hashes y compresion.
- Prueba de migracion aislada sobre copia recuperada del snapshot: Ghost 6.69.0, Node v22.23.3 y MySQL 8.0; portada y /ghost/ respondieron HTTP 200, cero errores de migracion y base preservo 131 posts + 4 paginas (135 filas combinadas). Red, contenedores y volumenes de prueba se limpiaron.
- Despliegue: Coolify compose y docker-compose.yml del proyecto fijados a ghost:6.69.0; se recreo solo Ghost con --no-deps. Contenedor Ghost bceac4bf1b6c8fa9c94b194350065df3d4d2bebc18c65d31a0b9f2ea715c4f2b, image ID sha256:55131b90d48c3cecae6c085f873b2067542ababd286b12d08474b2b34328e266, version 6.69.0 y Node v22.23.3; estado running/healthy. MySQL no se recreo: conserva ID 27963b698e4eae7094945cbba62967666ce929ee782def4f684d42b616192a6e, healthy.
- Verificacion posterior: https://tuhoy.com/ y /ghost/ devuelven HTTP 200; peticiones internas con cabeceras forwarded HTTPS devuelven 200/200; Ghost Admin API pagina correctamente y devuelve 131 posts, 4 pages, 4 users y 16 tags; cero errores de migracion. Se conservaron url, transporte SMTP de Brevo y su host/puerto. No se envio correo ni se cambio la configuracion de newsletters.
- Cambios locales sin commit: README.md, docker-compose.yml, scripts/daily_edition.py, nuevo scripts/test_ghost_pagination.py y HANDOFF.md (incluye el checkpoint previo ya existente de newsletter). Rama main, commit base fdb667d76772a6169b9b884bf2a216096c41046c. No hubo commit, push ni cambios a memoria global.
- Resultado final: 19 pruebas unitarias OK; compileall y git diff --check OK; GScan Ghost 6 solo advierte que el tema no declara soporte de fuentes personalizadas; sitio y tema activo responden bien. No quedan pasos operativos pendientes.

# HANDOFF — TuHoy — periódico digital

## Checkpoint de newsletter (2026-10-12 · Codex)
- Objetivo actual: conectar Mailgun con Ghost para habilitar el envío de newsletters, verificándolo con una prueba individual a Raul y sin lanzar una campaña a los suscriptores.
- Repositorio en `dnet.llc`: `/home/raul/tuhoy`; rama `main`, commit `fdb667d`. Estado al retomar: solo `HANDOFF.md` modificado sin commit; el mismo cambio está en `/tmp/tuhoy-newsletter-checkout`.
- Código/configuración revisados previamente: Ghost 5 usa Brevo SMTP en `docker-compose.yml` para correo transaccional; el envío masivo de Ghost se configura aparte con Mailgun.
- Mailgun: plan Free ($0/mes en la última consulta previa a la prueba; uso entonces `1 / 3,000`). Dominio `mg.tuhoy.com` en región US; SPF, DKIM y tracking verificados. No se cambió el plan.
- DNS: SPF TXT para `mg.tuhoy.com`, DKIM TXT para `pic._domainkey.mg.tuhoy.com`, y CNAME `email.mg.tuhoy.com` → `mailgun.org`, DNS-only. No se añadieron MX ni se tocó el SPF raíz de Brevo.
- Ghost Admin, tras iniciar sesión: Newsletter sending está Enabled; existe la newsletter `TuHoy` con 2 suscriptores y 0 entregas de campañas; Mailgun muestra “Mailgun is set up”.
- Mailgun > Domain Settings > Sending Keys: se creó una clave de envío etiquetada `Ghost newsletter — TuHoy`, limitada al dominio `mg.tuhoy.com`; el valor secreto no se guardó en archivos ni en el checkpoint.
- Ghost Admin aceptó la región US y el dominio `mg.tuhoy.com`; tras guardar, el estado visible cambió a “Mailgun is set up”.
- Ghost guardó el borrador `Prueba técnica de envío — no publicar` (ID `6acc61c591f7ad00010043ab`) con texto de prueba explícito; permanece como borrador sin publicar. Desde Preview se envió un test solo a Raul.
- Se envió desde Preview un correo de prueba a la dirección personal de Raul: Ghost confirmó “Sent”; Mailgun registró `accepted` y después `delivered` para `mg.tuhoy.com`. No se envió a los 2 suscriptores ni se lanzó una campaña.
- Sin cambios al código de aplicación ni escrituras directas a la base de datos; Ghost Admin guardó el borrador descrito arriba. No se modificó la memoria global.
- Verificaciones reales de este bloque: Ghost muestra “Mailgun is set up”, el editor muestra “Draft - Saved” y luego “Sent” para el test; Mailgun registra `accepted` a las 00:28:16 y `delivered` a las 00:28:22 (12-oct-2026, hora de la cuenta). La newsletter `TuHoy` conserva 2 suscriptores y 0 entregas de campañas. No se ejecutaron pruebas de código.
- Siguiente paso: preparar el contenido editorial de la primera newsletter y revisar destinatarios antes de cualquier publicación/envío; el borrador de prueba queda sin publicar.

## Último checkpoint
- **Fecha / agente:** 2026-10-11 (UTC) · Cursor (Claude), en el Dell `/home/raul/tuhoy`.
- **Objetivo pedido por Raul:** tres ediciones al día (6, 12 y 18 h Chicago, ~5 notas cada una), más fuentes en
  español (Univision, Telemundo, CNN en Español, EFE, AP, Voz de América) y de Venezuela y Cuba, mismas reglas
  (nada inventado, sin repetidas, `#revisar` para lo dudoso) y un post de X por cada nota. "No rompas nada."
- **Rama:** `main`.

## Qué se hizo
- `scripts/daily_edition.py`: ranuras por edición `--inmig 2 --general 2 --paises 1`; fuentes por RSS o sitemap de
  Google News (CNN en Español, Univision, Telemundo); filtro de antigüedad 48 h; fuera vídeos/directos/espectáculos;
  orden de fuentes sorteado e intercalado; menú de la página recortado antes del titular; descarta textos con restos
  de código HTML; ranura de países con etiqueta Venezuela/Cuba según la fuente; `--dry-run` sin redactar ni publicar.
- `scripts/x_posts.py`: corre tras cada edición, un post por nota nueva, reparto hasta la siguiente edición, conserva
  pendientes (antes se sobrescribían), cupo de enlaces `X_LINKS` por día.
- `scripts/install_daily_cron.sh`: cron cada hora con filtro 06|12|18 de Chicago → edición y luego `x_posts.py`.
  Eliminada la tanda fija de las 07:00. Cron instalado.
- `prompts/tweets.md`, `README.md`, `.env.example` (`X_SPACING`; fuera `X_HOURS`).

## Pruebas reales
- `daily_edition.py --dry-run` ejecutado varias veces: 5 notas por edición, etiquetas correctas, sin publicar.
- Planificación de `x_posts.schedule` probada con horas simuladas; `x_posts.py --dry-run` redactó un post real sin
  tocar `data/x_queue.json` (comprobado con `cmp`).
- Filtro horario del cron simulado con `sh` para 06/07/12/18/23.
- **La primera edición real con el código nuevo será la de las 06:00 de Chicago del 2026-10-11.**

## Descartado
- EFE y AP: 403 a cualquier lectura automática. Voz de América: sin publicaciones desde marzo de 2025.
  Cubanet y Diario de Cuba: no dejan leer el texto. Google News: enlaces cifrados.

## Siguiente paso
- Revisar `logs/daily.log` tras las ediciones del 2026-10-11 (6, 12 y 18 h) y las líneas `[x]` de los posts.
- Vigilar el gasto de X (~15 posts/día, 2 con enlace ≈ $18/mes).

## Diagnóstico TikTok · 2026-10-15 06:53 Chicago · Codex
- Pedido: revisar por qué no publica; solo diagnóstico, sin cambios de código/configuración ni publicaciones.
- Fuente real: Dell /home/raul/tuhoy main 46d5979. Existían sin seguimiento brand/tiktok-demo.mp4, content/ y scripts/publish_guides.py; preservados.
- TT_MODE=api y credencial sandbox; autorización presente con video.publish y refresh disponible. No se imprimieron ni renovaron credenciales. Expiración registrada 15-oct 15:29 UTC; no es la causa de los rechazos de esta mañana.
- Cron TikTok instalado cada 15 min. Logs 06:15, 06:30 y 06:45 Chicago: HTTP403 unaudited_client_can_only_post_to_private_accounts. Historial local conserva dos éxitos, ambos 14-oct; hoy ninguno.
- Cola a las 06:53: un pendiente dentro de ventana, cuatro futuros y catorce no publicados fuera de ventana de dos horas. No reencolar sin revisión editorial.
- Documentación oficial de TikTok Content Sharing Guidelines cotejada: app sin auditar exige cuenta privada y SELF_ONLY. También excluye utilidad exclusiva interna y exige selección de privacidad/consentimiento por usuario. No basta cambiar claves: revisar elegibilidad y UX antes de prometer aprobación de Production.
- El script intenta fallback privado; esto tampoco permite publicar con cuenta pública. No se cambió privacidad ni se ejecutó publicador. Siguiente paso: decidir flujo oficial compatible (publicación manual o integración aprobada); evaluar elegibilidad del producto antes de presentar auditoría. Estado del portal Production no comprobado en esta sesión.

## Diagnóstico aviso email-articles · 2026-10-15 ~07:10 Chicago · Codex
- Pedido: revisar Failed to start tuhoy-email-articles.service. Solo lectura operativa; sin reiniciar servicio, procesar manualmente mensajes, enviar correos ni cambiar código/configuración.
- Servicio oneshot disparado por timer cada 60 s tras ejecución. Última ejecución observada 12:08:57 UTC terminó status=0/Intake completed; inactive(dead) es normal entre ejecuciones.
- Journal desde 14-oct: 1.897 ejecuciones completas, 24 TimeoutError y 3 gaierror. Último fallo 15-oct 10:25:55 UTC (05:25 Chicago), seguido de éxitos. Registro solo guarda clase de excepción: no permite distinguir qué conexión IMAP/Ghost/SMTP agotó tiempo.
- SQLite abierto mode=ro: dos submissions draft, una published, tres expired; 13 mensajes outbox marcados enviados y cero pendientes. No se leyeron contenidos/destinatarios ni tokens. Expired significa confirmación de autoría pendiente que superó 48 h; no equivale a un artículo confirmado perdido.
- Código conserva cursor y procesa de nuevo tras fallo; requiere confirmación del autor antes de crear borrador Ghost. Estos datos no prueban recepción de un correo concreto sin cotejarlo.
- Siguiente paso recomendado: instrumentar etapa del fallo sin datos personales, evaluar reintento acotado de red y alertar por fallos consecutivos. Si se investiga un artículo, localizarlo con remitente/fecha y no reactivar expirados ni publicar sin autorización.

## 2026-10-17 · Codex · portada con vigencia · previo al despliegue
- Autorización expresa de Raul para desplegar solo ajuste de portada, preservando funcionalidad y trabajo existente.
- Base main 46d5979; cambios previos HANDOFF.md y archivos sin seguimiento conservados. Tema 1.5.5 preparado en home.hbs, package.json, partials/opening.hbs y partials/story-lead.hbs.
- Respaldo del tema real activo, tema del repo y documentos: /home/raul/tuhoy-theme-backup-20261017. Verificado home.hbs presente. API de lectura de temas no permitió acceso; respaldo obtenido del volumen del proceso Ghost sin cambios al servicio.
- GScan 6.6.1 sin errores (advertencia de fuentes personalizadas), sintaxis Handlebars y diff --check OK; lectura Ghost HTTP 200 con cuatro noticias del 17-oct mediante filtro de 48 h y exclusión #boletin.
- Siguiente: activar tema y verificar HTML real, enlaces, imágenes, secciones y diseño. No push ni memoria global.

### Resultado del despliegue de portada · 2026-10-17
- Tema 1.5.5 subido y activado por scripts/upload_theme.py: HTTP 200/200. No hubo reinicio ni cambios a artículos, base de datos, cron o credenciales.
- HTTPS público: portada, cuatro artículos de apertura y foto principal respondieron HTTP 200. HTML real muestra cuatro noticias del 17-oct, fecha antes del titular y secciones/boletín presentes. Revisión visual de escritorio confirmó imagen, columna lateral y fecha/titular correctos. Captura local /tmp/tuhoy-portada-publicada-20261017.png.
- Incidencia de verificación local: urllib de macOS no encontró CA local; se verificó con curl manteniendo validación TLS. No se desactivó HTTPS.
- No se simuló ausencia de noticias en producción ni se verificó visualmente móvil en este bloque. GScan previo sin errores; advertencia existente de fuentes personalizadas.
- Prioridad reiterada por Raul: conservar funcionamiento, cambios acotados y respaldo antes de desplegar. Backup del tema activo en /home/raul/tuhoy-theme-backup-20261017; para revertir, restaurar tema desde active-theme y subirlo mediante upload_theme.py.
- Cambios sin commit de esta tarea: home.hbs, package.json, partials/story-lead.hbs, nuevo partials/opening.hbs, README y este HANDOFF. Trabajo previo conservado; sin commit/push ni modificación de memoria central. Siguiente: ningún paso requerido para activar; commit/push solo con autorización.

## 2026-10-17 · Codex · diagnóstico TikTok
- Revisión sin cambios operativos: TT_MODE api, cliente sandbox, cron cada 15 min; token vigente hasta 18-oct. creator_info confirmó @tuhoynoticias y opciones PUBLIC_TO_EVERYONE/MUTUAL_FOLLOW_FRIENDS/SELF_ONLY. No se imprimieron secretos.
- Cola registra dos posts del 14-oct; log confirma 10:32 y 10:34 Chicago. 216 de 218 errores de publicación contienen unaudited_client_can_only_post_to_private_accounts. Último observado 17-oct 11:30, incluso tras reintento SELF_ONLY.
- Documentación oficial Content Sharing Guidelines: una app no auditada requiere cuenta privada además de post SELF_ONLY. La cuenta devuelve opciones de cuenta pública. Coincide con checkpoint de cambio a cuenta pública del 14-oct.
- Script anuncia que saldrá privado antes de confirmar; esa línea no prueba éxito. Notas fallidas dejan de ser elegibles tras 2 h.
- Sin publicar ni cambiar código, privacidad o configuración; solo checkpoint. Próximo paso: propietario decide si autoriza cuenta privada (afecta visibilidad del perfil y publicaciones) o continúa aprobación para mantener cuenta pública. No se promete aprobación.

## 2026-10-17 · Codex · conexión Buffer / TikTok
- Autorización de Raul para conectar solo TikTok, crear clave limitada de 30 días y configurar servidor; plan Free. Buffer confirmó canal @tuhoynoticias conectado, sin desconexión. Correo verificado por propietario. No se guardaron contraseñas ni claves en repo, logs o memoria.
- Clave encriptada con systemd-creds en /home/raul/.config/tuhoy/buffer-api.cred; solo account:read/posts:read/posts:write, vence 16-nov-2026. Se entrega al proceso por LoadCredentialEncrypted; sin secreto persistente en texto plano.
- Nuevo scripts/buffer_tiktok.py: canal fijo, comprueba identidad y conexión, reutiliza X_QUEUE sin modificar, una noticia por pasada y ventana 2 h. Estado atómico, lock, deduplicación contra Buffer y pausa ante resultado incierto/error; distingue sending/sent. Ejecuciones ociosas no llaman API.
- Timer systemd tuhoy-buffer-tiktok.timer activo, cada 15 minutos; servicio corre como raul. Unidades copiadas a deploy/. Se retiró solo cron tiktok_posts.py, copia de crontab en /home/raul/tuhoy-buffer-backup-20261017. Resto de cron intacto. .gitignore excluye estado y lock.
- Pruebas reales: cinco casos nuevos (cuenta incorrecta, job incierto, duplicado remoto, timeout, aceptación sin confirmación) y cinco existentes TikTok: 10/10 OK; diff --check OK. Consulta desde credencial systemd comprobó conexión. No nuevas dependencias de producto.
- Prueba real: noticia de Matanzas enviada mediante API Buffer, recibida en modo automatic, estado sending sin error a las 12:00 Chicago; pendiente de confirmar sent/enlace público antes de afirmar éxito final. Si falla, el sistema pausa nuevos envíos.
- Trabajo previo de portada y archivos no rastreados conservado. Sin commit/push ni actualización memoria global. Próximo paso: confirmar resultado de prueba, documentarlo aquí. Renovar clave antes de vencimiento.

### Confirmación final Buffer · 2026-10-17 12:02 Chicago
- Primera publicación confirmada como sent por API Buffer y como Post sent en UI: https://tiktok.com/@tuhoynoticias/video/7697682797913263373 (noticia de Matanzas). Estado local reconciliado mediante --reconcile-only, sin enviar otra noticia.
- Timer activo y siguiente ejecución observada 12:15 Chicago; las futuras ejecuciones aún no fueron observadas en este bloque. Prueba real demuestra creación y finalización del primer envío, no garantiza futuras publicaciones.
- 10 pruebas OK tras ajuste de consumo de API y opción --reconcile-only; diff --check OK. Credencial cifrada fuera del repo, portapapeles limpiado. Sin push/commit ni cambios a memoria central.
- Siguiente: revisar journal del servicio tras próximas ediciones y renovar clave antes del 16-nov-2026. Estado failed/rejected/submitting incierto bloquea nuevos envíos hasta revisión para evitar duplicados. No se recuperaron noticias antiguas masivamente.
# 2026-10-17 · Codex · formato combinado automático (en validación)
- Raul autorizó aplicar vídeo editorial combinado y exigió imagen en todas las escenas. Respaldo previo scripts/unidad/estado: /home/raul/tuhoy-video-backup-20261017. Se conservaron cambios anteriores. Timer pausado durante cambio, servicio inactivo antes de sustituir script.
- Nuevo tiktok_video.py genera 4 escenas verticales 1080x1920 con la imagen real del artículo en cada una, textos extractivos, fecha/crédito y voz sintética local. No inventa imágenes ni frases. Falta de imagen, texto suficiente o fallo de generación bloquea envío; sin fallback fotográfico.
- Runtime aislado /home/raul/.local/share/tuhoy-video/runtime: Piper 1.8.0, Pillow 12.3.0; voz es_MX-ald-medium (model card cita dataset Unlicense). FFmpeg y fuentes Liberation instaladas desde Ubuntu. pip se actualizó en venv tras detectar vulnerabilidades; pip-audit posterior: sin vulnerabilidades conocidas. Lock de dependencias en deploy/.
- Vídeos públicos en volumen Ghost content/media con nombres id+hash; solo artefactos de noticias públicas. Credenciales no cambiadas. URL valida HTTPS y origen; descarga de imagen limitada a 20 MB y ruta content/images. Estado/medios locales ignorados por Git.
- buffer_tiktok.py ahora envía asset video, metadata isAiGenerated true, conservando idempotencia/lock y canal fijo. Primer vídeo renderizado: Matanzas, 32.9 s, H264/AAC, 1080x1920; revisión de cuatro frames confirmó imagen en todos. Decodificación completa sin errores.
- 15 tests OK: 6 Buffer (incluye fallo render sin envío), 4 composición/validación y 5 TikTok existentes. diff --check OK.
- Pendiente validar borrador de vídeo en Buffer; lo bloqueó un envío fotográfico iniciado a las 12:15 por el timer anterior, aún sending. No reenviar ese contenido ni tocar su estado sin respuesta de Buffer. Reactivar timer tras validación. Sin commit/push/memoria central.

### Activación final del formato combinado · 2026-10-17 12:19 Chicago
- Buffer confirmó el envío anterior de las 12:15 como sent (7697686451848301838), sin duplicarlo. Se probó la generación de la noticia Cashea como borrador: API Buffer confirmó status draft, schedulingType automatic y asset video/mp4.
- Se eliminó únicamente ese borrador de prueba (respuesta DeletePostSuccess) y su registro local de prueba; X_QUEUE se conservó intacta, de modo que la noticia sigue elegible a su hora normal (16:15 Chicago). No se adelantó la publicación.
- Timer reactivado y active; siguiente ejecución observada 12:30 Chicago. Dry-run sin noticias elegibles: cero llamadas API. Las próximas noticias usarán vídeo editorial; no se publicó de nuevo Matanzas.
- Copia de seguridad y ruta de reversión: detener timer, restaurar buffer_tiktok.py desde /home/raul/tuhoy-video-backup-20261017 y reactivar timer. Conservar estado actual para no duplicar posts; no restaurar estado antiguo al revertir código.
- Confirmado: 15 tests OK, pip check OK, pip-audit sin vulnerabilidades conocidas, MP4 H264/AAC 1080x1920 32.9 s decodificado íntegro, imagen en las cuatro escenas y acceso público al archivo HTTP 200. Buffer aceptó un vídeo como borrador; publicación real futura del nuevo formato todavía no observada en este bloque.
- Sin commit/push ni cambios en memoria global. Preferencia duradera del usuario implementada: imagen del artículo en todas las escenas, sin fallback de solo foto si falla render. Voz local española mexicana, distinta a Paulina de la maqueta. README documenta funcionamiento, requisitos y limitaciones.

## 2026-10-17 · Codex · Kokoro Alex activado
- Raul eligió kokoro-alex tras escuchar muestras Dora/Alex y autorizó usarlo. Respaldo del renderer previo en /home/raul/tuhoy-kokoro-backup-20261017/tiktok_video.py; cambios anteriores preservados.
- Nuevo scripts/kokoro_voice.py usa Kokoro-82M ONNX v1.0, em_alex, idioma es, speed 1.0, CPU 2 hilos; cuatro WAV generados con un solo modelo cargado. Adaptador float32 para entrada speed del export. Valida audio finito/no silencioso y salida limitada al caché de vídeos.
- tiktok_video.py invoca el worker Kokoro, recalcula duraciones desde WAV e incluye versión de voz en hash/manifest para evitar reutilizar Piper. Imágenes en todas las escenas, diseño, canal y horario conservados; no se reenviaron noticias.
- Validación real: nuevo vídeo Matanzas generado y servido por HTTPS; decodificado completo sin errores. Manifest confirma kokoro-em_alex-v1 e images_per_scene=true. 15 tests OK, diff --check y pip check OK; pip-audit de runtime Kokoro sin vulnerabilidades conocidas. Lock y hashes añadidos a deploy/kokoro-*. Sin nueva API de pago.
- Timer pausado durante cambio y reactivado, active al cerrar. No se publicó de nuevo la noticia de prueba; futuros vídeos usarán Alex. Resultado de una publicación nueva en TikTok con Alex aún no observado en este bloque.
- Reversión: detener timer, restaurar solo renderer desde respaldo y reactivar; conservar estado para no duplicar. Piper permanece instalado para reversión, sin fallback automático entre voces. Sin commit/push ni cambios a memoria central.

## 2026-10-17 · Codex · publicación GitHub autorizada
- Raul pidió actualizar GitHub con el trabajo de esta sesión: portada vigente, integración Buffer, vídeo editorial con imágenes en todas las escenas y Kokoro Alex.
- Base main 46d5979; fetch confirmó HEAD y origin/main sin divergencia antes de commit. Revalidación de las 15 pruebas específicas OK y diff --check OK.
- Se incluyen únicamente código, tests, unidades, locks/hashes y documentación del trabajo autorizado. Se preservan sin añadir archivos previos no relacionados: brand/tiktok-demo.mp4, content/guias/ y scripts/publish_guides.py. No se publican colas, credenciales, modelos descargados ni cachés de vídeo.
- La memoria global no se modifica ni publica como parte de este commit de producto. Siguiente: verificar staged sin secretos, crear commit, push main y comprobar SHA remoto.

### Resultado GitHub
- Código y documentación publicados en main: f201e01380b412701ceb2be008fdd7e7bb064f8f. GitHub API confirmó ese SHA como cabecera remota tras push exitoso.
- 18 archivos, 15 tests específicos aprobados, revisión staged de valores secretos y rutas excluidas pasó. Quedaron únicamente los tres grupos previos sin seguimiento (demo, guías, publicador de guías), preservados fuera de este commit.
- No hubo despliegue adicional ni cambios a memoria global durante la publicación. Este registro documental cierra el checkpoint de publicación.

## 2026-10-17 · Codex · revisión SEO solo lectura
- Se revisaron portada, robots, sitemaps, 4 artículos de apertura, about, autor, categoría, canal Venezuela, URL inexistente y variantes HTTP/www. Sin cambios de configuración/código ni publicación; solo checkpoint.
- Bien: index/follow, canonical HTTPS sin www, lang es, H1 de artículo, descripción, JSON-LD Article con autor/fechas/imagen y BreadcrumbList. Sitemap general respondió y contenía 200 posts; URL inexistente respondió 404.
- Problemas comprobados: noticias-google incluye 100 URLs, 70 anteriores a ventana de 2 días, más antigua 11-oct (Google exige últimos 2 días); sitemap-news.hbs no filtra fecha. Seis cabeceras de sección y sus Más noticias enlazan a inicio en vez de categoría. http://tuhoy.com/ y https://www.tuhoy.com/ sirven 200 sin redirección, aunque canonical sí apunta al dominio HTTPS sin www. Tres de cuatro imágenes schema muestreadas son menores a 1200 px de ancho.
- No se accedió a Search Console ni se midieron Core Web Vitals; no se afirma cantidad indexada, posicionamiento ni tráfico. Próximo: priorizar ventana News, enlaces de secciones y redirecciones; luego imágenes y datos Search Console con autorización. No commit/push.

## 2026-10-17 · Codex · reparaciones SEO autorizadas
- Fuente main a3e3ba0; estado inicial HANDOFF.md modificado y archivos previos no rastreados conservados. Respaldo /home/raul/tuhoy-seo-backup-20261017 (tema, daily_edition.py, HANDOFF). Sin cambios a DB ni fechas/URLs de artículos.
- Tema 1.5.6 activado: upload/activate HTTP 200. sitemap-news.hbs filtra published_at >= now-2d, excluye #boletin y #resumen-automatico, limit 100. XML vivo: 30 noticias, todas dentro de 48 h; sitemap general preservado.
- Corregida colisión de helper url con hash de partial mediante section_url. Verificación HTML: seis cabeceras y Más noticias ahora apuntan a /tag/...; cada enlace dejó de volver a inicio.
- Configuración Traefik file-only limitada a tuhoy.com/www.tuhoy.com, sin reiniciar proxy ni tocar otros routers. HTTP y www devuelven 308 a https://tuhoy.com conservando path/query; HTTPS principal devuelve 200, sin bucles. Original de protocolo externo obtenido de CF-Visitor. Archivo fuente deploy/traefik-tuhoy-canonical.json y activo /data/coolify/proxy/dynamic/tuhoy-canonical.yaml; no existía regla previa. Reversión: retirar únicamente ese archivo dinámico.
- daily_edition.py ahora busca variantes srcset declaradas de la misma foto y verifica ancho real >=1200 si están disponibles. Límite tres candidatas, sin inferir URLs ni escalar. Fuentes de Cashea y Zelenskyy comprobadas: solo 960/1024 px disponibles mediante este mecanismo; no se alteraron fotos existentes ni se afirma resolver su resolución.
- Pruebas: 18 unittest OK (3 nuevas selección de imágenes + 15 existentes); diff --check OK; GScan sin errores, advertencia preexistente de fuentes personalizadas. Validación viva de XML, enlaces y redirecciones mediante HTTPS. No se comprobó indexación Search Console ni Core Web Vitals.
- Siguiente: registrar cambios autorizados en GitHub; para artículos con originales pequeños, obtener fotografías de mayor resolución con derechos adecuados. No actualizar memoria global automáticamente.

## 2026-10-17 · Codex · verificación propiedad AdSense
- Propietario mostró la pantalla de AdSense con identificador público de editor y métodos código/ads.txt/meta; continuidad del alta autorizada.
- Tema 1.5.7 añade google-adsense-account a head de default.hbs, usando identificador público de la captura. Se eligió solo meta para verificar propiedad sin cargar el script publicitario ni activar anuncios automáticos.
- Respaldo default-before-adsense.hbs en /home/raul/tuhoy-seo-backup-20261017. Upload/activate tema HTTP 200/200, diff --check OK; comprobado meta exactamente una vez en head de portada, about y artículo. Sin adsbygoogle.js en esas páginas.
- Pendiente acción en cuenta de AdSense: seleccionar Etiqueta meta, marcar que se colocó y Verificar; luego solicitar revisión. No se afirma propiedad verificada por Google ni aprobación del sitio. No se aceptaron acuerdos ni se tocaron datos de pago.
- Sin cambios a memoria central; cambios del tema se publican en GitHub conforme autorización persistente del propietario.

## 2026-10-17 · Codex · código AdSense instalado
- Propietario aportó el fragmento oficial de adsbygoogle.js para su editor público y pidió continuar la configuración. Tema 1.5.8 añade el script async crossorigin anonymous al head global, conservando meta de propiedad.
- Respaldo: /home/raul/tuhoy-seo-backup-20261017/default-before-adsense-script.hbs. Upload/activate HTTP 200/200; diff --check OK; portada, about y artículo respondieron 200 con una sola instancia del script dentro de head.
- El código permite servir anuncios según aprobación y ajustes de AdSense; no se afirma que ya se muestren ni se cambió la cuenta, ubicaciones, CMP o datos de pago. AdSense y contenido de terceros no se controlan desde la plantilla.
- Código y checkpoint se publican conforme autorización persistente de GitHub. Sin cambios a memoria global.
