"""Daily local run: Claude Code social search -> scraper -> backup commit.

Runs on your own computer with your own Claude Code login (no API key, no token).
Usage: python -m scraper.daily   (run_daily.cmd calls this from Task Scheduler)
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import date

from . import run

ROOT = run.ROOT
PROMPT = ROOT / "scraper" / "claude_prompt.md"


def claude_search() -> None:
    exe = shutil.which("claude")
    if not exe:
        print("claude komutu bulunamadı, sosyal medya taraması atlandı")
        return
    prompt = PROMPT.read_text(encoding="utf-8").replace("{TODAY}", date.today().isoformat())
    print("Claude Code taraması başlıyor…", flush=True)
    try:
        # prompt goes through stdin so quotes and Turkish characters survive
        res = subprocess.run(
            [exe, "-p", "--allowedTools", "WebSearch,WebFetch,Read,Write", "--max-turns", "60"],
            input=prompt, text=True, encoding="utf-8", cwd=ROOT,
            capture_output=True, timeout=30 * 60,
        )
        print(res.stdout[-3000:])
        if res.returncode:
            print(f"claude çıkış kodu {res.returncode}: {res.stderr[-1000:]}")
    except subprocess.TimeoutExpired:
        print("Claude Code taraması 30 dakikada bitmedi, önceki sonuçlar kullanılacak")


def backup() -> None:
    """Commit the data to the private GitHub repo; failures are fine (offline etc.)."""
    if not (ROOT / ".git").exists() or not shutil.which("git"):
        return
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    git("add", "site/data", "data")
    if git("diff", "--cached", "--quiet").returncode:
        git("commit", "-m", f"data: günlük güncelleme {date.today().isoformat()}")
        out = git("push")
        print("yedek push:", "tamam" if out.returncode == 0 else out.stderr.strip()[-300:])


def main() -> None:
    claude_search()
    run.main()
    backup()


if __name__ == "__main__":
    main()
