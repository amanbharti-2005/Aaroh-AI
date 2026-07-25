"""
app/core/rag/github_fetch.py

Minimal utility: takes a GitHub repo URL, downloads it as a ZIP, and
extracts it to a local temp folder. This is the SMALLEST possible
version of "Repository Intelligence" — just enough to hand a real
folder to ingest_repository() for testing.

This is NOT the full Repository Analysis Agent (folder structure
summaries, git status, AST parsing, framework detection, README
parsing) — that's a bigger, separate piece, and per your team's
proposal it's Member 3's scope, not RAG. This file only exists so
YOU can test Repository RAG against real external repos instead of
only your own code.
"""

import os
import re
import shutil
import tempfile
import zipfile

import requests


def _safe_extract(zip_ref: zipfile.ZipFile, extract_to: str) -> None:
    """
    Extracts a ZIP while blocking "zip slip" path traversal — a
    malicious archive can otherwise contain entries like
    "../../../etc/something" that resolve outside extract_to when
    naively passed to ZipFile.extractall(). Every member's resolved
    path is checked to still be inside extract_to before writing it;
    anything that isn't is rejected and the whole extraction fails
    loudly rather than silently writing outside the temp folder.
    """
    extract_to_real = os.path.realpath(extract_to)

    for member in zip_ref.infolist():
        member_path = os.path.realpath(os.path.join(extract_to, member.filename))
        if not (member_path == extract_to_real or member_path.startswith(extract_to_real + os.sep)):
            raise ValueError(f"Unsafe path in ZIP archive, refusing to extract: {member.filename}")

    zip_ref.extractall(extract_to)


def parse_owner_repo(repo_url: str) -> str:
    """
    Normalizes any of the forms people actually paste into "owner/repo":

        https://github.com/owner/repo
        https://github.com/owner/repo.git      <- the common copy-from-GitHub form
        https://www.github.com/owner/repo/
        http://github.com/owner/repo
        git@github.com:owner/repo.git
        github.com/owner/repo
        https://github.com/owner/repo/tree/some-branch
        owner/repo

    The previous implementation only stripped the literal
    "https://github.com/" prefix, so a URL ending in ".git" — exactly what
    GitHub's own "Code -> HTTPS" button gives you — produced
    "owner/repo.git" and every codeload request 404'd, surfacing as
    "Check the URL is correct and the repo is public" for a repo that was
    perfectly public.
    """
    url = repo_url.strip()

    # SSH form: git@github.com:owner/repo.git
    if url.startswith("git@"):
        url = url.split(":", 1)[-1]
    else:
        url = re.sub(r"^https?://", "", url)
        url = re.sub(r"^www\.", "", url)
        url = re.sub(r"^github\.com/", "", url)

    url = url.strip("/")

    parts = [p for p in url.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Couldn't parse owner/repo from: {repo_url}")

    owner, repo = parts[0], parts[1]
    # Drop a trailing ".git" and anything after owner/repo (e.g. /tree/main).
    repo = re.sub(r"\.git$", "", repo)

    if not owner or not repo:
        raise ValueError(f"Couldn't parse owner/repo from: {repo_url}")

    return f"{owner}/{repo}"


def _default_branch(owner_repo: str) -> str | None:
    """
    Asks the GitHub API what the repo's default branch is, so repos whose
    default is neither "main" nor "master" (e.g. "develop", "trunk") still
    work instead of failing the hardcoded two-branch guess.
    Returns None if the API call fails for any reason — the caller then
    just reports the branches it tried.
    """
    try:
        response = requests.get(
            f"https://api.github.com/repos/{owner_repo}",
            headers={"Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("default_branch")
    except requests.RequestException:
        pass
    return None


def download_github_repo(repo_url: str, branch: str = None) -> str:
    """
    repo_url: e.g. "https://github.com/owner/repo" (with or without ".git")
    branch: e.g. "main" — if None, tries "main", then "master", then the
            repo's actual default branch via the GitHub API.

    Returns the local folder path where the repo was extracted.
    Caller is responsible for cleaning it up when done (see cleanup_repo below).
    """
    owner_repo = parse_owner_repo(repo_url)

    branches_to_try = [branch] if branch else ["main", "master"]

    response = None
    for b in branches_to_try:
        zip_url = f"https://codeload.github.com/{owner_repo}/zip/refs/heads/{b}"
        response = requests.get(zip_url, timeout=30)
        if response.status_code == 200:
            break
    else:
        # Neither guess hit — ask GitHub for the real default branch before
        # giving up, and use its answer to tell the user what actually went
        # wrong (missing/private repo vs. an unusual branch name).
        resolved = None if branch else _default_branch(owner_repo)
        if resolved and resolved not in branches_to_try:
            zip_url = f"https://codeload.github.com/{owner_repo}/zip/refs/heads/{resolved}"
            response = requests.get(zip_url, timeout=30)

        if response is None or response.status_code != 200:
            if _default_branch(owner_repo) is None:
                raise RuntimeError(
                    f"Couldn't find the repository '{owner_repo}' on GitHub. "
                    "Check the URL is spelled correctly and the repo is public "
                    "— private repos aren't supported yet."
                )
            raise RuntimeError(
                f"Found '{owner_repo}' but couldn't download any of its "
                f"branches (tried {branches_to_try}"
                + (f" and '{resolved}'" if resolved else "")
                + "). The repository may be empty."
            )

    temp_dir = tempfile.mkdtemp(prefix="aaroh_repo_")
    zip_path = os.path.join(temp_dir, "repo.zip")
    with open(zip_path, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_path, "r") as z:
        _safe_extract(z, temp_dir)
    os.remove(zip_path)

    # GitHub zips extract into a single subfolder like "repo-main" — find it
    extracted = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
    if not extracted:
        raise RuntimeError("Extraction produced no folder — zip may be malformed.")

    return os.path.join(temp_dir, extracted[0])


def cleanup_repo(local_path: str):
    """Delete the temp folder once you're done ingesting it."""
    parent_temp_dir = os.path.dirname(local_path)
    if os.path.exists(parent_temp_dir):
        shutil.rmtree(parent_temp_dir, ignore_errors=True)


def extract_uploaded_zip(zip_file_path: str) -> str:
    """
    zip_file_path: path to a .zip file already saved on disk (e.g. from
    a FastAPI UploadFile that your router saved to a temp location).

    Returns the local folder path where it was extracted — same shape
    as download_github_repo(), so both feed ingest_repository() identically.
    """
    temp_dir = tempfile.mkdtemp(prefix="aaroh_zip_")

    with zipfile.ZipFile(zip_file_path, "r") as z:
        _safe_extract(z, temp_dir)

    # If the zip contains one single top-level folder, use that as the
    # root (matches GitHub's zip export behavior). Otherwise use temp_dir
    # itself as the root.
    entries = [e for e in os.listdir(temp_dir) if not e.startswith("__MACOSX")]
    dirs_only = [e for e in entries if os.path.isdir(os.path.join(temp_dir, e))]

    if len(dirs_only) == 1 and len(entries) == 1:
        return os.path.join(temp_dir, dirs_only[0])
    return temp_dir