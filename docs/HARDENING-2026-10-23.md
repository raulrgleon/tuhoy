# Controles editoriales y operación — 23-oct-2026

## Publicación

Noticias sensibles detectadas en titular original/redactado y entradilla requieren revisión humana en Ghost. El filtro cubre inmigración/ICE, elecciones, acusaciones/detenciones, salud, fallecimientos, guerra y otros términos de editorial_controls.py. No es infalible ni una corroboración independiente. Se mantiene deduplicación; los borradores retenidos cuentan dentro del cupo para no multiplicar gasto y notas pendientes.

Verificación de IA sin lista `unsupported` válida aborta. Factcheck desactivado obliga a revisión. No se publican noticias de prueba durante esta instalación.

## Imágenes

La foto del medio original solo se usa con permiso registrado para su URL exacta. Crear privadamente data/licensed-images.json (600), con objeto por URL y campos authorized=true, license, credit y evidence (URL HTTPS pública que justifique permiso real). No incluir secretos: crédito/evidencia pueden publicarse. Registrar un permiso no equivale a obtener derechos.

Commons exige licencia admitida y enlace; se rechazan licencias desconocidas, NC o ND. Imágenes de archivo se identifican como tales. Si no hay foto apta se crea un gráfico propio rotulado; no se fabrica una fotografía del hecho. La procedencia queda en data/image-provenance.jsonl (600, ignorada por Git). Si falla la producción de imagen, se omite la nota. No se revisaron ni borraron fotos históricas.

## Operación

Bloqueo exclusivo del kernel en data/daily-edition.lock, liberado al terminar o morir el proceso; no borrar ese archivo durante una ejecución. Se eliminó la expiración arbitraria de una hora.

Chequeo HTTP real interno de Ghost con Host y protocolo correctos, persistido en compose de referencia, compose activo y fuente del servicio Coolify. Solo se recreó Ghost; MySQL y las demás IDs no cambiaron. Timers de correo y Buffer activos, últimas ejecuciones success/0. Traducción permanece desactivada.

## Evidencia y límites

93 pruebas locales (una omitida por ausencia de Pillow), 104 en DNET sin omisiones. Solicitud real a IA editorial correcta sin crear artículos. Portada/RSS/admin HTTP200, inexistente404; Chromium390/1440 sin desbordamiento ni oscilación y artículo200. Salud positiva correcta y prueba negativa con puerto cerrado falló como corresponde. No prueba física Safari/iPhone, entrevista editorial completa con IA, envío nuevo a redes ni auditoría completa. Sin dependencias nuevas; no se realizó un nuevo análisis integral de vulnerabilidades.

## Recuperación

Respaldo local privado: /home/raul/tuhoy-hardening-backup-20261023, código anterior, compose/fuente Coolify y exportación SQL consistente antes del reinicio. No equivale a comprobar backup independiente. Revisar cambios posteriores antes de restaurar; revertir solo scripts/configuración afectados, manteniendo coherencia con fuente Coolify. No restaurar SQL/colas/estados sociales para revertir código. No retirar editorial_controls.py mientras daily_edition.py lo importe.

GitHub main conserva el tema1.7 e incorpora las reparaciones ya activas de Instagram/Buffer con sus pruebas. El checkout antiguo en DNET conserva cambios ajenos y no se hizo reset/pull. La siguiente edición normal conserva horario; el volumen público puede bajar por la revisión humana de noticias sensibles.

## Preferencia vigente de publicación automática — 2026-10-23
Por instrucción expresa del propietario se retiró la aprobación humana por sensibilidad. Las notas verificadas automáticamente se publican, también sobre inmigración, salud, elecciones u otros temas sensibles. Si la revisión automática queda sin resolver, se omite la nota y se marca procesada para evitar regenerarla; no se crea borrador ni tarea de revisión humana. Los borradores históricos se conservan sin publicarlos retroactivamente. Esta regla sustituye la retención por tema sensible descrita anteriormente. La IA no garantiza exactitud absoluta.
