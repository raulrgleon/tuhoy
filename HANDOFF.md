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
