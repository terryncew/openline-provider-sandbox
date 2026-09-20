"""B's protected-effect path: advance a GitHub branch ref by exactly one
commit via the provider API.

Fail-loud discipline: every provider call must succeed and be confirmed;
any failure raises ProviderCallFailed. A failed provider call can never
return success, and effect_committed is true only when the provider
confirms the new ref equals the commit B created.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


class ProviderCallFailed(RuntimeError):
    pass


def gh_api(method: str, endpoint: str, fields: dict[str, Any] | None = None) -> Any:
    """Call the GitHub REST API. Raises ProviderCallFailed on any failure."""
    cmd = ["gh", "api", "-X", method, endpoint]
    payload = None
    if fields:
        cmd += ["--input", "-"]
        payload = json.dumps(fields)
    try:
        proc = subprocess.run(
            cmd,
            input=payload,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as exc:
        raise ProviderCallFailed(f"gh api transport failure: {exc}") from exc
    if proc.returncode != 0:
        raise ProviderCallFailed(
            f"gh api {method} {endpoint} failed rc={proc.returncode}: "
            f"{proc.stderr.strip()[:500]}"
        )
    out = proc.stdout.strip()
    if not out:
        raise ProviderCallFailed(f"gh api {method} {endpoint} empty response")
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise ProviderCallFailed(f"gh api {method} {endpoint} bad JSON") from exc


def _get(path: str) -> Any:
    return gh_api("GET", path)


def get_ref(repo: str, branch: str) -> str:
    """Return the current SHA of refs/heads/<branch>. Raises on failure."""
    data = _get(f"repos/{repo}/git/ref/heads/{branch}")
    try:
        sha = data["object"]["sha"]
    except (KeyError, TypeError) as exc:
        raise ProviderCallFailed(f"ref lookup malformed: {str(data)[:300]}") from exc
    if not isinstance(sha, str) or len(sha) != 40:
        raise ProviderCallFailed(f"ref sha malformed: {sha!r}")
    return sha


def advance_branch(
    repo: str,
    branch: str,
    file_path: str,
    file_content: str,
    commit_message: str,
    author_name: str = "interop-002-receiver",
    author_email: str = "interop-002-receiver@localhost",
) -> dict[str, str]:
    """Create exactly one commit adding file_path and fast-forward the branch.

    Returns {ref_before, ref_after, commit}. Raises ProviderCallFailed unless
    the provider confirms the ref now equals the created commit.
    """
    ref_before = get_ref(repo, branch)

    commit_obj = _get(f"repos/{repo}/git/commits/{ref_before}")
    try:
        base_tree = commit_obj["tree"]["sha"]
    except (KeyError, TypeError) as exc:
        raise ProviderCallFailed("base commit tree lookup malformed") from exc

    blob = gh_api(
        "POST",
        f"repos/{repo}/git/blobs",
        {"content": file_content, "encoding": "utf-8"},
    )
    blob_sha = blob.get("sha")
    if not blob_sha:
        raise ProviderCallFailed(f"blob creation unconfirmed: {str(blob)[:200]}")

    tree = gh_api(
        "POST",
        f"repos/{repo}/git/trees",
        {
            "base_tree": base_tree,
            "tree": [
                {
                    "path": file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha,
                }
            ],
        },
    )
    tree_sha = tree.get("sha")
    if not tree_sha:
        raise ProviderCallFailed(f"tree creation unconfirmed: {str(tree)[:200]}")

    new_commit = gh_api(
        "POST",
        f"repos/{repo}/git/commits",
        {
            "message": commit_message,
            "tree": tree_sha,
            "parents": [ref_before],
            "author": {"name": author_name, "email": author_email},
        },
    )
    commit_sha = new_commit.get("sha")
    if not commit_sha or len(commit_sha) != 40:
        raise ProviderCallFailed(f"commit creation unconfirmed: {str(new_commit)[:200]}")

    updated = gh_api(
        "PATCH",
        f"repos/{repo}/git/refs/heads/{branch}",
        {"sha": commit_sha, "force": False},
    )
    try:
        confirmed_sha = updated["object"]["sha"]
    except (KeyError, TypeError) as exc:
        raise ProviderCallFailed("ref update unconfirmed") from exc
    if confirmed_sha != commit_sha:
        raise ProviderCallFailed(
            f"ref update mismatch: provider={confirmed_sha} expected={commit_sha}"
        )

    # Independent re-observation: the ref must read back as the new commit.
    ref_after = get_ref(repo, branch)
    if ref_after != commit_sha:
        raise ProviderCallFailed(
            f"ref re-observation mismatch: {ref_after} != {commit_sha}"
        )
    return {"ref_before": ref_before, "ref_after": ref_after, "commit": commit_sha}
