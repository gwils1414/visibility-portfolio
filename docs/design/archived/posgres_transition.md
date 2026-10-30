# Why Postgres for Hermes — DB Decision

## Summary

For a multi-agent system with concurrent reads/writes, short-term memory, scheduled jobs, and ingestion pipelines, **Postgres is the right choice** over DuckDB or SQLite.

| | DuckDB | SQLite | Postgres |
|---|---|---|---|
| Workload type | OLAP (analytics) | OLTP (transactional) | OLTP + OLAP |
| Concurrent reads | ✅ | ✅ | ✅ |
| Concurrent writes | ❌ | ❌ Single writer | ✅ True parallel |
| Lock granularity | File-level | Database-level | Row-level |
| Transactional ACID | Limited | ✅ | ✅ Full |
| Docker-friendly | Awkward | File-mount only | ✅ Native |
| dlt support | ✅ | ✅ | ✅ |
| Cost (local) | $0 | $0 | $0 |
| Idle resource use | None (in-process) | None (in-process) | ~80MB RAM |

---

## Workload Mismatch — DuckDB

DuckDB is OLAP — designed for analytical queries over large datasets (joins, aggregations, scans). It's the right choice for the Accupac analytics work — querying `fct_sku_profitability` with complex aggregations.

It's the wrong choice for agent memory because:

- **Frequent small writes** — agent memory means logging every message, every tool call, every feedback. DuckDB's columnar storage is optimized for bulk inserts and large scans, not high-frequency small writes.
- **No concurrent writes** — only one writer at a time. Two agents trying to log simultaneously will block.
- **Transactional semantics are limited** — not designed for the "many small ACID operations" pattern.

You can make DuckDB work for this, but you're using a hammer as a screwdriver.

---

## The SQLite Limitation

SQLite is fully transactional and a great fit for single-process apps. The problem is the single-writer model:

```
┌────────────────────────────────────────┐
│  SQLite — only ONE writer at a time   │
│                                        │
│  Agent A writing  →  ✓                │
│  Agent B writing  →  blocked, waits   │
│  Agent C writing  →  blocked, waits   │
└────────────────────────────────────────┘
```

For a system where:
- Sub-agents run in parallel and write results
- A Prefect job logs to the DB while you're chatting
- Multiple tools fire concurrently and log outputs

→ SQLite serializes them. Each write waits for the previous to finish. Works, but slow and fragile under load.

Postgres handles this natively:

```
┌────────────────────────────────────────┐
│  Postgres — concurrent writers OK     │
│                                        │
│  Agent A writing row 1  →  ✓          │
│  Agent B writing row 2  →  ✓          │
│  Agent C writing row 3  →  ✓          │
└────────────────────────────────────────┘
```

Row-level locking means writes to different rows don't block each other.

---

## Why This Matters for Hermes Specifically

### Short-term memory
Every message, tool call, and feedback entry is a small write. With sub-agents and parallel tools, these writes happen concurrently. Postgres handles this naturally; SQLite serializes; DuckDB struggles.

### Sub-agent ensembles
The interesting agent pattern (running 5 sub-agents in parallel to get diverse responses) means 5 concurrent writers. Postgres handles parallel writes to the same table without contention.

### Scheduled jobs (Prefect reflection, monthly fine-tune)
Background jobs need to read history and write results while the foreground CLI is also active. Postgres makes this seamless — no lock contention between job processes and interactive sessions.

### Evals + workflow execution
Eval runs and workflow steps both write to the DB. If you run them in parallel (multiple evals at once, or a workflow with parallel steps), concurrent writes are required.

---

## Transactional Guarantees Matter

For agent memory you need ACID:

- **Atomicity** — if logging fails mid-write, the whole record is rolled back, no half-state
- **Consistency** — foreign keys and constraints enforced
- **Isolation** — concurrent operations see consistent snapshots
- **Durability** — once committed, writes survive a crash

DuckDB has limited transactional support (oriented around bulk operations). SQLite has full ACID but bottlenecks on the single writer. Postgres gives you full ACID + concurrent writers.

---

## Docker Integration

Postgres runs natively in Docker, and containers can talk to either:

**Option A — Postgres on host, containers connect to it:**
```yaml
services:
  prefect:
    image: prefecthq/prefect:latest
    environment:
      DATABASE_URL: postgresql://garett@host.docker.internal:5432/hermes
```

The magic hostname `host.docker.internal` lets containers reach the Mac's Postgres.

**Option B — Postgres in its own container:**
```yaml
services:
  postgres:
    image: postgres:16
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  prefect:
    image: prefecthq/prefect:latest
    environment:
      DATABASE_URL: postgresql://hermes:hermes@postgres:5432/hermes
```

Both patterns are clean. DuckDB in Docker is awkward (file-based, conflicts with mounted volumes). SQLite in Docker only works as a file mount, no networked access.

For the Hermes setup:
```
Mac host (CLI):        connects locally       → postgresql://localhost/hermes
Docker (Prefect):      connects via Docker DNS → postgresql://host.docker.internal/hermes
```

One Postgres, multiple clients, no data duplication.

---

## Resource Cost

Postgres idle is very light:
- ~50-100MB RAM at rest
- ~0% CPU when no active queries
- Negligible on a 48GB Mac

Starting it as a background service:
```bash
brew install postgresql@16
brew services start postgresql@16
createdb hermes
```

Then it's just there, waiting. No noticeable system impact.

---

## dlt Compatibility

dlt fully supports Postgres as a destination:

```python
import dlt

pipeline = dlt.pipeline(
    pipeline_name="hermes_memory",
    destination="postgres",
    dataset_name="agent_data"
)
```

Works identically to dlt with DuckDB — same `@dlt.resource` decorators, same column hints, same load behavior. The `data_type: json` hint we discussed for embeddings works the same way.

For columns like embeddings, Postgres can also use `pgvector` extension for native vector search — something neither DuckDB nor SQLite supports cleanly. Future-proofs you for semantic memory retrieval.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memories (
    id          SERIAL PRIMARY KEY,
    content     TEXT,
    embedding   vector(1024),
    created_at  TIMESTAMP DEFAULT now()
);

-- semantic search via cosine distance
SELECT * FROM memories ORDER BY embedding <=> '[0.1, 0.2, ...]' LIMIT 5;
```

This becomes important when your reflection loop and long-term memory need to retrieve semantically similar past events.

---

## When DuckDB Still Makes Sense

DuckDB is genuinely better for analytics — keep using it for:
- Accupac profitability queries
- Ad-hoc data exploration
- dbt transformations on warehouse-style data
- Notebook analytics

The pattern is: **DuckDB for analytics, Postgres for state.** They serve different purposes and can coexist in the same project.

---

## When SQLite Still Makes Sense

SQLite is the right call for:
- Pure single-process apps
- Local config storage
- Cache databases
- Anything where "one writer" is fine

For Hermes specifically — given sub-agents, parallel tools, scheduled jobs, and Docker integration — the single-writer model is the limiting factor.

---

## Migration Path

If you've started in DuckDB or SQLite, dlt makes migration trivial:

```python
# point dlt at Postgres instead — same schema, same data
pipeline = dlt.pipeline(
    pipeline_name="hermes_memory",
    destination="postgres",  # was "duckdb"
    dataset_name="agent_data"
)
pipeline.run(your_existing_data)
```

dlt handles the schema translation. You can migrate incrementally — keep DuckDB for analytics, move state/memory to Postgres.

---

## Bottom Line

For a multi-agent system with:
- Concurrent reads/writes from multiple agents
- Short-term memory across sessions
- Scheduled background jobs
- Docker-based pipelines
- Future semantic search via embeddings

→ **Postgres is the right backbone.** Free locally, light on resources, plays well with Docker, fully transactional, supports concurrent writers, integrates with dlt, and has pgvector for vector search.

DuckDB stays in the toolkit for analytics. SQLite for genuinely single-process needs. Postgres for everything else.