# prt-actions-pwn

This project provides a CI/CD supply chain security agent with two skills. Follow the instructions in [AGENTS.md](AGENTS.md) for the full agent specification, including operating modes, constraints, and response format.

## Skills

- **workflow-audit** — Blue team skill for detecting PRT Scan vulnerability patterns in GitHub Actions workflows. See `.agents/skills/workflow-audit/SKILL.md` for the full procedure and `.agents/skills/workflow-audit/references/` for the pattern catalog, hardening guide, and CLI command reference.
- **attack-simulate** — Red team skill for simulating PRT Scan / TeamPCP attack chains against GitHub Actions workflows. See `.agents/skills/attack-simulate/SKILL.md` for the full procedure and `.agents/skills/attack-simulate/references/` for TTP catalog and CLI recon commands.

## Sample Vulnerable Workflows

Deliberately vulnerable workflows for practice are hosted in a separate repo: [`dextersec-playground/pwn-ci-prt-lab`](https://github.com/dextersec-playground/pwn-ci-prt-lab). Use it as a live audit/simulate target:
- `vulnerable-prt-target.yml` — Classic PRT Scan target
- `vulnerable-persist-creds.yml` — Credential persistence demo
- `vulnerable-script-injection.yml` — Script injection demo
- `hardened-reference.yml` — Secure reference workflow
