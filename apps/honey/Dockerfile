FROM ghcr.io/dani3l0/honey:v2.4.1

ARG PUID
ARG PGID

RUN apk add --no-cache gettext

COPY config.json /app/dist/config/config.json.tmpl

RUN chown "${PUID}:${PGID}" /app/dist/config/config.json

COPY setenv.sh /app/setenv.sh
RUN chmod +x /app/setenv.sh

ENTRYPOINT ["/app/setenv.sh"]
