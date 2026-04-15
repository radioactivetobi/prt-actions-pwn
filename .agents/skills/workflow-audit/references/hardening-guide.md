# CI/CD Supply Chain Hardening Guide

Remediation strategies for each PRT Scan vulnerability pattern, with before/after code snippets and attack phase mapping.

---

## PRT-001: pull_request_target + Checkout PR Head

**Attack Phase Blocked**: EXFIL (Phase 1)

### Remediation: Use `pull_request` instead of `pull_request_target`

If you don't need write access to the repository, use `pull_request` which runs in the fork context with a read-only token.

**Before** (Vulnerable):
```yaml
on:
  pull_request_target:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
```

**After** (Hardened):
```yaml
on:
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        # No ref override needed — checks out PR code safely in fork context
```

### Remediation: Use `workflow_run` for privileged operations

If you need write access (e.g., to comment on PRs, label PRs), split the workflow: use `pull_request` for untrusted code and `workflow_run` for privileged operations.

**Before** (Vulnerable):
```yaml
on:
  pull_request_target:

jobs:
  test-and-comment:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: ./run-tests.sh
      - uses: actions/github-script@v7
        with:
          script: github.rest.issues.createComment({...})
```

**After** (Hardened — split into two workflows):
```yaml
# Workflow 1: Untrusted code runs in fork context
name: PR Tests
on:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ./run-tests.sh
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: results.json

# Workflow 2: Privileged operations in base repo context
name: PR Comment
on:
  workflow_run:
    workflows: ["PR Tests"]
    types: [completed]

jobs:
  comment:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: test-results
      - uses: actions/github-script@v7
        with:
          script: github.rest.issues.createComment({...})
```

### Remediation: If you must use `pull_request_target`, never check out PR code

**Before** (Vulnerable):
```yaml
on:
  pull_request_target:

jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
```

**After** (Hardened — checkout base only):
```yaml
on:
  pull_request_target:

jobs:
  label:
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        # No ref override — checks out base branch only
      - uses: actions/github-script@v7
        with:
          script: |
            // Only use PR metadata, never run PR code
            const labels = context.payload.pull_request.labels;
```

---

## PRT-002: Credential Persistence via actions/checkout

**Attack Phase Blocked**: EXFIL (Phase 1)

### Remediation: Set `persist-credentials: false`

**Before** (Vulnerable):
```yaml
steps:
  - uses: actions/checkout@v4
  - run: |
      # Token is accessible in .git/config
      git config --get http.https://github.com/.extraheader
```

**After** (Hardened):
```yaml
steps:
  - uses: actions/checkout@v4
    with:
      persist-credentials: false
  - run: |
      # Token is no longer saved to .git/config
      # git config --get http.https://github.com/.extraheader → empty
```

### Remediation: Use SSH keys or deploy keys instead of GITHUB_TOKEN

For workflows that need persistent git authentication, use deploy keys scoped to specific repositories.

**Before** (Vulnerable):
```yaml
steps:
  - uses: actions/checkout@v4
    # persist-credentials: true (default) leaks GITHUB_TOKEN
  - run: git push  # Uses leaked GITHUB_TOKEN
```

**After** (Hardened):
```yaml
steps:
  - uses: actions/checkout@v4
    with:
      persist-credentials: false
      ssh-key: ${{ secrets.DEPLOY_KEY }}
  - run: git push  # Uses scoped deploy key, not GITHUB_TOKEN
```

---

## PRT-003: Script Injection via Untrusted PR Data

**Attack Phase Blocked**: EXFIL (Phase 1), RECON (Phase 2)

### Remediation: Use environment variables instead of direct interpolation

**Before** (Vulnerable):
```yaml
- run: echo "PR title: ${{ github.event.pull_request.title }}"
- run: ./deploy.sh "${{ github.event.pull_request.head.ref }}"
```

**After** (Hardened):
```yaml
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
    PR_BRANCH: ${{ github.event.pull_request.head.ref }}
  run: |
    echo "PR title: $PR_TITLE"
    ./deploy.sh "$PR_BRANCH"
```

### Remediation: Use `github-script` action for GitHub API calls

**Before** (Vulnerable):
```yaml
- run: gh pr comment ${{ github.event.pull_request.number }} --body "${{ github.event.pull_request.title }}"
```

**After** (Hardened):
```yaml
- uses: actions/github-script@v7
  with:
    script: |
      await github.rest.issues.createComment({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.payload.pull_request.number,
        body: `PR: ${context.payload.pull_request.title}`
      });
```

### Remediation: Validate and sanitize inputs

**Before** (Vulnerable):
```yaml
- run: ./test.sh "${{ github.event.inputs.target }}"
```

**After** (Hardened):
```yaml
- name: Validate input
  run: |
    if [[ ! "${{ github.event.inputs.target }}" =~ ^[a-zA-Z0-9_-]+$ ]]; then
      echo "Invalid input"
      exit 1
    fi
- env:
    TARGET: ${{ github.event.inputs.target }}
  run: ./test.sh "$TARGET"
```

---

## PRT-004: Missing or Overly Broad Permissions

**Attack Phase Blocked**: DISPATCH (Phase 3), LABEL_BYPASS (Phase 4)

### Remediation: Add explicit minimal `permissions:` blocks

**Before** (Vulnerable):
```yaml
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    # No permissions block — inherits repo defaults (often contents: write)
```

**After** (Hardened):
```yaml
on: push
permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    # Token is now read-only for contents
```

### Remediation: Scope permissions to the job level

**Before** (Vulnerable):
```yaml
permissions:
  contents: write
  packages: write
  id-token: write
```

**After** (Hardened — job-level scoping):
```yaml
permissions:
  contents: read

jobs:
  build:
    permissions:
      contents: read
    steps:
      - run: ./build.sh

  deploy:
    needs: build
    permissions:
      contents: read
      packages: write
      id-token: write
    steps:
      - run: ./deploy.sh
```

### Remediation: Use `id-token: write` only for OIDC

**Before** (Vulnerable):
```yaml
permissions:
  id-token: write
  contents: read
```

**After** (Hardened — only on the job that needs it):
```yaml
permissions:
  contents: read

jobs:
  build:
    permissions:
      contents: read
    steps:
      - run: ./build.sh

  deploy-to-cloud:
    needs: build
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/deploy
```

---

## PRT-005: Unpinned Action Versions

**Attack Phase Blocked**: Supply chain vector (pre-attack)

### Remediation: Pin actions to commit SHA

**Before** (Vulnerable):
```yaml
- uses: actions/checkout@v4
- uses: actions/setup-node@v4
- uses: actions/cache@v3
```

**After** (Hardened):
```yaml
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
- uses: actions/setup-node@60edb5dd541a7dc3869a40e5f7b3c6e3b8e4e4e4  # v4.0.3
- uses: actions/cache@e12d46a901c7485e154c2b5e8e3b6b3e9a8b8b8b  # v3.3.2
```

### Remediation: Use a pinning automation tool

Add [pinact](https://github.com/suzuki-shunsuke/pinact) or [workflow-pin](https://github.com/nickvdyck/workflow-pin) to automatically pin and update action versions:

```yaml
# In a separate workflow
name: Pin Actions
on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly
  workflow_dispatch:

jobs:
  pin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
      - run: |
          pinact run  # Automatically pins all actions to SHA
```

---

## PRT-006: First-Time Contributor Approval Bypass

**Attack Phase Blocked**: Entry vector (pre-EXFIL)

### Remediation: Require approval for all outside collaborators

**Repository Settings**:
- Go to Settings → Actions → General
- Under "Fork pull request workflows from outside collaborators"
- Select **"Require approval for all outside collaborators"** (not just first-time)

### Remediation: Add author_association checks in workflows

**Before** (Vulnerable):
```yaml
on:
  pull_request_target:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
```

**After** (Hardened):
```yaml
on:
  pull_request_target:

jobs:
  approve:
    runs-on: ubuntu-latest
    if: github.event.pull_request.author_association != 'MEMBER' &&
        github.event.pull_request.author_association != 'OWNER' &&
        github.event.pull_request.author_association != 'COLLABORATOR'
    steps:
      - run: echo "External PR requires approval"

  build:
    needs: approve
    if: github.event.pull_request.author_association == 'MEMBER' ||
        github.event.pull_request.author_association == 'OWNER' ||
        github.event.pull_request.author_association == 'COLLABORATOR'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
```

---

## PRT-007: Path-Based Trigger Abuse

**Attack Phase Blocked**: Entry vector (pre-EXFIL)

### Remediation: Include `.github/workflows/**` in path filters

**Before** (Vulnerable):
```yaml
on:
  pull_request_target:
    paths:
      - 'docs/**'
      - 'README.md'
```

**After** (Hardened):
```yaml
on:
  pull_request_target:
    paths:
      - 'docs/**'
      - 'README.md'
      - '.github/workflows/**'  # Detect workflow modifications
```

### Remediation: Avoid path filters on `pull_request_target`

The safest approach is to not use path filters with `pull_request_target` at all, since path filters can be bypassed by including changes in monitored paths.

**Before** (Vulnerable):
```yaml
on:
  pull_request_target:
    paths:
      - 'src/**'
```

**After** (Hardened — no path filter):
```yaml
on:
  pull_request_target:
    # No path filter — all PRs trigger, but workflow is safe
    # because it never checks out PR code
```

---

## PRT-008: Untrusted workflow_dispatch / repository_dispatch

**Attack Phase Blocked**: DISPATCH (Phase 3)

### Remediation: Sanitize and validate all dispatch inputs

**Before** (Vulnerable):
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
      - run: ./deploy.sh ${{ github.event.inputs.target }}
```

**After** (Hardened):
```yaml
on:
  workflow_dispatch:
    inputs:
      target:
        description: 'Target to deploy'
        required: true
        type: choice
        options:
          - staging
          - production

jobs:
  deploy:
    steps:
      - env:
          TARGET: ${{ github.event.inputs.target }}
        run: |
          ./deploy.sh "$TARGET"
```

### Remediation: Restrict dispatch triggers to trusted actors

```yaml
jobs:
  authorize:
    runs-on: ubuntu-latest
    if: github.actor == 'trusted-maintainer' || contains(fromJSON('["maintainer1", "maintainer2"]'), github.actor)
    steps:
      - run: echo "Authorized"

  deploy:
    needs: authorize
    steps:
      - run: ./deploy.sh
```

---

## PRT-009: Secrets in Untrusted Code Context

**Attack Phase Blocked**: EXFIL (Phase 1)

### Remediation: Never expose secrets in jobs that run untrusted code

**Before** (Vulnerable):
```yaml
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm install && npm test
        env:
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_KEY }}
```

**After** (Hardened — split into trusted and untrusted jobs):
```yaml
jobs:
  # Untrusted code runs without secrets
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install && npm test
        # No secrets exposed

  # Trusted job handles secrets
  publish:
    needs: test
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
        # Checks out base branch, not PR code
      - run: npm publish
        env:
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Remediation: Use OIDC instead of long-lived secrets

**Before** (Vulnerable):
```yaml
- name: Configure AWS
  run: |
    aws configure set aws_access_key_id ${{ secrets.AWS_KEY }}
    aws configure set aws_secret_access_key ${{ secrets.AWS_SECRET }}
```

**After** (Hardened — OIDC):
```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-actions
    aws-region: us-east-1
  # No long-lived secrets needed — uses short-lived OIDC tokens
```

---

## PRT-010: Forked Action References

**Attack Phase Blocked**: Supply chain vector (pre-attack)

### Remediation: Use canonical action repositories

**Before** (Vulnerable):
```yaml
- uses: some-user/forked-action@main
- uses: ./.github/actions/my-action
```

**After** (Hardened):
```yaml
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # Official, SHA-pinned
- uses: ./.github/actions/my-action
  # Only safe if the workflow doesn't use pull_request_target
  # or if the action is reviewed and protected
```

### Remediation: Protect local composite actions

If using local actions (`.github/actions/*`), ensure they cannot be modified by untrusted PRs:

```yaml
# In pull_request_target workflows, never reference local actions
# that could be modified by the PR author

# Instead, use the base branch version explicitly:
- uses: ./.github/actions/my-action@main
  # This references the main branch version, not the PR version
```

---

## Quick Reference: Hardening Checklist

| # | Pattern | Key Fix | Phase Blocked |
|---|---------|---------|---------------|
| PRT-001 | `pull_request_target` + checkout PR | Use `pull_request` or `workflow_run` | EXFIL |
| PRT-002 | `persist-credentials: true` | Set `persist-credentials: false` | EXFIL |
| PRT-003 | Untrusted PR data in `run:` | Use env vars, `github-script`, or sanitize | EXFIL, RECON |
| PRT-004 | Missing/broad `permissions:` | Add minimal explicit permissions | DISPATCH, LABEL_BYPASS |
| PRT-005 | Unpinned action versions | Pin to commit SHA | Supply chain |
| PRT-006 | First-time contributor bypass | Require approval for all outside collaborators | Entry vector |
| PRT-007 | Path-based trigger abuse | Include `.github/workflows/**` or remove path filters | Entry vector |
| PRT-008 | Untrusted dispatch inputs | Use `type: choice`, validate inputs, restrict actors | DISPATCH |
| PRT-009 | Secrets in untrusted context | Split trusted/untrusted jobs, use OIDC | EXFIL |
| PRT-010 | Forked action references | Use canonical repos, pin to SHA | Supply chain |

## Defense-in-Depth Strategy

No single remediation is sufficient. The PRT Scan campaign demonstrates a **5-phase attack chain** where each phase builds on the previous one. Apply hardening at every level:

1. **Prevent entry** (PRT-006, PRT-007) — Make it harder for attackers to trigger workflows
2. **Prevent token theft** (PRT-001, PRT-002, PRT-003) — Even if triggered, the attacker can't steal credentials
3. **Limit blast radius** (PRT-004, PRT-009) — Even with a token, damage is contained
4. **Prevent escalation** (PRT-008) — Dispatch inputs can't be weaponized
5. **Prevent supply chain** (PRT-005, PRT-010) — Actions can't be silently replaced