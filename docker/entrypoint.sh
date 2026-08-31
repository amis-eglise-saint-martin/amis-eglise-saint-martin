#!/bin/sh
# Entrypoint script: run cron in background, then start nginx

# Run visitor counter once at startup
python3 /scripts/count_visitors.py

# Start supercronic in background (cron for containers)
supercronic /etc/crontab &

# Start nginx in foreground
exec nginx -g 'daemon off;'
