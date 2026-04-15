# GitHub CLI Reconnaissance Commands

Reference for `gh api` commands used during live target analysis and attack simulation.

All commands assume `gh` CLI is installed and authenticated (`gh auth status`).
For paginated results, append `--paginate` or use `--jq ".[]"` with filtering.

---

## Target Fingerprinting

| Command | Purpose |
|---------|----------|
| `gh api repos/{owner}/{repo}` | Repo metadata: visibility, default branch, fork status, language, size |
| `gh api repos/{owner}/{repo} --jq ".visibility,.default_branch,.fork,.language"` | Quick fingerprint |
| `gh api repos/{owner}/{repo}/collaborators --jq ".[].login"` | List collaborators (who has push access) |
| `gh api repos/{owner}/{repo}/contributors --jq ".[].login"` | List contributors |
| `gh api repos/{owner}/{repo}/branches --jq ".[].name"` | List all branches |
| `gh api repos/{owner}/{repo}/tags --jq ".[].name"` | List tags (for version-based targeting) |

## Workflow Enumeration

Enumerate all workflow files to identify the attack surface:

```bash
# List all workflow files
gh api repos/{owner}/{repo}/actions/workflows --jq ".workflows[] | {name: .name, path: .path, state: .state}"

# Fetch a specific workflow YAML (base64-decoded)
gh api repos/{owner}/{repo}/contents/.github/workflows/{filename} --jq ".content" | python -m base64 -d

# List recent workflow runs
gh api repos/{owner}/{repo}/actions/runs --jq ".workflow_runs[] | {id: .id, name: .name, status: .status, conclusion: .conclusion}"
```

## Attack Surface Analysis

### EXFIL Phase — Identify Token Exfiltration Vectors

```bash
# Check for pull_request_target workflows
gh api repos/{owner}/{repo}/actions/workflows --jq ".workflows[] | .path"
# Then fetch each workflow YAML and search for:
# - on: pull_request_target
# - ref: ${{ github.event.pull_request.head.sha }}
# - persist-credentials: true (or missing persist-credentials: false)
```

### RECON Phase — Identify Enumeration Targets

```bash
# List repository secrets (names only)
gh api repos/{owner}/{repo}/actions/secrets --jq ".secrets[] | {name: .name, created_at: .created_at}"

# List org secrets available to the repo
gh api repos/{owner}/{repo}/actions/organization-secrets --jq ".secrets[] | {name: .name, visibility: .visibility}"

# List environment secrets
gh api repos/{owner}/{repo}/environments --jq '.environments[].name' | \
  while read -r env; do
    gh api "repos/{owner}/{repo}/environments/$env/secrets" --jq '.secrets[].name'
  done

# Check Actions permissions (what the GITHUB_TOKEN can do)
gh api repos/{owner}/{repo}/actions/permissions
```

### DISPATCH Phase — Identify Privilege Escalation Paths

```bash
# Check branch protection (are dispatch pushes blocked?)
gh api repos/{owner}/{repo}/branches/{branch}/protection

# Check for workflow_dispatch workflows
# Fetch each workflow YAML and look for:
# - on: workflow_dispatch
# - on: repository_dispatch
# - inputs that flow into run: blocks

# List open PRs (injection vectors)
gh api repos/{owner}/{repo}/pulls?state=open --jq ".[] | {number: .number, title: .title, author: .user.login, author_association: .author_association}"
```

### LABEL_BYPASS Phase — Identify Approval Gate Bypasses

```bash
# Check branch protection required reviews
gh api repos/{owner}/{repo}/branches/{branch}/protection --jq ".required_pull_request_reviews"

# Check if maintainers can approve PRs from first-time contributors
gh api repos/{owner}/{repo}/actions/permissions --jq ".can_approve_pull_request_reviews"

# List labels used in the repo
gh api repos/{owner}/{repo}/labels --jq ".[] | .name"

# Check interaction limits for public repos
gh api repos/{owner}/{repo}/interaction-limits
```

### DELAYED Phase — Identify Persistence Vectors

```bash
# Check repo language (determines injection vector)
gh api repos/{owner}/{repo} --jq ".language"

# Check for conftest.py, package.json, build.rs in recent PRs
gh api repos/{owner}/{repo}/pulls?state=open --jq ".[] | {number: .number, changed_files: .changed_files}"

# List repo contents (look for language-specific config files)
gh api repos/{owner}/{repo}/contents/ --jq ".[].name"
```

## Environment & Protection Analysis

```bash
# List deployment environments
gh api repos/{owner}/{repo}/environments --jq ".environments[] | {name: .name, protection_rules: .protection_rules}"

# Check specific environment protection rules
gh api repos/{owner}/{repo}/environments/{env_name}/deployment_protection_rules

# Full branch protection details
gh api repos/{owner}/{repo}/branches/{branch}/protection
```

## Workflow Run Analysis

```bash
# List recent workflow runs (identify active attacks)
gh api repos/{owner}/{repo}/actions/runs --jq ".workflow_runs[:10][] | {id: .id, name: .name, event: .event, actor: .actor.login, status: .status, conclusion: .conclusion, created_at: .created_at}"

# Get logs for a specific run
gh api repos/{owner}/{repo}/actions/runs/{run_id}/logs

# List jobs for a run
gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs --jq ".jobs[] | {name: .name, conclusion: .conclusion, started_at: .started_at}"
```

## Tips

- Use `--paginate` for endpoints that return large result sets
- Use `--jq` for filtering to extract only the fields you need
- For repos with many workflows, fetch the list first then fetch each YAML individually
- Base64-decode content API responses: `gh api repos/{owner}/{repo}/contents/{path} --jq ".content" | python -m base64 -d`
- The `gh api` commands can be combined with `execute` tool for live analysis during simulation
- Rate limits apply — avoid fetching full run logs unless specifically needed
