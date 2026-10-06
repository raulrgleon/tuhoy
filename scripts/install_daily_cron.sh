#!/bin/bash
set -euo pipefail
# El servidor está en UTC y cron no admite zona horaria por línea.
# 06:00 en America/Chicago = 11:00 UTC (CDT) o 12:00 UTC (CST): se lanza a ambas horas
# y solo sigue la que coincide con las 06 locales.
LINE='0 11,12 * * * [ "$(TZ=America/Chicago date +\%H)" = "06" ] && TZ=America/Chicago /usr/bin/python3 /home/raul/tuhoy/scripts/daily_edition.py > /dev/null 2>> /home/raul/tuhoy/logs/daily-errors.log'
mkdir -p /home/raul/tuhoy/logs /home/raul/tuhoy/data
chmod 755 /home/raul/tuhoy/scripts/daily_edition.py
(crontab -l 2>/dev/null | grep -v 'tuhoy/scripts/daily_edition.py' || true; echo "$LINE") | crontab -
echo "cron instalado:"
crontab -l
