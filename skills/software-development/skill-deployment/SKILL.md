---
name: skill-deployment
description: "Deploy AI skills from GitHub to all profiles."
version: 1.0.0
author: Neo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, deployment, github, hermes, team]
---

# Skill Deployment

Find, clone, and deploy AI agent skills from GitHub repos to all Hermes profiles (default, neo, max, lisa).

## When to Use

- User asks to find and install skills from GitHub
- User wants to deploy skills to the whole team
- User asks to clone a skill repo and make it available to all agents

## Procedure

### 1. Search GitHub

```bash
curl -s 'https://api.github.com/search/repositories?q=<query>&sort=stars&order=desc&per_page=10' | python3 -c "import sys,json; data=json.load(sys.stdin); [print(f\"{r['stargazers_count']:>6} | {r['full_name']} | {r['description'][:80] if r['description'] else 'N/A'}\") for r in data.get('items',[])]"
```

### 2. Clone and Inspect

```bash
cd /tmp && git clone --depth 1 https://github.com/<owner>/<repo>.git <repo-name>
find /tmp/<repo-name> -name "SKILL.md" -type f | head -10
```

### 3. Deploy to All Profiles

```bash
# Copy to default profile
cp -r /tmp/<repo-name>/skills ~/.hermes/skills/<category>

# Copy to each team profile
cp -r /tmp/<repo-name>/skills ~/.hermes/profiles/neo/skills/
cp -r /tmp/<repo-name>/skills ~/.hermes/profiles/max/skills/
cp -r /tmp/<repo-name>/skills ~/.hermes/profiles/lisa/skills/

# Clean up
rm -rf /tmp/<repo-name>
```

### 4. Verify

```bash
find ~/.hermes/skills -name "SKILL.md" -type f | wc -l
```

## Pitfalls

- **Check license before deploying.** MIT/Apache-2.0 are safe. NOASSERTION or proprietary licenses need review.
- **Check for paid APIs.** Many skill repos call paid APIs (Gemini, Higgsfield, Agnes). User requires free alternatives only.
- **Skill description must be ≤60 chars** for the system prompt budget. Long descriptions get truncated and lose routing signal.
- **Deploy to ALL profiles.** Forgetting one profile creates inconsistency. Always deploy to default, neo, max, and lisa.
- **Clean up /tmp.** Always remove cloned repos after deployment to avoid clutter.

## Notes

- Skills are markdown files that teach agents how to do things better
- No executable code, no dependencies, no security risk
- All profiles share the same skill format
- User prefers free tools only — no paid APIs