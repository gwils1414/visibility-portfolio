# Self-Hosting Infisical in a Homelab

A practical reference for running Infisical on your own hardware and wiring it into a Python CLI (Hermes). Targets a single always-on Linux box with Docker.

## Why self-host (in a homelab specifically)

The usual argument against self-hosting a secrets manager is operational tax — TLS, backups, patching, an extra stateful service to keep alive. **In a homelab that tax is already paid.** You have an always-on box, you already run Docker + a reverse proxy + backups for other services, so Infisical is one more compose stack on infrastructure you maintain anyway.

Concrete benefits:

- **Data stays on your hardware.** Secrets never leave your network — the actual reason to self-host vs. the cloud free tier.
- **No external dependency / no vendor account** in your secret-fetch path.
- **One source of truth across machines.** Laptop, desktop, and any homelab service pull from the same instance instead of scattered `.env` files.
- **Learning surface.** Machine identities, service tokens, and RBAC are exposed here in a way the lightweight alternatives (`keyring`, sops) never make you touch — useful if you want production-grade secret handling patterns in your own projects.
- **Runtime injection, no plaintext on disk.** `infisical run -- <cmd>` fetches and injects just-in-time; nothing lands in a `.env`.

When it does **not** make sense: if you don't already run an always-on box, self-hosting turns a handful of API keys into a single point of failure you now own. Use the cloud free tier or `keyring` instead.

## Requirements

- Linux server (Ubuntu 20.04+) or any Docker host, internal network only
- Docker Engine + Docker Compose v2
- ~2 CPU cores, 4 GB RAM (covers all three containers)
- Three containers will run: **Infisical backend + PostgreSQL + Redis**

## Setup

### 1. Pull the compose file and env template

```bash
mkdir infisical && cd infisical
curl -o docker-compose.prod.yml \
  https://raw.githubusercontent.com/Infisical/infisical/main/docker-compose.prod.yml
curl -o .env \
  https://raw.githubusercontent.com/Infisical/infisical/main/.env.example
chmod 600 .env
```

### 2. Set the required secrets in `.env`

Two non-negotiable values:

```bash
# 16-byte hex string — used for platform encryption/decryption
ENCRYPTION_KEY=$(openssl rand -hex 16)

# JWT signing secret for auth
AUTH_SECRET=$(openssl rand -base64 32)
```

Write those into `.env`. **Back up `ENCRYPTION_KEY` somewhere off-box immediately** (see Backups — the DB is useless without it).

### 3. Bring it up

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps   # expect 3 containers
curl http://localhost:8080/api/status          # expect message: OK
```

`OK` means the backend is connected to Postgres and Redis and is ready.

### 4. Create the admin account

Open the web UI (`http://localhost:8080` or your domain). The **first account created becomes the instance administrator** — that's you.

- Download the **Emergency Kit PDF** shown at setup. It's the only recovery path if you're locked out. Store it off-box.
- In server settings, **disable user signups** right after, so the instance can't accumulate accounts you didn't create.

## Homelab hardening

### Keep it internal

Do not port-forward Infisical to the public internet. If you need remote access, put it behind a VPN (Tailscale/WireGuard), never a raw port-forward. A secrets manager is the last thing you want reachable from the open web.

### TLS via reverse proxy

Out of the box you get a self-signed cert warning. Front it with Caddy/Nginx/Traefik. If running Nginx on the host, change the backend mapping in `docker-compose.prod.yml` from `80:8080` to `127.0.0.1:8080:8080` so Nginx can own 80/443.

Minimal Nginx location block:

```nginx
location / {
    proxy_pass http://infisical-backend:8080;
}
```

### Treat it as core infra

Infisical is now in the boot path for anything that fetches from it.

- Ensure restart policies bring it up on reboot (`restart: unless-stopped` is in the prod compose by default — verify).
- It should be healthy *before* services that depend on it start.

## Backups

Back up **two things, stored separately**. The DB without the key is unrecoverable ciphertext.

```bash
# 1. Postgres dump
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U infisical infisical > infisical_$(date +%Y%m%d).sql

# 2. The ENCRYPTION_KEY from .env  → store off-box (password manager / vault)
# 3. The Emergency Kit PDF         → store off-box
```

Cron the dump:

```bash
# crontab -e
0 2 * * * cd /path/to/infisical && docker compose -f docker-compose.prod.yml \
  exec -T db pg_dump -U infisical infisical > /backups/infisical_$(date +\%Y\%m\%d).sql
```

> If your existing homelab backup routine only grabs volumes/databases, the key in `.env` is easy to forget — that's exactly the failure that leaves you with a backup you can't decrypt.

## Wiring into Hermes

Day-to-day is identical to the cloud version, just pointed at your box.

```bash
# Authenticate against your self-hosted instance
infisical login --domain=https://secrets.yourdomain.lan

# Optional: avoid the --domain flag on every command
export INFISICAL_API_URL=https://secrets.yourdomain.lan

# Initialize per-project — drops a .infisical.json with project/env settings
cd ~/code/hermes
infisical init

# Run with secrets injected at runtime — no .env on disk
infisical run --env=dev -- hermes chat
```

Set/list secrets from the CLI instead of the dashboard if you prefer:

```bash
infisical secrets set ANTHROPIC_API_KEY="sk-..." --env=dev
infisical secrets --env=dev
```

For non-interactive contexts (cron jobs, CI on your runners), use a **machine identity / service token** rather than your interactive login.

## Caveat worth knowing

Env-var injection isn't invisibility — any process running as your user can read another of your processes' environment (`/proc/<pid>/environ` on Linux). Fine for a personal/homelab threat model; just don't treat "off disk" as "fully isolated."

---

**TL;DR:** three containers, ~4 GB RAM, an afternoon to stand up. Back up the DB *and* the encryption key separately, keep it off the public internet, disable signups. In a homelab where the box and the ops hygiene already exist, the marginal cost is low and you get data-on-your-own-hardware plus a real RBAC/machine-identity surface to learn on.