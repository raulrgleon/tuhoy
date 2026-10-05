#!/bin/bash
set -euo pipefail
# 06:00 hora de Nueva York = 10:00 UTC (EDT) o 11:00 UTC (EST).
# Usamos TZ en la propia línea para que el reloj del Dell (UTC) no desfase la edición.
LINE='0 6 * * * TZ=America/New_York /usr/bin/python3 /home/raul/tuhoy/scripts/daily_edition.py > /dev/null 2>> /home/raul/tuhoy/logs/daily-errors.log'
mkdir -p /home/raul/tuhoy/logs /home/raul/tuhoy/data
chmod 755 /home/raul/tuhoy/scripts/daily_edition.py
(crontab -l 2>/dev/null | grep -v 'tuhoy/scripts/daily_edition.py' || true; echo "$LINE") | crontab -
echo "cron instalado:"
crontab -l
