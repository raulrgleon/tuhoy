#!/bin/bash
set -euo pipefail
# El servidor está en UTC y cron no admite zona horaria por línea.
# La edición se lanza cada hora en punto y solo sigue a las 06, 12 y 18 de America/Chicago
# (vale igual en horario de verano e invierno). Justo después, x_posts.py escribe y programa
# un post de X por cada nota nueva ("; " y no "&&": también corre si la edición no publicó nada).
PY=/usr/bin/python3
DIR=/home/raul/tuhoy
EDITION="0 * * * * case \"\$(TZ=America/Chicago date +\\%H)\" in 06|12|18) TZ=America/Chicago $PY $DIR/scripts/daily_edition.py > /dev/null 2>> $DIR/logs/daily-errors.log; $PY $DIR/scripts/x_posts.py > /dev/null 2>> $DIR/logs/x-errors.log;; esac"
X_DUE="*/15 * * * * $PY $DIR/scripts/x_posts.py --post-due > /dev/null 2>> $DIR/logs/x-errors.log"
# Facebook, Instagram y TikTok publican los mismos posts a su hora (solo si FB_MODE/IG_MODE/TT_MODE=api).
FB_DUE="*/15 * * * * $PY $DIR/scripts/facebook_posts.py > /dev/null 2>> $DIR/logs/facebook-errors.log"
IG_DUE="*/15 * * * * $PY $DIR/scripts/instagram_posts.py > /dev/null 2>> $DIR/logs/instagram-errors.log"
TT_DUE="*/15 * * * * $PY $DIR/scripts/tiktok_posts.py > /dev/null 2>> $DIR/logs/tiktok-errors.log"
OVERRIDES="*/10 * * * * $DIR/scripts/apply_ghost_overrides.sh >> $DIR/logs/overrides.log 2>&1"
# Boletín «Lo que importa hoy» a las 07 de Chicago, tras la edición de las 06 (solo si DIGEST_MODE=on).
DIGEST="0 * * * * case \"\$(TZ=America/Chicago date +\\%H)\" in 07) $PY $DIR/scripts/daily_digest.py > /dev/null 2>> $DIR/logs/digest-errors.log;; esac"
# Aviso a Bing y demás buscadores (IndexNow) de las notas nuevas, cada hora (solo si hay INDEXNOW_KEY).
INDEXNOW="5 * * * * $PY $DIR/scripts/indexnow.py > /dev/null 2>> $DIR/logs/indexnow-errors.log"
mkdir -p $DIR/logs $DIR/data
chmod 755 $DIR/scripts/daily_edition.py $DIR/scripts/x_posts.py $DIR/scripts/facebook_posts.py $DIR/scripts/instagram_posts.py $DIR/scripts/tiktok_posts.py $DIR/scripts/daily_digest.py $DIR/scripts/indexnow.py $DIR/scripts/apply_ghost_overrides.sh
(crontab -l 2>/dev/null | grep -v -e 'tuhoy/scripts/daily_edition.py' -e 'tuhoy/scripts/x_posts.py' -e 'tuhoy/scripts/facebook_posts.py' -e 'tuhoy/scripts/instagram_posts.py' -e 'tuhoy/scripts/tiktok_posts.py' -e 'tuhoy/scripts/daily_digest.py' -e 'tuhoy/scripts/indexnow.py' -e 'tuhoy/scripts/apply_ghost_overrides.sh' || true
 echo "$EDITION"; echo "$X_DUE"; echo "$FB_DUE"; echo "$IG_DUE"; echo "$TT_DUE"; echo "$DIGEST"; echo "$INDEXNOW"; echo "$OVERRIDES") | crontab -
echo "cron instalado:"
crontab -l
