# Threads y YouTube — integración de TuHoy, 23-oct-2026

Proveedor: Buffer existente, API GraphQL oficial. La cuenta gratuita muestra tres plazas: TikTok más dos canales nuevos. No se contrató un plan. Threads requiere inicio de sesión del propietario; no está activo todavía. YouTube fue conectado con autorización explícita de los permisos OAuth solicitados y se comprobó que el ID UCPvMwculzE04EAjeSPpilVw corresponde a @TuHoyNoticias.

## Trabajador

scripts/buffer_extra_channels.py reutiliza la cola de noticias publicada y no la modifica. Threads recibe titular/enlace; YouTube recibe los vídeos verticales existentes mediante tiktok_video.py, título, enlace, categoría News & Politics, visibilidad pública, sin notificaciones a suscriptores y con indicación de contenido generado con IA por la narración sintética. No cambia el comportamiento de TikTok.

Configuración privada data/buffer-extra-channels.json: por plataforma, enabled, id de canal Buffer verificado, enabled_at ISO con zona. Solo se seleccionan noticias programadas después de activación y vencidas hace menos de dos horas. No hay recuperación automática de históricos. Cada destino tiene bloqueo, archivo de estado atómico0600 y máximo10 intentos por24h. Sin pendientes ni elegibles no consume API. Una respuesta incierta detiene nuevos envíos; no borrar estado para reintentar. Aceptación de Buffer no equivale a publicación final: se exige estado sent y externalLink para confirmar.

## Instalación activa

YouTube: canal Buffer 6adb009b778b240e2f998449, timer tuhoy-buffer-youtube.timer cada15min con45s aleatorios. Primera ejecución success/0, sin noticias nuevas elegibles, ningún vídeo publicado durante la prueba.
Threads: código y unidades preparados; configuración deshabilitada, timer sin activar, pendiente completar OAuth y verificar ID/handle antes de fijarlo en configuración. En la conexión, revisar permisos y confirmar con el propietario antes de conceder nuevos accesos.
Ambos servicios leen la misma credencial cifrada de Buffer ya usada por TikTok mediante LoadCredentialEncrypted. No se copia la clave a scripts, repositorio o entorno del navegador.

## Pruebas y próximos pasos

Seis pruebas específicas: destino/cuenta, ausencia de históricos/duplicados, payloads, rechazo de vídeos externos, inactividad sin API, estado privado y detención tras pérdida de respuesta. No prueba de publicación real en YouTube/Threads aún. Hacer verificación GET del primer envío normal con ID/enlace real. No afirmar que las seis redes están activas mientras Threads no esté conectado. Credencial Buffer con vencimiento previamente documentado16-nov-2026: verificar/renovar antes de esa fecha, sin registrar valor.

Reversión: deshabilitar únicamente el timer de destino y enabled=false. Mantener estados y colas; no desconectar TikTok ni borrar publicaciones para revertir código.
