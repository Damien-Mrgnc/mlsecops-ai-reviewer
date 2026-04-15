"""Client GitHub pour lire les diffs de PR et poster des reviews."""
import os
from github import Github, GithubException


def get_github_client() -> Github:
    token = os.environ["GITHUB_TOKEN"]
    return Github(token)


def get_pr_diff(repo_name: str, pr_number: int) -> dict:
    """Retourne les fichiers modifiés et leur patch diff."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    files = {}
    for f in pr.get_files():
        if f.patch:
            files[f.filename] = {
                "patch": f.patch,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
            }
    return files


def post_review_with_decision(
    repo_name: str,
    pr_number: int,
    body: str,
    approve: bool,
) -> None:
    """Poste une review APPROVE ou REQUEST_CHANGES sur la PR."""
    g = get_github_client()
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    event = "APPROVE" if approve else "REQUEST_CHANGES"
    try:
        pr.create_review(body=body, event=event)
    except GithubException as e:
        print(f"[WARN] Review API failed ({e}), fallback to comment")
        pr.create_issue_comment(body)
