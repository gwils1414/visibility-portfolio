# Postgres Portability — Moving Data Between Machines

## The Core Issue

Unlike DuckDB or SQLite (single portable file), Postgres data lives in a directory managed by a running server. You can't just copy a file — you need to either dump/restore or run Postgres somewhere both machines can reach.

---

## Option 1 — pg_dump / pg_restore (manual, free)

The standard approach. Export to a SQL file, transfer, import.

### Basic SQL export
```bash
# old machine — export
pg_dump hermes > hermes.sql

# transfer (scp, AirDrop, USB, whatever)
scp hermes.sql new-machine:~

# new machine — import
createdb hermes
psql hermes < hermes.sql
```

### Custom format (recommended)
Smaller file, faster restore, supports selective table restore.

```bash
# export as compressed binary
pg_dump -Fc hermes > hermes.dump

# restore
createdb hermes
pg_restore -d hermes hermes.dump
```

### Pros
- Free, built into Postgres
- Works across Postgres versions and architectures
- Full schema + data + indexes preserved
- Can be automated with cron

### Cons
- Manual step before switching machines
- Stale if you forget to dump before leaving
- No real-time sync

### When to use
Occasional machine switches where you can plan ahead.

---

## Option 2 — Scheduled dump + cloud sync (low effort, free)

Combine `pg_dump` with iCloud/Dropbox/Google Drive for auto-synced backups.

```bash
# daily cron job: dump to a synced folder
0 2 * * * pg_dump -Fc hermes > ~/Dropbox/backups/hermes.dump
```

On a new machine, restore from the synced file:
```bash
pg_restore -d hermes ~/Dropbox/backups/hermes.dump
```

### Pros
- Free
- Always have a recent backup
- Doubles as disaster recovery

### Cons
- Up to 24h of drift between machines
- Still need to restore manually on the new machine
- Not suitable for active multi-machine use

### When to use
Single-machine primary use with occasional fallback to another machine. Also good as a general backup strategy regardless of portability.

---

## Option 3 — Neon (cloud-hosted, free tier)

Postgres-as-a-service. Connect to the same database from any machine.

### Setup
```bash
# 1. sign up at neon.tech
# 2. create a project, get connection string
# 3. update Hermes config

DATABASE_URL=postgresql://user:pass@xyz.neon.tech/hermes
```

### Free tier
- 0.5GB storage
- Branching support
- Auto-pause when idle (cold-start ~1s)

### Pros
- True multi-machine access — connect from anywhere
- No manual dump/restore
- Built-in backups
- Auto-pause keeps costs $0
- Branching lets you fork the DB for experiments

### Cons
- Network latency (vs local)
- Free tier has storage limits
- Dependent on internet connection

### When to use
You actively work on multiple machines (laptop + desktop) and want zero-friction switching.

---

## Option 4 — Supabase (cloud-hosted, free tier)

Similar to Neon, broader feature set (auth, storage, realtime).

### Free tier
- 500MB storage
- 2GB bandwidth
- Auto-pause after 7 days inactive

### Pros
- Hosted Postgres + extra features (auth, storage, realtime)
- Web dashboard for browsing data
- Good Python client (`supabase-py`)

### Cons
- More features than you need for a single-user agent
- Slightly more overhead to set up than Neon

### When to use
You want the full backend-as-a-service stack, not just Postgres.

---

## Option 5 — Self-hosted on a home server / VPS

Run Postgres on a machine that stays online (Raspberry Pi, NAS, Linode/Hetzner VPS).

### Setup
```bash
# on the server
sudo apt install postgresql-16
sudo -u postgres createdb hermes

# allow remote connections
# edit postgresql.conf: listen_addresses = '*'
# edit pg_hba.conf: add host entry for your IP

# from any client
psql -h server-ip -d hermes
```

### Pros
- Full control
- No vendor lock-in
- Can run multiple databases for other projects

### Cons
- You manage backups, updates, security
- Hardware/VPS cost (~$5/mo for Hetzner)
- Network exposure requires firewall/VPN setup

### When to use
You already have a home server or want full ownership of the data layer.

---

## Option 6 — Tailscale + local Postgres (best of both worlds)

Run Postgres locally on your "primary" machine, but make it reachable from other machines via Tailscale's encrypted mesh network.

### How it works

Tailscale builds a private mesh network across your devices using WireGuard. Every device on your tailnet gets a stable IP in the `100.x.x.x` range that only your devices can reach. Postgres binds to that interface, and any other device you own can connect via `psql -h <tailscale-ip>` as if it were on the same local network.

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Mac Mini   │         │   Tailscale  │         │   Laptop     │
│  (Postgres)  │ ◄─────► │   Mesh Net   │ ◄─────► │  (Hermes CLI)│
│ 100.64.1.10  │         │  (encrypted) │         │ 100.64.1.20  │
└──────────────┘         └──────────────┘         └──────────────┘
```

Traffic is peer-to-peer (not routed through Tailscale's servers) and end-to-end encrypted via WireGuard.

### Tailscale free tier (Personal Plan)

The Personal plan is free forever, and the current limits are:
- **6 users** per tailnet
- **Unlimited devices** (the old 100-device cap was removed)
- Up to 50 tagged resources
- WireGuard-based encryption
- MagicDNS for device name resolution

For a single user with multiple machines, this is more than enough — you can connect a laptop, desktop, Mac Mini, phone, iPad, and any cloud VMs without ever hitting a limit.

### Setup steps

Since you already have Tailscale installed and connected:

**1. Find your machines' Tailscale IPs:**
```bash
tailscale ip -4
# 100.x.x.x — that's your Tailscale IPv4

tailscale status
# shows all devices on your tailnet
```

**2. Configure Postgres to listen on Tailscale interface:**

Find your `postgresql.conf`:
```bash
psql -d postgres -c "SHOW config_file;"
# returns path like /usr/local/var/postgresql@16/postgresql.conf
```

Edit that file:
```conf
# bind to localhost AND Tailscale IP only — NOT 0.0.0.0
listen_addresses = 'localhost,100.x.x.x'
```

**3. Allow connections from your tailnet in `pg_hba.conf`:**
```conf
# allow Tailscale network range
host    all    all    100.64.0.0/10    scram-sha-256
```

The `100.64.0.0/10` range covers all Tailscale-assigned IPs, so any device on your tailnet can connect (but nothing outside it).

**4. Restart Postgres:**
```bash
brew services restart postgresql@16
```

**5. Test from another machine on your tailnet:**
```bash
# from laptop
psql -h 100.x.x.x -d hermes -U garettwilson
```

Or use Tailscale's MagicDNS:
```bash
# refer to machines by name instead of IP
psql -h mac-mini -d hermes
```

### Connection string for Hermes

```python
DATABASE_URL = "postgresql://garettwilson@mac-mini.tail-xxxx.ts.net/hermes"
```

The `tail-xxxx.ts.net` MagicDNS name resolves automatically on any device on your tailnet. No DNS setup needed, no hardcoded IPs that change.

### Security considerations

This is genuinely secure for personal use:
- **Encrypted by default** — all traffic uses WireGuard, even on hostile networks
- **Private** — only devices on your tailnet can reach Postgres
- **No public exposure** — Postgres never binds to a public IP
- **ACLs available** — you can restrict which devices can reach the Postgres port

You can tighten further with ACL rules in the Tailscale admin console:
```json
{
  "acls": [
    {
      "action": "accept",
      "src":    ["user@example.com"],
      "dst":    ["mac-mini:5432"]
    }
  ]
}
```

That limits Postgres access to just your account — even if you share other resources with family.

### Pros
- **Free forever** on the Personal plan (more than enough for personal use)
- Postgres stays on hardware you own
- Encrypted by default, only your devices can reach it
- No cloud Postgres costs
- MagicDNS means stable hostnames regardless of IP changes
- Works from anywhere (laptop on coffee shop wifi connects fine)
- ACLs let you scope access precisely

### Cons
- Primary machine must be online when secondary needs access
- Wake-from-sleep on Macs can be flaky for inbound connections (consider a Mac Mini or always-on machine as the host)
- Slightly more network setup than local-only
- If Tailscale's coordination servers go down, new connections can't be established (existing ones keep working)

### When to use
You want cloud-like portability without paying for cloud Postgres, you trust your own hardware as the data layer, and you have at least one machine that stays online when you want to access Hermes from elsewhere.

### Ideal hardware setup
- **Mac Mini or iMac** as the Postgres host (always on, low power)
- **Laptop** runs Hermes CLI, connects to Mac Mini via Tailscale
- **Phone/iPad** for occasional check-ins via a future GUI
- All connected via Tailscale, all using the same Hermes database

---

## Comparison Matrix

| Option | Cost | Multi-machine | Effort | Latency |
|---|---|---|---|---|
| pg_dump manual | Free | Manual transfer | Low ongoing | None |
| pg_dump + cloud sync | Free | Daily-lagged | Low | None |
| Neon | Free tier | ✅ Instant | Low setup | Network |
| Supabase | Free tier | ✅ Instant | Medium setup | Network |
| Self-hosted VPS | ~$5/mo | ✅ Instant | High setup | Network |
| Tailscale + local | Free | ✅ When host on | Medium setup | LAN-fast |

---

## Recommendation for Hermes

**Start with Option 1 (pg_dump)** — you're already running Postgres locally, and manual dumps before machine switches are fine for now.

**Add Option 2 (scheduled dump to Dropbox/iCloud)** once you have meaningful data — your feedback history, eval results, and reflection versions deserve backup regardless of portability needs.

**Migrate to Option 3 (Neon)** if you actually find yourself wanting to chat with Hermes from multiple machines. Neon's free tier handles a personal agent's data trivially, and the connection string change is the only code touched.

**Consider Option 6 (Tailscale + local)** if you have a Mac that stays on (Mac Mini, iMac) and want the Mac to host Postgres while your laptop connects in. Good middle ground if you want full control without the cloud.

Avoid Options 4 and 5 unless you have specific needs they solve — they're overkill for a personal agent.