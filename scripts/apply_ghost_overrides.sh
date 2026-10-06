#!/usr/bin/env bash
# Copia las plantillas propias de ghost-overrides/ dentro del contenedor de Ghost de tuhoy.com.
# Se accede al sistema de archivos del contenedor por /proc/<pid>/root (Ghost corre con el mismo uid 1000).
# Es idempotente: solo copia si el archivo cambió. El cron lo ejecuta cada 10 min porque Coolify
# recrea el contenedor en cada despliegue y se perderían los cambios.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE_URL="${SITE_URL:-https://tuhoy.com}"

pid=""
for p in $(pgrep -f "node current/index.js" || true); do
    if tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep -qx "url=$SITE_URL"; then
        pid="$p"
        break
    fi
done
if [ -z "$pid" ]; then
    echo "[overrides] no encuentro el proceso de Ghost de $SITE_URL" >&2
    exit 1
fi

croot="/proc/$pid/root"
ghost="$croot$(readlink "$croot/var/lib/ghost/current")"
templates="$ghost/core/server/services/mail/templates"
src="$ROOT/ghost-overrides/mail/invite-user.html"

changed=0
for name in invite-user.html invite-user-by-api-key.html; do
    dest="$templates/$name"
    if ! cmp -s "$src" "$dest"; then
        cp "$src" "$dest"
        changed=1
        echo "[overrides] $(date '+%F %T') actualizado $name"
    fi
done
[ "$changed" = 0 ] && [ -t 1 ] && echo "[overrides] ya estaba al día"
exit 0
