import json
import os
import subprocess
import sys
import shutil
import tempfile
from datetime import datetime

# Configuration
REPOS = {
    "ogg": "https://gitlab.xiph.org/xiph/ogg.git",
    "flac": "https://gitlab.xiph.org/xiph/flac.git",
    "opus": "https://gitlab.xiph.org/xiph/opus.git",
    "libopusenc": "https://gitlab.xiph.org/xiph/libopusenc.git",
    "opusfile": "https://gitlab.xiph.org/xiph/opusfile.git",
    "opus-tools": "https://gitlab.xiph.org/xiph/opus-tools.git"
}

JSON_FILE = ".github/upstream-version.json"

def run_command(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(cmd)}: {e.stderr}", file=sys.stderr)
        raise

def get_remote_info(name, url):
    print(f"Checking {name}...", file=sys.stderr)
    # Get hash
    output = run_command(["git", "ls-remote", url, "HEAD"])
    if not output:
        raise Exception(f"Could not get ls-remote for {url}")
    
    commit_hash = output.split()[0]
    return commit_hash

def get_commit_details(url, commit_hash):
    temp_dir = tempfile.mkdtemp()
    try:
        # Clone bare, depth 1
        print(f"Fetching details for {url}...", file=sys.stderr)
        run_command(["git", "clone", "--bare", "--depth", "1", "--filter=blob:none", url, temp_dir])
        
        # Get date
        commit_time = run_command(["git", "-C", temp_dir, "show", "-s", "--format=%ci", commit_hash])
        
        return commit_time
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def get_commit_url(repo_url, commit_hash):
    base_url = repo_url.rstrip("/")
    if base_url.endswith(".git"):
        base_url = base_url[:-4]
        
    if "gitlab" in base_url:
        return f"{base_url}/-/commit/{commit_hash}"
    elif "bitbucket" in base_url:
        return f"{base_url}/commits/{commit_hash}"
    else:
        # Default to GitHub-style /commit/ which works for GitHub, Gitee, etc.
        return f"{base_url}/commit/{commit_hash}"

def main():
    # Load existing
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}

    updates_found = False
    new_data = {}

    for name, url in REPOS.items():
        current_info = data.get(name, {})
        cached_hash = current_info.get("commit_hash")
        
        try:
            remote_hash = get_remote_info(name, url)
        except Exception as e:
            print(f"Failed to check {name}: {e}", file=sys.stderr)
            new_data[name] = current_info
            continue

        if remote_hash != cached_hash:
            print(f"Update found for {name}: {cached_hash} -> {remote_hash}", file=sys.stderr)
            updates_found = True
            
            # Fetch details
            try:
                commit_time = get_commit_details(url, remote_hash)
            except Exception as e:
                print(f"Failed to get details for {name}: {e}", file=sys.stderr)
                commit_time = datetime.now().isoformat()

            new_data[name] = {
                "name": name,
                "url": url,
                "commit_hash": remote_hash,
                "commit_url": get_commit_url(url, remote_hash),
                "commit_time": commit_time
            }
        else:
            # Update commit_url even if hash is the same, to support logic changes
            if "commit_hash" in current_info:
                current_info["commit_url"] = get_commit_url(url, current_info["commit_hash"])
            new_data[name] = current_info

    # Save to file
    with open(JSON_FILE, "w") as f:
        json.dump(new_data, f, indent=2)
        
    if updates_found:
        print("Updates detected.")
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("upstream_updated=true\n")
    else:
        print("No updates detected.")
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("upstream_updated=false\n")

    # Always output current hashes
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            for name, info in new_data.items():
                key = f"{name.replace('-', '_')}_hash"
                value = info.get("commit_hash", "")
                if value:
                    f.write(f"{key}={value}\n")

if __name__ == "__main__":
    main()
