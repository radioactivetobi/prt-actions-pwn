---
name: workflow-audit
description: "Blue team skill for detecting CI/CD supply chain vulnerabilities in GitHub Actions workflows. Use when: scanning workflows for PRT Scan patterns, auditing pull_request_target usage, checking credential persistence, finding script injection vectors, reviewing permissions blocks, generating security findings reports."
argument-hint: "Path to workflow file/directory OR 'owner/repo' for live GitHub audit (default: .github/workflows/)"
user-invocable: true
---

# Workflow Audit Skill

Detect CI/CD supply chain vulnerabilities in GitHub Actions workflows using the PRT Scan / TeamPCP pattern catalog.

## Procedure

### Step 1: Discovery

Determine whether the target is a local path or a remote repository:

**Local mode** (default) — target is a file path or directory:
```
Find all *.yml and *.yaml files under .github/workflows/
If a specific file was provided, read that file only
Otherwise, read every workflow file in the directory
```

**Live audit mode** — target matches `owner/repo` format:
```
1. gh api repos/{owner}/{repo} — Get repo metadata (visibility, default branch, fork status)
2. gh api repos/{owner}/{repo}/actions/workflows --jq ".workflows[] | .path" — List all workflow files
3. For each workflow, fetch YAML content:
   gh api repos/{owner}/{repo}/contents/{path} --jq ".content" | python -m base64 -d
4. gh api repos/{owner}/{repo}/actions/permissions — Check Actions permissions and default GITHUB_TOKEN scope
5. gh api repos/{owner}/{repo}/actions/secrets --jq ".secrets[] | .name" — List repository secrets
6. gh api repos/{owner}/{repo}/actions/organization-secrets --jq ".secrets[] | .name" — List org secrets available to repo
7. gh api repos/{owner}/{repo}/branches/{branch}/protection — Check branch protection rules
8. gh api repos/{owner}/{repo}/interaction-limits — Check first-time contributor restrictions
9. gh api repos/{owner}/{repo}/environments — List deployment environments and protection rules
```

See `references/gh-audit-commands.md` for the full command reference.

### Step 2: Pattern Matching

For each workflow, check against the **PRT Scan Vulnerability Pattern Catalog** (see references/prt-scan-patterns.md). Evaluate every pattern:

| Pattern ID | Check |
|------------|-------|
| PRT-001 | Does the workflow use `pull_request_target` with `actions/checkout` on PR head? |
| PRT-002 | Does `actions/checkout` lack `persist-credentials: false`? |
| PRT-003 | Does the workflow interpolate untrusted PR data into `run:` blocks? |
| PRT-004 | Is the `permissions:` block missing or overly broad? |
| PRT-005 | Are actions pinned by SHA rather than tag? |
| PRT-006 | Can first-time contributors trigger the workflow without approval? |
| PRT-007 | Are there path-based triggers that could be exploited? |
| PRT-008 | Does the workflow use `workflow_run` or `repository_dispatch` from untrusted sources? |
| PRT-009 | Are secrets accessible in jobs that run untrusted code? |
| PRT-010 | Does the workflow check out PR-owned code paths (e.g., custom actions from forks)? |

For live audits, use the `gh api` commands from Step 1 to gather the data needed for each pattern check. See `references/gh-audit-commands.md` for pattern-specific commands.

### Step 3: Severity Assessment

Classify each finding:

- **CRITICAL** — Directly exploitable for token theft or code execution (PRT-001, PRT-002 with PRT-001, PRT-003 with PRT-001)
- **HIGH** — Significant exposure that enables privilege escalation (PRT-002 alone, PRT-004, PRT-009)
- **MEDIUM** — Increases attack surface but requires additional conditions (PRT-005, PRT-006, PRT-007, PRT-008)
- **LOW** — Best practice violation with limited direct exploitability (PRT-010, PRT-005 alone)

### Step 4: Cross-Reference Remediation

For each finding, consult the **Hardening Guide** (see references/hardening-guide.md) and provide:

1. The specific remediation action
2. A code snippet showing the before/after
3. The PRT Scan phase that the remediation blocks

### Step 5: Generate Report

Produce a structured audit report:

**Local audit report format:**
```markdown
## CI/CD Supply Chain Audit Report

**Target**: [path]
**Date**: [date]
**Total Findings**: [count] (Critical: [n], High: [n], Medium: [n], Low: [n])

### Findings

| # | Severity | Pattern | File | Line(s) | Description |
|---|----------|---------|------|---------|-------------|
| 1 | ... | PRT-XXX | ... | ... | ... |

### Remediation Priority

1. **[CRITICAL]** [Finding] → [Specific fix with code snippet]
2. **[HIGH]** [Finding] → [Specific fix with code snippet]
...

### Attack Chain Analysis

If multiple findings coexist, describe the combined attack chain:
- Which PRT Scan phases are enabled?
- What is the maximum blast radius?
- What is the recommended hardening sequence?
```

**Live audit report format:**
```markdown
## CI/CD Supply Chain Audit Report

**Target**: [owner/repo] (remote)
**Visibility**: [public/private/internal]
**Default Branch**: [branch]
**Date**: [date]
**Total Findings**: [count] (Critical: [n], High: [n], Medium: [n], Low: [n])

### Findings

| # | Severity | Pattern | Resource | Description |
|---|----------|---------|----------|-------------|
| 1 | ... | PRT-XXX | [workflow URL or path] | ... |

### Remediation Priority

1. **[CRITICAL]** [Finding] → [Specific fix with code snippet]
2. **[HIGH]** [Finding] → [Specific fix with code snippet]
...

### Attack Chain Analysis

If multiple findings coexist, describe the combined attack chain:
- Which PRT Scan phases are enabled?
- What is the maximum blast radius?
- What is the recommended hardening sequence?

### Repository Configuration

| Setting | Value | Risk |
|---------|-------|------|
| Actions enabled | [yes/no] | ... |
| Allowed actions | [all/local/selected] | ... |
| Default token permissions | [read/write] | ... |
| Branch protection | [yes/no] | ... |
| First-time contributor limits | [yes/no] | ... |
| Secrets count | [n] | ... |
```

## Important Notes

- Always read the full workflow file — don't assume patterns based on trigger type alone
- For live audits, ensure `gh` CLI is installed and authenticated (`gh auth status`)
- Check for `concurrency` groups that might mask race conditions
- Look for `environment` protections that mitigate some findings
- Note when `GITHUB_TOKEN` permissions are explicitly restricted (this is a positive finding)
- Report both vulnerabilities AND positive security controls found
- For large repos, use `--paginate` when fetching workflow lists and run histories
- Live audit findings use resource URLs (e.g., `https://github.com/owner/repo/blob/main/.github/workflows/ci.yml`) instead of local file paths
