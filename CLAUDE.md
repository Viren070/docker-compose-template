# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Docker Compose template for self-hosting ~100 services on a single VPS, fronted by **Traefik** (reverse proxy + Let's Encrypt) and protected by **Authelia** (forward-auth, ACLs, 2FA/passkeys). End users clone this onto a VPS at `/opt/docker`, fill in `.env`, and run `docker compose up -d`. There is no build step — the repo *is* the artifact.

## Architecture

**Root `compose.yaml` is just an `include:` list** of `apps/<name>/compose.yaml` files. Each app is a self-contained directory under `apps/`. Adding/removing a service is done by editing the `include:` list and/or toggling profiles, not by editing one large file.

**Profiles gate every service.** Every service block declares `profiles: [<service-name>, all]`, and the core gateway services (traefik, authelia + its redis/postgres) additionally declare the `required` profile. Nothing starts unless its profile is listed in `COMPOSE_PROFILES` (set in root `.env`) or passed via `--profile`. The `all` profile turns everything on; `required` is the minimum viable bootstrap.

**Config flows through `.env`, not YAML.**
- Root `.env` holds shared config: `DOMAIN`, `DOCKER_DATA_DIR` (default `/opt/docker/data`), `DOCKER_APP_DIR`, `PUID`/`PGID`, `TZ`, `COMPOSE_PROFILES`, secrets, and one `<APP>_HOSTNAME=<sub>.${DOMAIN}` line per service.
- Per-app secrets/options live in `apps/<name>/.env` and are pulled in via `env_file: - .env` inside that app's compose file (e.g. aiostreams, gluetun). These are *not* visible to other services — only to the containers that explicitly reference them.
- Hostnames use `${X_HOSTNAME?}` (the `?` makes the variable required); when adding a service follow the same pattern so misconfiguration fails fast.

**Traefik wiring is by label, not by config file.** Each web-exposed service declares:
```
traefik.enable=true
traefik.http.routers.<svc>.rule=Host(`${<SVC>_HOSTNAME?}`)
traefik.http.routers.<svc>.entrypoints=websecure
traefik.http.routers.<svc>.tls.certresolver=letsencrypt
traefik.http.routers.<svc>.middlewares=authelia@docker   # if it should require login
traefik.http.services.<svc>.loadbalancer.server.port=<container-port>
```
Traefik reads these via the Docker provider. The `letsencrypt` resolver and `authelia@docker` middleware are defined once in `apps/traefik/compose.yaml` and `apps/authelia/compose.yaml` respectively.

**Authelia is templated from env vars.** `apps/authelia/config/configuration.yml` uses Go templating (`X_AUTHELIA_CONFIG_FILTERS: template`) and reads `TEMPLATE_*` env vars set in `apps/authelia/compose.yaml`. The `access_control` block at the bottom of `configuration.yml` references those template vars to decide which hostnames need login, two-factor, or bypass policies. **Two consequences**:
1. Adding a host that needs a non-default ACL rule (e.g. a Stremio addon that needs partial bypass, or a path-specific bypass) requires editing **both** `apps/authelia/compose.yaml` (add a `TEMPLATE_<X>_HOSTNAME: ${X_HOSTNAME?}` env line) **and** `configuration.yml` (add the rule referencing that env var).
2. Stremio addon hostnames are intentionally listed together in `TEMPLATE_STREMIO_ADDON_HOSTNAMES` — those domains get page-specific protection only because the addon protocol won't tolerate full auth.

**Network.** All services share one Docker network, named `${DOCKER_NETWORK:-aio_default}` (defined at the bottom of the root `compose.yaml`). Service-to-service references use container names (e.g. `http://authelia:9091`).

**Volume conventions.** Two patterns coexist:
- App data → `${DOCKER_DATA_DIR}/<app>:/...` (absolute, from root `.env`).
- App-shipped config files → relative paths like `./config:/config` or `./config.toml:/...`, which resolve relative to *that app's compose file* (e.g. `apps/authelia/config/`, `apps/seanime/config.toml`). These files are committed to the repo and are the reason the `apps/<name>/` directories sometimes contain more than just `compose.yaml`.

## Common commands

```bash
# First boot — bring up only Traefik + Authelia
docker compose --profile required up -d

# Use the profiles set in .env (COMPOSE_PROFILES=...)
docker compose up -d

# Operate on one service stack (overrides COMPOSE_PROFILES)
docker compose --profile <name> up -d
docker compose --profile <name> restart
docker compose --profile <name> logs -f
docker compose --profile <name> pull

# Validate the merged config without starting anything
docker compose config
docker compose --profile all config        # see everything resolved
```

Note: `--profile` *must* come before the subcommand. `COMPOSE_PROFILES` in `.env` is read for bare `docker compose up -d`, but `--profile` flags override it for that single invocation.

## Adding a new service

1. Create `apps/<name>/compose.yaml` with a service block that sets `container_name`, `restart: unless-stopped`, the right `image`, `profiles: [<name>, all]`, Traefik labels (including `authelia@docker` middleware unless there's a protocol reason not to), and volumes under `${DOCKER_DATA_DIR}/<name>`.
2. Add `- apps/<name>/compose.yaml` to the `include:` list in root `compose.yaml` (keep alphabetical).
3. Add `<NAME>_HOSTNAME=<sub>.${DOMAIN}` to root `.env` near the other hostname entries.
4. If the service needs its own secrets/config, create `apps/<name>/.env` and reference it with `env_file: - .env` in the compose file.
5. If the service needs a non-default Authelia rule (Stremio addon, public, bypass-by-path, etc.), wire it through both `apps/authelia/compose.yaml` and `apps/authelia/config/configuration.yml` as described above.

## Gotchas

- Relative bind-mount paths (`./config:/config`) resolve relative to the *including* compose file's directory — i.e. `apps/<name>/`, not the repo root. Absolute paths via `${DOCKER_DATA_DIR}` avoid this ambiguity and are preferred for data volumes.
- `apps/cloudflare-ddns/...` only works for domains using Cloudflare nameservers; DuckDNS/Afraid users must create DNS records manually and should *not* enable that profile.
- The `${VAR?}` syntax aborts compose with a clear error if `VAR` is unset — preserve it when copying patterns; silently defaulting hostnames or secrets is worse than failing loudly.
- Crowdsec wiring in `apps/traefik/compose.yaml` is commented out; enabling it requires uncommenting both the `--experimental.plugins.bouncer.*` lines and the `crowdsec` `depends_on` block.
- Three alternative debrid stacks are mutually exclusive (decypharr / zurg / debridav) — see the commented block at the bottom of root `compose.yaml`. Don't enable more than one without reading those notes.
