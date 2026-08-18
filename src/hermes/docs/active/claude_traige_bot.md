github workflow file using claude

lets swap this out to use ollama (local cloud) models


name: Claude Issue Triage

# Thin shim. Logic + system prompt live in
# aretecp/github-actions/.github/workflows/claude-issue-triage.yml.
#
# Auth: OIDC. ANTHROPIC_API_KEY is loaded from Infisical at
# arete-internal/prod/areteos at workflow runtime — no stored credentials
# in this repo's GH secrets.

on:
  issues:
    types: [opened]
  issue_comment:
    types: [created]

# The reusable workflow declares per-job permissions, but a caller's grant
# is the ceiling — reusable jobs can't use more than the caller allowed.
# Explicitly grant the union of what the shared workflow needs.
permissions:
  contents: read
  issues: write
  id-token: write

jobs:
  triage:
    uses: aretecp/github-actions/.github/workflows/claude-issue-triage.yml@v1
    with:
      infisical-identity-id: ${{ vars.INFISICAL_OIDC_IDENTITY_ID }}
      infisical-project-slug: arete-internal
      infisical-env: prod
      infisical-path: /areteos