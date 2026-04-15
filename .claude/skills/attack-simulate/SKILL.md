---
name: attack-simulate
description: "Red team skill for simulating PRT Scan / TeamPCP CI/CD supply chain attacks on GitHub Actions workflows. Use when: generating injection payloads for security research, crafting PRT Scan 5-phase attack chains, testing workflow exploit paths, simulating credential exfiltration, creating educational exploit demonstrations."
user-invocable: true
---

# Attack Simulate Skill

Follow the full procedure in `.agents/skills/attack-simulate/SKILL.md`.

Reference files are in `.agents/skills/attack-simulate/references/`:
- `teamPCP-ttps.md` — Attack TTP catalog for the PRT Scan / TeamPCP campaign
- `gh-recon-commands.md` — GitHub CLI reconnaissance command reference for live target analysis

The payload generator script is at `.agents/skills/attack-simulate/scripts/prt-scan-payload.py`.
