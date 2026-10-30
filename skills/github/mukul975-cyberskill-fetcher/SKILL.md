---
name: mukul975-cyberskill-fetcher
description: Fetches and executes a cybersecurity skill from the mukul975/Anthropic-Cybersecurity-Skills repository.
domain: cybersecurity
subdomain: skill-util
tags: [cybersecurity, skill-management, github, mukul975]
author: mukul975
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cybersecurity, skill-management, github, mukul975]
    homepage: https://github.com/mukul975/Anthropic-Cybersecurity-Skills
    related_skills: [github-repo-management, github-code-review]
---

# Mukul975 Cybersecurity Skill Fetcher

This skill enables Hermes to fetch and execute cybersecurity skills from the mukul975/Anthropic-Cybersecurity-Skills GitHub repository, which contains 817+ structured cybersecurity skills.

## When to Use This Skill

- When you need to execute a specific cybersecurity skill from mukul975's collection
- To browse available cybersecurity skills in the repository
- For automated execution of security-related tasks (malware analysis, CVE research, etc.)
- When integrating mukul975's skill library into Hermes workflows

## Prerequisites

- Internet access to fetch from GitHub
- Python 3.6+ (for the fetcher script)
- GitHub token recommended for higher rate limits (optional)

## Usage

### List Available Skills
```bash
hermes agent skill mukul975-cyberskill-fetcher --action list_skills
```

### Fetch a Specific Skill
```bash
hermes agent skill mukul975-cyberskill-fetcher --action fetch_skill --skill-name <skill-name>
```

### Execute a Skill
```bash
hermes agent skill mukul975-cyberskill-fetcher --action execute_skill --skill-name <skill-name> --args <arg1> <arg2> ...
```

### Clean Up Temporary Files
```bash
hermes agent skill mukul975-cyberskill-fetcher --action cleanup
```

## How It Works

1. **Listing**: Queries the GitHub API to retrieve skill metadata from the repository
2. **Fetching**: Downloads the complete skill directory (including SKILL.md, scripts, templates, etc.)
3. **Execution**: Runs the skill's `scripts/agent.py` if available, passing any provided arguments
4. **Cleanup**: Removes temporary files (unless `--temp-dir` is specified to persist them)

## Examples

### List first 5 skills
```bash
hermes agent skill mukul975-cyberskill-fetcher --action list_skills | head -20
```

### Fetch and execute a malware analysis skill
```bash
hermes agent skill mukul975-cyberskill-fetcher --action execute_skill --skill-name analyzing-malware-behavior --args --file sample.exe
```

### Fetch a CVE research skill
```bash
hermes agent skill mukul975-cyberskill-fetcher --action fetch_skill --skill-name cve-lookup-and-analysis
```

## Skill Structure

Each fetched skill typically contains:
- `SKILL.md`: Skill documentation with metadata
- `scripts/agent.py`: Executable script (if applicable)
- `templates/`: Jinja2 templates for reports, etc.
- `references/`: Reference materials
- `assets/`: Binary assets, signatures, etc.

## Notes

- Skills are fetched to a temporary directory by default (auto-cleaned)
- Use `--temp-dir /path/to/keep` to persist fetched skills
- GitHub API rate limiting applies; use `--github-token` for higher limits
- Some skills may require additional dependencies (check SKILL.md)

## Related Skills

- `github-repo-management`: For broader GitHub repository operations
- `github-code-review`: For analyzing fetched security skills
- `analyzing-malware-behavior`: Example skill from mukul975's collection (when fetched)

---
*Skill created from mukul975/Anthropic-Cybersecurity-Skills repository containing 817+ cybersecurity skills*