---
name: workflow-audit
description: "Blue team skill for detecting CI/CD supply chain vulnerabilities in GitHub Actions workflows. Use when: scanning workflows for PRT Scan patterns, auditing pull_request_target usage, checking credential persistence, finding script injection vectors, reviewing permissions blocks, generating security findings reports."
user-invocable: true
---

# Workflow Audit Skill

Follow the full procedure in `.agents/skills/workflow-audit/SKILL.md`.

Reference files are in `.agents/skills/workflow-audit/references/`:
- `prt-scan-patterns.md` — Vulnerability pattern catalog (PRT-001 through PRT-010)
- `hardening-guide.md` — Remediation reference with before/after code snippets
- `gh-audit-commands.md` — GitHub CLI audit command reference for live audits
