#!/bin/bash
set -euo pipefail
# El servidor está en UTC y cron no admite zona horaria por línea.
# Cada tarea se lanza a las dos horas UTC posibles (horario de verano e invierno)
# y solo sigue la que coincide con la hora local de America/Chicago.
PY=/usr/bin/python3
DIR=/home/raul/tuhoy
EDITION="0 11,12 * * * [ \"\$(TZ=America/Chicago date +\\%H)\" = \"06\" ] && TZ=America/Chicago $PY $DIR/scripts/daily_edition.py > /dev/null 2>> $DIR/logs/daily-errors.log"
X_DAILY="0 12,13 * * * [ \"\$(TZ=America/Chicago date +\\%H)\" = \"07\" ] && $PY $DIR/scripts/x_posts.py > /dev/null 2>> $DIR/logs/x-errors.log"
X_DUE="*/15 * * * * $PY $DIR/scripts/x_posts.py --post-due > /dev/null 2>> $DIR/logs/x-errors.log"
mkdir -p $DIR/logs $DIR/data
chmod 755 $DIR/scripts/daily_edition.py $DIR/scripts/x_posts.py
(crontab -l 2>/dev/null | grep -v -e 'tuhoy/scripts/daily_edition.py' -e 'tuhoy/scripts/x_posts.py' || true
 echo "$EDITION"; echo "$X_DAILY"; echo "$X_DUE") | crontab -
echo "cron instalado:"
crontab -l
