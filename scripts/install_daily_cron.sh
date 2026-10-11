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
OVERRIDES="*/10 * * * * $DIR/scripts/apply_ghost_overrides.sh >> $DIR/logs/overrides.log 2>&1"
mkdir -p $DIR/logs $DIR/data
chmod 755 $DIR/scripts/daily_edition.py $DIR/scripts/x_posts.py $DIR/scripts/apply_ghost_overrides.sh
(crontab -l 2>/dev/null | grep -v -e 'tuhoy/scripts/daily_edition.py' -e 'tuhoy/scripts/x_posts.py' -e 'tuhoy/scripts/apply_ghost_overrides.sh' || true
 echo "$EDITION"; echo "$X_DUE"; echo "$OVERRIDES") | crontab -
echo "cron instalado:"
crontab -l
