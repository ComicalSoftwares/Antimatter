import argparse
import base64
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_REPO = "https://github.com/LiteBands-Pro/Antimatter.git"
PROJECT_DIR = Path(__file__).resolve().parent
IGNORED_DIRS = {".git", "__pycache__", ".venv", "venv", "build", "dist", ".staging", ".idea", ".vscode"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".spec"}
IGNORED_FILES = {"upload.py", ".DS_Store", "Thumbs.db"}


def git(args, cwd, token=None, check=True):
    command = ["git"]
    if token:
        encoded = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        command += ["-c", f"http.extraheader=AUTHORIZATION: basic {encoded}"]
    command += args
    env = dict(os.environ, GIT_TERMINAL_PROMPT="1" if not token else "0")
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace", env=env)
    if check and result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"git {args[0]} failed")
    return result


def project_files():
    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in files:
            path = Path(root) / name
            if name in IGNORED_FILES or path.suffix in IGNORED_SUFFIXES:
                continue
            yield path.relative_to(PROJECT_DIR)


def sync_files(target, mirror):
    wanted = set(project_files())
    if mirror:
        for path in list(Path(target).rglob("*")):
            rel = path.relative_to(target)
            if rel.parts and rel.parts[0] == ".git":
                continue
            if path.is_file() and rel not in wanted:
                path.unlink()
    for rel in wanted:
        destination = Path(target) / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_DIR / rel, destination)
    return len(wanted)


def main():
    parser = argparse.ArgumentParser(description="Upload this Antimatter folder to your GitHub fork")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Repository URL to push to")
    parser.add_argument("--branch", default=None, help="Branch to push to (default: the repository's default branch)")
    parser.add_argument("--message", "-m", default=None, help="Commit message")
    parser.add_argument("--mirror", action="store_true", help="Also delete files in the repository that are not in this folder")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without pushing")
    parser.add_argument("--yes", "-y", action="store_true", help="Do not ask for confirmation")
    args = parser.parse_args()

    if shutil.which("git") is None:
        sys.exit("Git is not installed. Get it from https://git-scm.com/downloads and run this again.")

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    work = tempfile.mkdtemp(prefix="antimatter-upload-")
    try:
        print(f"Cloning {args.repo} ...")
        try:
            git(["clone", args.repo, work], cwd=tempfile.gettempdir(), token=token)
        except RuntimeError as e:
            sys.exit(f"Could not clone the repository:\n{e}\n\nIf it is private, sign in to Git or set the GITHUB_TOKEN environment variable to a personal access token.")

        if args.branch:
            existing = git(["rev-parse", "--verify", f"origin/{args.branch}"], cwd=work, check=False)
            if existing.returncode == 0:
                git(["checkout", args.branch], cwd=work)
            else:
                git(["checkout", "-b", args.branch], cwd=work)
        branch = git(["symbolic-ref", "--short", "HEAD"], cwd=work).stdout.strip()

        count = sync_files(work, args.mirror)
        git(["add", "-A"], cwd=work)
        status = git(["status", "--short"], cwd=work).stdout.strip()
        if not status:
            print("Nothing to upload. The repository already matches this folder.")
            return

        lines = status.splitlines()
        print(f"\n{count} files checked, {len(lines)} changed on branch '{branch}':\n")
        for line in lines[:40]:
            print("  " + line)
        if len(lines) > 40:
            print(f"  ... and {len(lines) - 40} more")

        if args.dry_run:
            print("\nDry run, nothing was pushed.")
            return

        if not args.yes and input("\nPush these changes? [y/N] ").strip().lower() != "y":
            print("Cancelled.")
            return

        message = args.message
        if not message:
            message = input("Commit message [Update Antimatter]: ").strip() or "Update Antimatter"

        committed = git(["commit", "-m", message], cwd=work, check=False)
        if committed.returncode != 0:
            err = (committed.stderr + committed.stdout).strip()
            if "tell me who you are" in err or "empty ident" in err:
                name = input("Git needs your name for the commit: ").strip()
                email = input("And your email: ").strip()
                git(["config", "user.name", name], cwd=work)
                git(["config", "user.email", email], cwd=work)
                git(["commit", "-m", message], cwd=work)
            else:
                sys.exit(f"Commit failed:\n{err}")

        print("Pushing ...")
        try:
            git(["push", "-u", "origin", branch], cwd=work, token=token)
        except RuntimeError as e:
            sys.exit(f"Push failed:\n{e}\n\nMake sure you are signed in to GitHub in Git, or set GITHUB_TOKEN to a personal access token with write access to the repository.")
        print(f"\nDone. Your changes are on branch '{branch}' of {args.repo}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
