#!/usr/bin/env python3
"""
Mukul975 Cybersecurity Skill Fetcher Script
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.error

# GitHub API base for the repository
GITHUB_API_BASE = "https://api.github.com/repos/mukul975/Anthropic-Cybersecurity-Skills"
RAW_BASE = "https://raw.githubusercontent.com/mukul975/Anthropic-Cybersecurity-Skills/main"

def get_github_api(url: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Make a GET request to GitHub API."""
    req = urllib.request.Request(url)
    if token:
        req.add_header('Authorization', f'token {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error fetching {url}: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error connecting to {url}: {e.reason}", file=sys.stderr)
        sys.exit(1)

def get_raw_file(path: str) -> str:
    """Get raw file content from GitHub."""
    url = f"{RAW_BASE}/{path}"
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except urllib.error.URLError as e:
        print(f"Error fetching raw file {path}: {e.reason}", file=sys.stderr)
        return ""

def list_skills(token: Optional[str] = None) -> List[Dict[str, str]]:
    """List all available skills from the repository."""
    # Try to get the index.json file which contains the skill index
    index_data = get_github_api(f"{GITHUB_API_BASE}/contents/index.json", token)
    
    # If index.json exists, download and parse it
    if 'download_url' in index_data:
        try:
            with urllib.request.urlopen(index_data['download_url']) as response:
                index_content = json.loads(response.read().decode())
                if isinstance(index_content, dict) and 'skills' in index_content:
                    skills_data = index_content['skills']
                    # Convert to expected format
                    skills = []
                    for skill in skills_data:
                        if isinstance(skill, dict):
                            skills.append({
                                'name': skill.get('name', ''),
                                'description': skill.get('description', ''),
                                'domain': skill.get('domain', 'cybersecurity'),
                                'path': f"skills/{skill.get('name', '')}"
                            })
                    return skills
        except Exception as e:
            print(f"Error parsing index.json: {e}", file=sys.stderr)
            pass
    
    # Fallback: scan the skills directory
    skills_data = get_github_api(f"{GITHUB_API_BASE}/contents/skills", token)
    skills = []
    
    if isinstance(skills_data, list):
        for item in skills_data:
            if item['type'] == 'dir':
                skill_name = item['name']
                # Get the SKILL.md to extract metadata
                skill_path = f"skills/{skill_name}/SKILL.md"
                skill_content = get_raw_file(skill_path)
                
                # Extract basic metadata from SKILL.md frontmatter
                name = skill_name
                description = ""
                domain = ""
                
                if skill_content:
                    if skill_content:
                                        lines = skill_content.split('\n')
                                        in_frontmatter = False
                                        for line in lines:
                                            if line.strip() == '---':
                                                if not in_frontmatter:
                                                    in_frontmatter = True
                                                else:
                                                    break
                                            elif in_frontmatter:
                                                if line.startswith('name:'):
                                                    name = line.split(':', 1)[1].strip().strip('"\'')
                                                elif line.startswith('description:'):
                                                    description = line.split(':', 1)[1].strip().strip('"\'')
                                                elif line.startswith('domain:'):
                                                    domain = line.split(':', 1)[1].strip().strip('\'"')
                
                skills.append({
                    'name': skill_name,
                    'description': description,
                    'domain': domain,
                    'path': f"skills/{skill_name}"
                })
    
    return skills

def fetch_skill(skill_name: str, output_dir: Path, token: Optional[str] = None) -> bool:
    """Fetch a specific skill by name."""
    skill_path = f"skills/{skill_name}"
    
    # Get the skill directory contents
    skill_contents = get_github_api(f"{GITHUB_API_BASE}/contents/{skill_path}", token)
    
    if not isinstance(skill_contents, list):
        print(f"Error: Skill '{skill_name}' not found or inaccessible.", file=sys.stderr)
        return False
    
    # Create skill directory
    skill_dir = output_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch each file in the skill directory
    for item in skill_contents:
        if item['type'] == 'file':
            file_path = item['path']
            relative_path = Path(file_path).relative_to(skill_path)
            dest_path = skill_dir / relative_path
            
            # Create parent directories if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the file
            content = get_raw_file(file_path)
            if content:
                dest_path.write_text(content, encoding='utf-8')
                print(f"Fetched: {relative_path}")
            else:
                print(f"Warning: Failed to fetch {relative_path}", file=sys.stderr)
        elif item['type'] == 'dir':
            # Recursively fetch directory contents
            dir_path = item['path']
            relative_dir = Path(dir_path).relative_to(skill_path)
            dest_dir = skill_dir / relative_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Get contents of subdirectory
            sub_contents = get_github_api(f"{GITHUB_API_BASE}/contents/{dir_path}", token)
            if isinstance(sub_contents, list):
                for sub_item in sub_contents:
                    if sub_item['type'] == 'file':
                        file_path = sub_item['path']
                        relative_path = Path(file_path).relative_to(skill_path)
                        dest_path = skill_dir / relative_path
                        
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        content = get_raw_file(file_path)
                        if content:
                            dest_path.write_text(content, encoding='utf-8')
                            print(f"Fetched: {relative_path}")
                        else:
                            print(f"Warning: Failed to fetch {relative_path}", file=sys.stderr)
    
    # Check if we got the SKILL.md
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: SKILL.md not found for skill '{skill_name}'", file=sys.stderr)
        return False
        
    return True

def execute_skill(skill_name: str, args: List[str], skill_dir: Path) -> int:
    """Execute the skill's agent.py if it exists."""
    agent_py = skill_dir / "scripts" / "agent.py"
    
    if not agent_py.exists():
        print(f"No agent.py found for skill '{skill_name}'.", file=sys.stderr)
        print("Please refer to the SKILL.md for manual execution instructions.")
        return 1
    
    # Check if it's a Python script
    if not os.access(agent_py, os.X_OK):
        # Make it executable if it's a Python script
        if agent_py.suffix == '.py':
            import stat
            st = os.stat(agent_py)
            os.chmod(agent_py, st.st_mode | stat.S_IEXEC)
    
    # Prepare command
    cmd = [sys.executable, str(agent_py)] + args
    
    # Set up environment - add any necessary paths
    env = os.environ.copy()
    # Add the skill directory to PYTHONPATH for imports
    env['PYTHONPATH'] = f"{skill_dir}:{skill_dir / 'scripts'}:{env.get('PYTHONPATH', '')}"
    
    try:
        # Execute the script
        import subprocess
        result = subprocess.run(cmd, env=env, cwd=skill_dir)
        return result.returncode
    except Exception as e:
        print(f"Error executing {agent_py}: {e}", file=sys.stderr)
        return 1

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch and execute cybersecurity skills from mukul975/Anthropic-Cybersecurity-Skills")
    parser.add_argument('--action', required=True, choices=['list_skills', 'fetch_skill', 'execute_skill', 'cleanup'], help='Action to perform')
    parser.add_argument('--skill-name', help='Name of the skill to fetch/execute')
    parser.add_argument('--args', nargs='*', default=[], help='Arguments to pass to the skill\'s agent.py')
    parser.add_argument('--github-token', help='GitHub personal access token (for higher rate limits)')
    parser.add_argument('--temp-dir', help='Directory to store fetched skills (default: temporary directory)')
    
    args = parser.parse_args()
    
    # Set up temporary directory
    if args.temp_dir:
        base_dir = Path(args.temp_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
    else:
        base_dir = Path(tempfile.mkdtemp(prefix='mukul975_skill_'))
    
    try:
        if args.action == 'list_skills':
            skills = list_skills(args.github_token)
            print(f"Found {len(skills)} skills:")
            for skill in skills:
                print(f"  - {skill['name']}: {skill['description']}")
                if skill['domain']:
                    print(f"    Domain: {skill['domain']}")
        
        elif args.action == 'fetch_skill':
            if not args.skill_name:
                print("Error: --skill-name required for fetch_skill action", file=sys.stderr)
                sys.exit(1)
            
            success = fetch_skill(args.skill_name, base_dir, args.github_token)
            if success:
                print(f"Successfully fetched skill '{args.skill_name}' to {base_dir / args.skill_name}")
            else:
                sys.exit(1)
        
        elif args.action == 'execute_skill':
            if not args.skill_name:
                print("Error: --skill-name required for execute_skill action", file=sys.stderr)
                sys.exit(1)
            
            skill_dir = base_dir / args.skill_name
            if not skill_dir.exists():
                print(f"Skill '{args.skill_name}' not found locally. Fetching first...")
                if not fetch_skill(args.skill_name, base_dir, args.github_token):
                    sys.exit(1)
            
            exit_code = execute_skill(args.skill_name, args.args, skill_dir)
            sys.exit(exit_code)
        
        elif args.action == 'cleanup':
            if base_dir.exists():
                shutil.rmtree(base_dir)
                print(f"Cleaned up {base_dir}")
            else:
                print("Nothing to clean up.")
    
    finally:
        # Clean up temp directory if we created it
        if not args.temp_dir and base_dir.exists():
            shutil.rmtree(base_dir)

if __name__ == '__main__':
    main()