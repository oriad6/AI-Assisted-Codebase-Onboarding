import requests
from pathlib import Path


def fetch_github_repo(repo_url: str) -> tuple[list | None, str | None]:
    """
    Fetch code files from a public GitHub repository.
    Returns (files_data, error_message). Exactly mirrors the original app.py logic.
    """
    try:
        clean_url = repo_url.rstrip("/")
        if not clean_url.startswith("https://github.com/"):
            return None, "Invalid GitHub URL."
        parts = clean_url.split("/")
        if len(parts) < 5:
            return None, "Invalid URL format."
        owner, repo = parts[3], parts[4]

        branches = ["main", "master"]
        tree_data = None
        used_branch = None
        for branch in branches:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            resp = requests.get(api_url)
            if resp.status_code == 200:
                tree_data = resp.json().get("tree", [])
                used_branch = branch
                break

        if not tree_data:
            return None, "Repo not found or branch issue."

        allowed_ext = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".cpp", ".c",
            ".h", ".rs", ".php", ".rb", ".css", ".html", ".json", ".sql",
            ".yaml", ".yml", ".md",
        }

        files_data = []
        count = 0
        for item in tree_data:
            if item["type"] == "blob" and Path(item["path"]).suffix in allowed_ext:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{used_branch}/{item['path']}"
                r = requests.get(raw_url)
                if r.status_code == 200:
                    files_data.append({
                        "name": item["path"],
                        "content": r.text,
                        "size": len(r.content),
                    })
                    count += 1
                    if count >= 60:
                        break

        if not files_data:
            return None, "No code files found."
        return files_data, None
    except Exception as e:
        return None, str(e)
