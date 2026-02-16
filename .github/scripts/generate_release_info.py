import json
import os
import sys
from datetime import datetime

JSON_FILE = ".github/upstream-version.json"
NOTES_FILE = "release_notes.md"

def main():
    if not os.path.exists(JSON_FILE):
        print(f"Error: {JSON_FILE} not found", file=sys.stderr)
        sys.exit(1)

    with open(JSON_FILE, "r") as f:
        data = json.load(f)

    # Helper to get info safely
    def get_info(name):
        return data.get(name, {})

    opus_tools = get_info("opus-tools")
    opus = get_info("opus")

    if not opus_tools or not opus:
        print("Error: Missing opus-tools or opus info in json", file=sys.stderr)
        sys.exit(1)

    # 1. Tag Name: yyyy-MM-dd_hh-mm_opus-toolsShortHash
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d_%H-%M")
    tools_hash_short = opus_tools.get("commit_hash", "")[:7]
    tag_name = f"{date_str}_{tools_hash_short}"

    # 2. Zip Name: opus-tools-opus-toolsShortHash_opus-opusShortHash.zip
    opus_hash_short = opus.get("commit_hash", "")[:7]
    zip_name = f"opus-tools-{tools_hash_short}_opus-{opus_hash_short}.zip"

    # 3. Release Notes Table
    # Columns: Repository Name/URL, Commit Hash (7)/Link, Commit Time
    table_header = "| Repository | Commit | Time |\n| --- | --- | --- |"
    table_rows = []

    # Order of repos to display
    repos = ["opus-tools", "opus", "opusfile", "libopusenc", "ogg", "flac"]
    
    for name in repos:
        info = get_info(name)
        if not info:
            continue
            
        repo_name = info.get("name", name)
        repo_url = info.get("url", "")
        # Remove .git for display or linking if desired, but user said "Repository Name/Address"
        # Let's make the name a link to the repo
        if repo_url:
            repo_col = f"[{repo_name}]({repo_url.rstrip('.git')})"
        else:
            repo_col = repo_name

        commit_hash = info.get("commit_hash", "")
        short_hash = commit_hash[:7]
        commit_url = info.get("commit_url", "")
        
        if commit_url:
            commit_col = f"[{short_hash}]({commit_url})"
        else:
            commit_col = short_hash

        commit_time = info.get("commit_time", "")

        table_rows.append(f"| {repo_col} | {commit_col} | {commit_time} |")

    notes_content = f"{table_header}\n" + "\n".join(table_rows)

    with open(NOTES_FILE, "w") as f:
        f.write(notes_content)

    # Output variables for GitHub Actions
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"tag_name={tag_name}\n")
            f.write(f"zip_name={zip_name}\n")
    
    print(f"Generated release info:")
    print(f"Tag: {tag_name}")
    print(f"Zip: {zip_name}")

if __name__ == "__main__":
    main()
