import tempfile
import subprocess

def clone_repo(repo_url: str, pat: str | None):
    temp_dir = tempfile.mkdtemp()

    clone_url = repo_url

    # ------------------------------------------------
    # Azure DevOps private repo
    # ------------------------------------------------
    if "dev.azure.com" in repo_url and pat:

        clone_url = repo_url.replace(
            "https://",
            f"https://{pat}@"
        )

    # ------------------------------------------------
    # Public GitHub / public git repo
    # ------------------------------------------------
    else:
        clone_url = repo_url

    subprocess.run(
        ["git", "clone", clone_url, temp_dir],
        check=True
    )

    return temp_dir