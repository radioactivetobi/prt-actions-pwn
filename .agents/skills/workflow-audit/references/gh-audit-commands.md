# GitHub CLI Audit Commands

Reference for `gh api` commands used during live audits of remote repositories.

All commands assume `gh` CLI is installed and authenticated (`gh auth status`).
For paginated results, append `--paginate` or use `--jq ".[]"` with filtering.

---

## General Reconnaissance

| Command | Purpose |
|---------|----------|
| `gh api repos/{owner}/{repo}` | Repo metadata (visibility, default branch, fork status) |
| `gh api repos/{owner}/{repo}/collaborators --jq ".[].login"` | List collaborators with push access |
| `gh api repos/{owner}/{repo}/branches --jq ".[].name"` | List all branches |
| `gh api repos/{owner}/{repo}/environments --jq ".environments[].name"` | List deployment environments |
| `gh api repos/{owner}/{repo}/interaction-limits` | Interaction limits for first-time contributors |

## PRT Pattern Audit Commands

### PRT-001: pull_request_target + Checkout PR Head

Check if any workflow uses `pull_request_target`:

```bash
gh api repos/{owner}/{repo}/actions/workflows --jq ".workflows[] | .path"
```

Then fetch each workflow YAML and search for `pull_request_target`:

```bash
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq ".content" | python -m base64 -d
```

Look for `ref: ${{ github.event.pull_request.head.sha }}` or `ref: ${{ github.event.pull_request.head.ref }}` in the same workflow.

### PRT-002: Credential Persistence (persist-credentials)

Fetch each workflow YAML and check for `actions/checkout` steps that lack `persist-credentials: false`:

```bash
# List all workflow files
gh api repos/{owner}/{repo}/actions/workflows --jq ".workflows[] | .path"

# Fetch a specific workflow YAML (base64-decoded)
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq ".content" | python -m base64 -d
```

A checkout step is vulnerable if it uses `actions/checkout` without `persist-credentials: false`.

### PRT-003: Script Injection via Untrusted PR Data

Fetch each workflow YAML and search for `${{ github.event.pull_request.* }}` interpolated directly in `run:` blocks:

```bash
# Same fetch as PRT-002, then grep for PR context in run blocks
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq ".content" | python -m base64 -d
```

Look for patterns like:
- `${{ github.event.pull_request.title }}` in `run:`
- `${{ github.event.pull_request.body }}` in `run:`
- `${{ github.event.pull_request.head.ref }}` in `run:`

### PRT-004: Missing or Overly Broad Permissions

Check repository-level Actions permissions:

```bash
gh api repos/{owner}/{repo}/actions/permissions
```

This returns:
- `enabled`: Whether Actions are enabled
- `allowed_actions`: Which actions are permitted (`all`, `local_only`, `selected`)
- `can_approve_pull_request_reviews`: Whether PRs from public forks can approve

Also check each workflow YAML for top-level and job-level `permissions:` blocks.

### PRT-005: Unpinned Action Versions

Fetch each workflow YAML and look for `uses:` references by tag instead of SHA:

```bash
# List workflows
gh api repos/{owner}/{repo}/actions/workflows --jq ".workflows[] | .path"

# Fetch and check each one
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq ".content" | python -m base64 -d
```

Vulnerable patterns:
- `uses: actions/checkout@v4` (tag, not SHA)
- `uses: actions/setup-python@v5` (tag, not SHA)

Hardened patterns:
- `uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11` (SHA-pinned)

### PRT-006: First-Time Contributor Approval Bypass

Check if the repository requires approvals for first-time contributors:

```bash
# Check branch protection (includes required reviews)
gh api repos/{owner}/{repo}/branches/{branch}/protection --jq ".required_pull_request_reviews"
```

If the response is `404` or `required_pull_request_reviews` is absent, there are no required reviews.

Also check interaction limits:

```bash
gh api repos/{owner}/{repo}/interaction-limits
```

### PRT-007: Path-Based Trigger Abuse

Fetch each workflow YAML and check for `paths:` filters on `pull_request_target`:

```bash
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq ".content" | python -m base64 -d
```

Vulnerable: `paths:` on `pull_request_target` that do not include `.github/workflows/**`.

### PRT-008: Untrusted workflow_dispatch / repository_dispatch

Fetch each workflow YAML and look for `workflow_dispatch` or `repository_dispatch` triggers with `inputs` that are passed to `run:` blocks:

```bash
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq ".content" | python -m base64 -d
```

### PRT-009: Secrets in Untrusted Code Context

List repository secrets (names only, never values):

```bash
gh api repos/{owner}/{repo}/actions/secrets --jq ".secrets[] | .name"
```

List organization secrets available to the repo:

```bash
gh api repos/{owner}/{repo}/actions/organization-secrets --jq ".secrets[] | .name"
```

Cross-reference secret names with workflow YAML to find secrets used in jobs that also check out PR code.

### PRT-010: Forked Action References

Fetch each workflow YAML and check `uses:` references:

- Actions from non-canonical repositories (not `actions/*`, `github/*`, or known publishers)
- Local actions (`./.github/actions/*`) in `pull_request_target` workflows

```bash
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq ".content" | python -m base64 -d
```

---

## Branch Protection Audit

```bash
# Full branch protection for the default branch
gh api repos/{owner}/{repo}/branches/{branch}/protection
```

Key fields to check:
- `required_pull_request_reviews.dismiss_stale_reviews`
- `required_pull_request_reviews.require_code_owner_reviews`
- `required_pull_request_reviews.required_approving_review_count`
- `restrictions` (who can push)
- `required_status_checks` (which checks must pass)
- `enforce_admins` (do protections apply to admins)

## Environment Protection Audit

```bash
# List environments
gh api repos/{owner}/{repo}/environments --jq ".environments[] | .name"

# Get protection rules for a specific environment
gh api repos/{owner}/{repo}/environments/{environment_name}/protection_rules
```

## Workflow Permissions Audit

```bash
# Default GITHUB_TOKEN permissions for the repository
gh api repos/{owner}/{repo}/actions/permissions --jq ".default_workflow_permissions"
```

Key fields:
- `default_workflow_permissions.permissions` (read/write scope)
- `can_approve_pull_request_reviews` (can fork PR workflows auto-approve)

## Tips

- Use `--paginate` for endpoints that return large result sets (e.g., listing all workflows or runs)
- Use `--jq` for filtering and formatting to extract only the fields you need
- For repos with many workflows, fetch the workflow list first, then fetch each YAML individually
- Base64-decode content API responses: `gh api repos/{owner}/{repo}/contents/{path} --jq ".content" | python -m base64 -d`
- Rate limits: `gh api` respects GitHub API rate limits. Use `--paginate` with caution on large orgs
