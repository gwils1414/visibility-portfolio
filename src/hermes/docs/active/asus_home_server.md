# ASUS ROG Zephyrus as Home AI Server — Setup Plan

## Hardware

- **ASUS ROG Zephyrus**
- AMD Ryzen 9
- 16GB DDR5
- NVIDIA RTX 3060 (GPU passthrough capable)
- 512GB PCIe 4.0 SSD
- Windows 11

## Goal

Turn the laptop into an always-on home server hosting:
1. **Postgres** — shared database for Hermes + future projects
2. **Ollama** — local LLM inference with GPU acceleration
3. **Docker + Prefect** — scheduled jobs (reflection, fine-tuning, ETL)
4. **Tailscale** — secure remote access from any device

All accessible from your Mac (and any other Tailscale device) as if running locally.

```
┌──────────────────────────────┐         ┌──────────────────────────────┐
│  Mac (daily use)             │         │  ASUS (always-on server)     │
│                              │         │                              │
│  Hermes CLI                  │         │  Postgres :5432              │
│  ↓                           │ ←─────→ │  Ollama   :11434             │
│  Tailscale ─────────────────────────→  │  Prefect  :4200              │
│                              │         │  Docker daemon                │
└──────────────────────────────┘         └──────────────────────────────┘
                                           Tailscale: 100.x.x.x
```

---

## Why This Setup Makes Sense

- **You already own it** — zero hardware cost
- **RTX 3060 is real GPU compute** — way better than Mac inference
- **More capable than dedicated alternatives** — beats a Mac Mini or Raspberry Pi for AI work
- **Tailscale handles networking** — no port forwarding, no exposed IPs
- **Stay on Windows** — gaming-ready if you want, no OS migration needed

---

## Phase 1 — Foundation Setup

### Step 1 — Enable WSL2

WSL2 is your Linux environment for Docker and most server work. Open PowerShell as Administrator:

```powershell
wsl --install
wsl --set-default-version 2

# install Ubuntu (latest LTS)
wsl --install -d Ubuntu-24.04
```

Reboot when prompted, then set up Ubuntu username/password.

### Step 2 — Configure WSL2 memory limits

Create `C:\Users\YOU\.wslconfig`:

```ini
[wsl2]
memory=10GB              # cap WSL2 at 10GB, leaves 6GB for Windows
processors=8
swap=4GB
networkingMode=mirrored  # share host network (Tailscale, VPN, etc.)
```

Restart WSL: `wsl --shutdown` then open Ubuntu again.

### Step 3 — Power settings for always-on operation

Windows settings → System → Power:
- **Plugged in** — never sleep, never turn off display
- **Lid close action** → Do nothing (when plugged in)
- Disable USB selective suspend
- Disable hibernation: `powercfg /hibernate off` in admin PowerShell

The laptop will run 24/7 with the lid closed when plugged in.

### Step 4 — Wired ethernet (recommended)

Wifi works but wired is more reliable for a server. If your ASUS has ethernet, use it. Otherwise, consider a USB-C ethernet adapter.

---

## Phase 2 — Tailscale

### Step 1 — Install on ASUS
Download from `tailscale.com/download/windows`, sign in with the same account as your other devices.

### Step 2 — Find the Tailscale IP
```powershell
tailscale ip -4
# 100.x.x.x  ← your ASUS's Tailscale IP
```

### Step 3 — Set up MagicDNS (optional but cleaner)
Tailscale admin console → DNS → Enable MagicDNS. Your ASUS becomes reachable as `asus.tail-xxxx.ts.net` instead of by IP.

### Step 4 — Test from your Mac
```bash
ping 100.x.x.x        # ASUS Tailscale IP
ping asus.tail-xxxx.ts.net  # via MagicDNS
```

If those work, your encrypted mesh is established.

---

## Phase 3 — Postgres

### Step 1 — Install Postgres on Windows directly
Download installer from `postgresql.org/download/windows`. Standard install, remember the password.

Or via Chocolatey/Scoop:
```powershell
winget install PostgreSQL.PostgreSQL.16
```

### Step 2 — Configure to listen on Tailscale IP
Edit `C:\Program Files\PostgreSQL\16\data\postgresql.conf`:

```conf
# bind to localhost AND Tailscale IP — NOT 0.0.0.0
listen_addresses = 'localhost,100.x.x.x'
```

### Step 3 — Allow tailnet connections in `pg_hba.conf`
Same data directory:

```conf
# Tailscale network range
host    all    all    100.64.0.0/10    scram-sha-256
```

### Step 4 — Open Windows Firewall for port 5432 (Tailscale only)
```powershell
New-NetFirewallRule -DisplayName "Postgres Tailscale" `
    -Direction Inbound -Protocol TCP -LocalPort 5432 `
    -RemoteAddress 100.64.0.0/10 -Action Allow
```

This is critical — restricts Postgres to ONLY accept connections from your tailnet, never the public internet.

### Step 5 — Restart Postgres service
```powershell
Restart-Service postgresql-x64-16
```

### Step 6 — Create the Hermes database
```powershell
psql -U postgres -c "CREATE DATABASE hermes;"
```

### Step 7 — Test from Mac
```bash
psql -h asus.tail-xxxx.ts.net -d hermes -U postgres
```

---

## Phase 4 — Ollama with GPU

### Step 1 — Install Ollama for Windows
Native Windows install is best for GPU access. Download from `ollama.com/download/windows`.

Why native and not WSL2: ROCm/CUDA passthrough in WSL2 works but is more fragile. Native Windows Ollama uses your RTX 3060 directly with no extra setup.

### Step 2 — Verify GPU detection
```powershell
ollama serve
# in another terminal:
ollama run qwen2.5:7b
# while it runs, in another terminal:
nvidia-smi
# you should see ollama_llama_server in the process list using VRAM
```

### Step 3 — Bind to Tailscale IP
By default Ollama only listens on `127.0.0.1`. To expose it on Tailscale:

Set system environment variable via System Properties → Environment Variables:
```
OLLAMA_HOST=0.0.0.0:11434
```

Restart Ollama. Now it listens on all interfaces — including your Tailscale IP.

### Step 4 — Firewall rule (Tailscale only)
```powershell
New-NetFirewallRule -DisplayName "Ollama Tailscale" `
    -Direction Inbound -Protocol TCP -LocalPort 11434 `
    -RemoteAddress 100.64.0.0/10 -Action Allow
```

### Step 5 — Pull models suited for the 3060
The RTX 3060 has 6GB or 12GB VRAM depending on variant. Check yours:
```powershell
nvidia-smi
```

**For 6GB VRAM:**
```powershell
ollama pull qwen2.5:7b           # ~4GB, good fit
ollama pull llama3.1:8b-q4_K_M   # ~5GB, slightly tighter
```

**For 12GB VRAM:**
```powershell
ollama pull qwen2.5:14b          # ~9GB, comfortable
ollama pull gemma2:9b            # ~6GB, fast and capable
```

### Step 6 — Test from Mac
```bash
curl http://asus.tail-xxxx.ts.net:11434/api/tags
# lists models on the ASUS
```

Or wire it into Hermes:
```python
ollama_model = OpenAIChatModel(
    model_name='qwen2.5:7b',
    provider=OllamaProvider(
        base_url='http://asus.tail-xxxx.ts.net:11434/v1',
        api_key='ollama'  # required but unused
    )
)
```

Now Hermes runs on your Mac but inference happens on the ASUS GPU.

---

## Phase 5 — Docker + Prefect

### Step 1 — Install Docker Desktop
Download from `docker.com/products/docker-desktop`. Configure to use WSL2 backend during install.

### Step 2 — Verify it works
```powershell
docker run hello-world
```

### Step 3 — Set up Prefect server
Create `docker-compose.yml`:

```yaml
services:
  prefect-server:
    image: prefecthq/prefect:3-latest
    command: prefect server start --host 0.0.0.0
    ports:
      - "4200:4200"
    environment:
      PREFECT_API_DATABASE_CONNECTION_URL: postgresql+asyncpg://postgres:PASSWORD@host.docker.internal:5432/prefect
    restart: unless-stopped

  prefect-worker:
    image: prefecthq/prefect:3-latest
    command: prefect worker start --pool default
    environment:
      PREFECT_API_URL: http://prefect-server:4200/api
    depends_on:
      - prefect-server
    restart: unless-stopped
```

The Prefect server uses Postgres on your Windows host (`host.docker.internal` resolves to the host machine from within Docker).

### Step 4 — Create the Prefect database
```powershell
psql -U postgres -c "CREATE DATABASE prefect;"
```

### Step 5 — Start the stack
```powershell
docker compose up -d
```

### Step 6 — Firewall rule for Prefect API
```powershell
New-NetFirewallRule -DisplayName "Prefect Tailscale" `
    -Direction Inbound -Protocol TCP -LocalPort 4200 `
    -RemoteAddress 100.64.0.0/10 -Action Allow
```

### Step 7 — Access Prefect UI from Mac
Browser → `http://asus.tail-xxxx.ts.net:4200`

You'll see the Prefect dashboard. Flows can be scheduled here and will run inside Docker on the ASUS.

---

## Connection Strings Cheat Sheet

From your Mac (or any Tailscale device):

```python
# Postgres
DATABASE_URL = "postgresql://postgres:PASSWORD@asus.tail-xxxx.ts.net:5432/hermes"

# Ollama
OLLAMA_HOST = "http://asus.tail-xxxx.ts.net:11434"

# Prefect API
PREFECT_API_URL = "http://asus.tail-xxxx.ts.net:4200/api"
```

Store these in your Hermes `Settings` deps. Everything else stays the same.

---

## Operational Notes

### Auto-restart on boot
- **Postgres** — installed as a Windows service, auto-starts
- **Ollama** — set to start with Windows in Settings → Apps → Startup
- **Docker** — start with Windows in Docker Desktop settings → "Start when you log in"
- **Tailscale** — starts with Windows by default

### Monitor health
PowerShell helpers:
```powershell
# all critical services
Get-Service postgresql-x64-16, "Docker Desktop Service"

# Ollama check
curl http://localhost:11434/api/tags

# disk space
Get-PSDrive C
```

### Thermals
Gaming laptops aren't designed for 24/7 high load. Recommendations:
- Keep lid open OR use a stand that lifts it
- Use the included cooling pad if you have one
- Set NVIDIA control panel power mode to "Optimal" not "Maximum"
- Avoid leaving large models loaded 24/7 — set `OLLAMA_KEEP_ALIVE=5m` so models unload after inactivity

### Backups
Schedule a daily Postgres dump to a synced folder:

```powershell
# scheduled task: daily 2am
pg_dump -U postgres hermes | Out-File "C:\Users\YOU\Dropbox\backups\hermes.sql"
```

---

## Build Order

```
Phase 1 — Foundation
  ├── WSL2 + Ubuntu
  ├── .wslconfig with memory limits
  └── Power settings for 24/7 operation

Phase 2 — Network
  ├── Tailscale install + verify
  └── MagicDNS setup

Phase 3 — Postgres
  ├── Install Postgres
  ├── Bind to Tailscale interface
  ├── Configure pg_hba.conf
  ├── Firewall rule (Tailscale only)
  └── Test connection from Mac

Phase 4 — Ollama
  ├── Native Windows install
  ├── Verify GPU detection
  ├── Set OLLAMA_HOST environment var
  ├── Firewall rule
  ├── Pull appropriate models for your VRAM
  └── Test from Mac

Phase 5 — Docker + Prefect
  ├── Docker Desktop with WSL2 backend
  ├── docker-compose.yml for Prefect
  ├── Create Prefect Postgres database
  ├── Firewall rule for port 4200
  └── Verify UI from Mac
```

---

## Future — Linux Migration (Supplemental)

If you ever decide Windows is too heavy for an always-on server, the migration to Linux is straightforward:

### Recommended distros
- **Ubuntu Server 24.04 LTS** — best documentation, easiest setup
- **Pop!_OS** — Ubuntu-based, NVIDIA drivers preinstalled
- **Fedora Server** — modern, NVIDIA support is solid

### What you gain
- ~2GB less RAM used by the OS (more for Ollama)
- Faster boot, lighter footprint
- Native Docker (no Docker Desktop overhead)
- Better for headless operation
- No Windows updates interrupting service

### What's roughly the same
- Tailscale works identically
- Postgres setup is similar
- Ollama natively supports Linux + NVIDIA
- Docker is first-class

### What you lose
- Gaming on this machine (still can dual-boot if needed)
- Some Windows-specific software
- Familiar GUI

### Migration approach
1. Back up all data (pg_dump, model files, configs)
2. Dual-boot Linux alongside Windows initially
3. Verify everything works on Linux
4. Once stable, repurpose the Windows partition or wipe it

Most online guides for these tools assume Linux, so you'd actually find more reference material once migrated. But staying on Windows is totally viable — everything in this plan works natively.

---

## What This Enables

Once complete, your Mac becomes a thin client:
- Hermes CLI runs locally on Mac for instant interaction
- All heavy work (LLM inference, DB, scheduled jobs) happens on ASUS
- Works from anywhere via Tailscale (coffee shop, office, traveling)
- One Postgres serves multiple projects (Hermes, Accupac side projects, etc.)
- One Ollama serves multiple agents
- Prefect schedules background work without affecting your Mac

You've effectively built a personal AI infrastructure stack for $0 in ongoing costs, using hardware you already own.