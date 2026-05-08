import tempfile
import subprocess

def clone_repo(repo_url: str, pat: str | None):
    temp_dir = tempfile.mkdtemp()

    if pat:
        repo_url = repo_url.replace("https://", f"https://{pat}@")

    subprocess.run(
        ["git", "clone", repo_url, temp_dir],
        check=True
    )

    return temp_dir