# prt-actions-pwn

A security research toolkit for detecting and simulating PRT Scan / TeamPCP attack patterns in GitHub Actions workflows.

> ⚠️ **WARNING**: This project is for **security research and education only**. The attack simulation tools generate deliberately insecure payloads. **Never deploy them in production.** Vulnerable sample workflows are hosted separately in [`dextersec-playground/pwn-ci-prt-lab`](https://github.com/dextersec-playground/pwn-ci-prt-lab).

## Overview

This toolkit provides a `prt-actions-pwn` agent with two bundled skills for auditing and simulating CI/CD supply chain attacks. It works with **Codex CLI**, **Claude Code**, and **VS Code Copilot**:

| Component | Type | Purpose |
|-----------|------|---------|
| `prt-actions-pwn` agent | Custom Agent | Entry point — routes to audit or simulate mode |
| `workflow-audit` skill | Blue Team | Detect PRT Scan vulnerability patterns in workflows |
| `attack-simulate` skill | Red Team | Generate PRT Scan / TeamPCP attack payloads for testing |

### PRT Scan Attack Chain

PRT Scan is a 5-phase automated attack targeting GitHub Actions:

1. **EXFIL** — Steal `GITHUB_TOKEN` via `actions/checkout` credential persistence
2. **RECON** — Enumerate secrets and workflows via GitHub API
3. **DISPATCH** — Push temporary workflows to capture secret values
4. **LABEL_BYPASS** — Auto-apply labels to bypass approval gates
5. **DELAYED** — Background `/proc` scanner, exfiltrate via PR comments

### Vulnerability Patterns

| ID | Pattern | Severity | PRT Phase |
|----|---------|----------|-----------|
| PRT-001 | `pull_request_target` + checkout PR head | CRITICAL | EXFIL |
| PRT-002 | Credential persistence via `persist-credentials: true` | HIGH/CRITICAL | EXFIL |
| PRT-003 | Script injection via untrusted PR data | CRITICAL | EXFIL, RECON |
| PRT-004 | Missing or overly broad `permissions:` | HIGH | DISPATCH, LABEL_BYPASS |
| PRT-005 | Unpinned action versions (tags, not SHAs) | MEDIUM | Supply chain |
| PRT-006 | First-time contributor approval bypass | MEDIUM | Entry vector |
| PRT-007 | Path-based trigger abuse | MEDIUM | Entry vector |
| PRT-008 | Untrusted `workflow_dispatch` inputs | MEDIUM | DISPATCH |
| PRT-009 | Secrets in untrusted code context | HIGH | EXFIL |
| PRT-010 | Forked action references | LOW | Supply chain |

## Quick Start

### Prerequisites

- GitHub CLI (`gh`) installed and authenticated — for live auditing remote repositories (`gh auth status`)
- **One** of the following agent harnesses:
  - **Codex CLI** — picks up `AGENTS.md` automatically
  - **Claude Code** — picks up `CLAUDE.md` and discovers skills in `.claude/skills/`
  - **VS Code Copilot** — loads `.github/agents/prt-actions-pwn.agent.md`

### Usage

#### Codex CLI

```
# Codex reads AGENTS.md automatically — just ask:
> audit dextersec-playground/pwn-ci-prt-lab
> simulate dextersec-playground/pwn-ci-prt-lab
```

#### Claude Code

```
# Claude reads CLAUDE.md and discovers skills in .claude/skills/ — just ask:
> run workflow-audit on dextersec-playground/pwn-ci-prt-lab
> simulate an attack on dextersec-playground/pwn-ci-prt-lab
```

#### VS Code Copilot

```
@prt-actions-pwn audit dextersec-playground/pwn-ci-prt-lab
@prt-actions-pwn simulate dextersec-playground/pwn-ci-prt-lab
```

The agent works with any `owner/repo` target or local workflow path. The lab repo [`dextersec-playground/pwn-ci-prt-lab`](https://github.com/dextersec-playground/pwn-ci-prt-lab) provides deliberately vulnerable workflows for practice.

### Skill Modes

#### Audit Mode (Blue Team)

```
> audit owner/repo
```

Runs a 5-step detection procedure:
1. **Discovery** — Parse workflow YAML structure (local) or fetch via `gh api` (remote)
2. **Pattern Matching** — Check for PRT-001 through PRT-010
3. **Severity Assessment** — Rate each finding
4. **Cross-Reference Remediation** — Map to hardening guide
5. **Generate Report** — Structured findings with code snippets

#### Simulate Mode (Red Team)

```
> simulate owner/repo
```

Runs a 5-step exploitation procedure:
1. **Target Analysis** — Identify attack surface (local or remote)
2. **Vulnerability Mapping** — Map to PRT patterns
3. **Injection Vector Selection** — Choose exploitation path
4. **Payload Generation** — Create nonce-marked payloads
5. **Detection Guidance** — Generate detection rules

## Sample Workflows

Deliberately vulnerable workflows for practice are hosted in [`dextersec-playground/pwn-ci-prt-lab`](https://github.com/dextersec-playground/pwn-ci-prt-lab):

| File | Focus | Vulnerabilities |
|------|-------|----------------|
| `vulnerable-prt-target.yml` | Classic PRT Scan target | PRT-001 through PRT-009 |
| `vulnerable-persist-creds.yml` | Credential persistence | PRT-002, PRT-003, PRT-004, PRT-005, PRT-009 |
| `vulnerable-script-injection.yml` | Script injection | PRT-001, PRT-003, PRT-004, PRT-005, PRT-008 |
| `hardened-reference.yml` | Secure counterpart | All mitigations applied |

## Project Structure

```
prt-actions-pwn/
├── AGENTS.md                              # Codex CLI entry point
├── CLAUDE.md                              # Claude Code entry point
├── README.md
├── .agents/
│   └── skills/                            # Canonical skill content (single source of truth)
│       ├── workflow-audit/
│       │   ├── SKILL.md                   # Blue team detection skill
│       │   └── references/
│       │       ├── prt-scan-patterns.md   # Vulnerability pattern catalog
│       │       ├── hardening-guide.md     # Remediation reference
│       │       └── gh-audit-commands.md   # GitHub CLI audit command reference
│       └── attack-simulate/
│           ├── SKILL.md                   # Red team simulation skill
│           ├── scripts/
│           │   └── prt-scan-payload.py    # Payload generator
│           └── references/
│               ├── teamPCP-ttps.md        # Attack TTP reference
│               └── gh-recon-commands.md   # GitHub CLI recon command reference
├── .claude/
│   └── skills/                            # Claude Code skill stubs (point to .agents/skills/)
│       ├── workflow-audit/
│       │   └── SKILL.md
│       └── attack-simulate/
│           └── SKILL.md
├── .github/
│   └── agents/
│       └── prt-actions-pwn.agent.md       # VS Code Copilot agent entry point
```

## Payload Generator

The `prt-scan-payload.py` script generates educational payloads for testing:

```bash
python .agents/skills/attack-simulate/scripts/prt-scan-payload.py \
  --target-lang python \
  --phases exfil,recon \
  --nonce "research-$(date +%s)" \
  --output ./payloads/prt-research.yml
```

Options:
- `--target-lang` — python, node, rust, go, composite
- `--phases` — Comma-separated: exfil, recon, dispatch, label_bypass, delayed (or `all`)
- `--nonce` — Unique marker for tracking research payloads (default: RESEARCH-001)
- `--output` — Output file path (default: stdout)
- `--list-phases` — List available phases and exit
- `--list-langs` — List available target languages and exit

## Hardening Quick Reference

| Pattern | Vulnerable | Hardened |
|---------|-----------|----------|
| Trigger | `pull_request_target` | `pull_request` |
| Credentials | `persist-credentials: true` (default) | `persist-credentials: false` |
| Script injection | `${{ github.event.pull_request.title }}` in `run:` | Use env vars: `PR_TITLE: ${{ github.event.pull_request.title }}` |
| Permissions | No `permissions:` block | Explicit minimal `permissions: contents: read` |
| Action pins | `actions/checkout@v4` | `actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11` |
| Contributor check | None | Verify `author_association` before running |
| Dispatch inputs | Direct `${{ }}` interpolation | Validate against allowlist, use env vars |

## Disclaimer

This project is intended **solely for authorized security research and education**. The vulnerable workflows, attack patterns, and payload generator are designed to help security professionals understand and defend against CI/CD supply chain attacks.

**Do not**:
- Deploy vulnerable workflows in production
- Use payloads against systems you don't own or have authorization to test
- Use this toolkit for unauthorized access or data exfiltration

Always follow responsible disclosure practices and obtain proper authorization before testing.

## References

- [Wiz Research: PRT Scan Campaign](https://www.wiz.io/blog/prt-scan-campaign-targets-github-actions)
- [GitHub Security Hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-for-github-actions)
- [OWASP CI/CD Security Guide](https://owasp.org/www-community/CI-CD_Security)
