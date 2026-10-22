---
name: dbt-model-yaml
description: >-
  Author or edit dbt model YAML (schema.yml, staging.yml, intermediate.yml, marts.yml)
  so it declares real database guarantees — primary keys, unique/check/not-null
  constraints, foreign keys, indexes, and enforced contracts — instead of only
  descriptions and tests. Use whenever adding a model to a .yml, documenting columns,
  adding tests, being asked to "set a primary key", "add constraints", "add an index",
  "enforce a contract", "add data types", or when reviewing a dbt YAML file for what it
  is failing to guarantee. Also use when choosing incremental_strategy, unique_key, or
  on_schema_change, since those interact directly with constraints. Covers
  dbt-postgres specifics — which constraints are actually enforced, when indexes get
  created, and the cost of turning a contract on.
---

# Filling out dbt model YAML

Default posture: a column entry that has only a `description` is unfinished. Push
each model toward declaring its grain in the database, not just in prose.

## First, confirm the adapter

Constraint and index behavior is entirely adapter-specific. Do not reason from the
generic dbt docs matrix. Check what is actually installed:

```bash
uv run dbt --version                    # core + adapter versions
grep -n "type:" data_center_research/profiles.yml
```

This project is **dbt-core 1.12 / dbt-postgres 1.11**, targeting a postgres endpoint.
Everything below is verified against that installed adapter. If the adapter changes,
re-verify before applying — `grep -n "CONSTRAINT_SUPPORT" -A 8` in the adapter's
`impl.py` is the authoritative answer.

## Decision order

Work in this order. Each step depends on the one above it.

**1. Name the grain.** One row per what? Write it in the model description in those
words. If you cannot state the grain in one sentence, stop and read the SQL — the
rest of the YAML is guesswork until you can.

**2. Identify the key column.** Usually a `dbt_utils.generate_surrogate_key(...)`.
The arguments to that macro *are* the grain. If the surrogate key is built over
`accession_number + attachment_url`, the grain is one row per attachment, and any
description claiming "one row per filing" is wrong.

**3. Decide whether to enforce a contract.** Constraints require
`contract: enforced: true`. See the tax below — it is real, and it is worth paying
for staging models and marts that downstream work depends on.

**4. Add constraints,** then **5. indexes,** then **6. prune redundant tests.**

## The contract tax

`constraints:` are only applied when the model carries an enforced contract:

```yaml
models:
  - name: my_model
    config:
      contract:
        enforced: true
```

Three costs come with that, all of which must be handled in the same edit:

**Every column needs a `data_type`.** Not just the constrained one. dbt calls
`get_assert_columns_equivalent(sql)` and fails the build if the model's SELECT
returns a column that is missing, extra, or mistyped relative to the YAML. Get the
types from a real source, never from guessing:

- This repo lands raw tables via dlt — [dlt_schemas/export/Edgar_Filings.schema.yaml](../../../dlt_schemas/export/Edgar_Filings.schema.yaml)
  is the source of truth for anything passing through unchanged.
- dlt's postgres destination maps its `timestamp` to `timestamp with time zone`.
- `generate_surrogate_key` returns `text` on postgres (it's an `md5(...)`).
- Otherwise query `information_schema.columns` for the built relation.

**Column order in YAML must match the SELECT order.** The contract check is
positional.

**Incremental models must set `on_schema_change` explicitly.** dbt refuses to even
parse otherwise: *"Models materialized as incremental with contracts enabled must set
on_schema_change to 'append_new_columns' or 'fail'."* Prefer `append_new_columns` —
the contract is validated *before* schema-change handling runs, so a column added to
the SQL but not the YAML fails on the contract either way. `append_new_columns` gives
up no safety and saves a full refresh when you add a blessed column.

## Constraints on postgres

All five types are `ENFORCED` here — verified at
`.venv/lib/python3.12/site-packages/dbt/adapters/postgres/impl.py:89-95`. This is
*not* the dbt default; the base adapter treats `unique` and `primary_key` as
`NOT_ENFORCED` and `check` as `NOT_SUPPORTED`. On postgres they are real DDL.

```yaml
      - name: filing_pk
        data_type: text
        constraints:
          - type: primary_key
      - name: score
        data_type: integer
        constraints:
          - type: check
            expression: "score between 0 and 3"
```

Reach for `primary_key` on the grain column of every staging and intermediate model.
Reach for `check` on anything with a known domain — score ranges, flag columns that
should only be 0/1, enum-ish strings. A check constraint is strictly better than an
`accepted_values` test: it rejects bad rows at write time rather than reporting them
after they have already landed.

**Foreign keys: default to not using them here.** They are enforced on postgres, but
`postgres__drop_relation` issues `drop table if exists ... cascade`
(`dbt/include/postgres/macros/relations/table/drop.sql:2`). Full-refreshing a parent
therefore drops the child's FK constraint and leaves the child silently unconstrained
until it is itself rebuilt. Use a `relationships` test instead unless someone has
explicitly asked for referential integrity in the database.

## Indexes

Indexes are **not** a column property. They go in the model's `config`, either in the
`.sql` or under `config:` in the YAML:

```yaml
    config:
      contract:
        enforced: true
      indexes:
        - columns: ['start_date']
        - columns: ['accession_number']
        - columns: ['filing_pk']
          unique: true
          type: btree
```

Accepted keys are `columns`, `unique`, and `type` only.

**The trap: indexes are only created on first build or full refresh.** From
`macros/materializations/models/incremental/incremental.sql:70-72`:

```jinja
{% if existing_relation is none or existing_relation.is_view or should_full_refresh() %}
  {% do create_indexes(relation_for_indexes) %}
{% endif %}
```

Adding an `indexes:` config to a model that already exists as a table does nothing
until `dbt run --full-refresh -s that_model`. Always say this out loud when adding
one — otherwise it looks applied and isn't. The same applies to constraints: dbt only
emits them in the `CREATE TABLE`, never as a later `ALTER`.

What to index in this project: the incremental watermark column (`start_date`), any
column used as a join key downstream, and the `unique_key`. A `primary_key`
constraint already creates a unique index, so do not also declare an index on that
column.

## Constraints and incremental strategy interact

On postgres, setting `unique_key` alone already selects delete+insert — no
`incremental_strategy` line needed
(`dbt/include/postgres/macros/materializations/incremental_strategies.sql:1-7`).
Without `unique_key`, the strategy is `append`.

This matters directly for keys. An append-mode incremental whose filter uses `>=`
against its own watermark re-selects and re-inserts the boundary period on every run.
Without a PK that silently duplicates rows; with a PK the run hard-fails on the
constraint. So whenever adding a `primary_key` to an incremental model, check the
`is_incremental()` filter in the same edit and set `unique_key` if the filter can
re-emit existing rows.

The pairing is mutually reinforcing: delete+insert issues
`DELETE FROM target WHERE (key) IN (SELECT DISTINCT key FROM temp)`, which is a
sequential scan unless the key is indexed. The primary key's unique index is what
keeps that delete cheap as the table grows.

## Tests after constraints

Constraints fail the build at write time; tests report after the fact. Keep both only
where the redundancy buys something:

| Once you have | This test is | Because |
|---|---|---|
| `primary_key` constraint | redundant, but cheap to keep | surfaces as a clean `dbt test` failure instead of an insert error |
| `not_null` constraint | fully redundant | the PK already implies it |
| `check` constraint | replaces `accepted_values` | rejects rather than reports |
| no constraint (view model) | required | views carry no constraints at all |

Note that views cannot hold constraints or indexes. If a model needs a real key, it
needs to be a table or incremental.

## Verify before reporting done

```bash
DB_HOST=x DB_PORT=5432 DB_USER=x DB_PASSWORD=x DB_NAME=x \
  uv run dbt parse --project-dir data_center_research --profiles-dir data_center_research
```

`dbt parse` needs no live connection and catches the whole class of contract and
config errors — missing `on_schema_change`, malformed constraint blocks, bad YAML
shape. Run it after every YAML edit. It does not validate `data_type` values against
the warehouse; only a real `dbt run` does that.

When the change adds a constraint or index to an existing table, state plainly that a
`--full-refresh` is required for it to take effect, and that the refresh will fail if
the existing data already violates the new constraint.
