# HANDOFF — TuHoy — periódico digital

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
