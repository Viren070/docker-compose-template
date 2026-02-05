#!/bin/sh

set -e

if [ -f /app/dist/config/config.json.tmpl ]; then
  envsubst < /app/dist/config/config.json.tmpl > /app/dist/config/config.json
fi

exec /app/entrypoint.sh
