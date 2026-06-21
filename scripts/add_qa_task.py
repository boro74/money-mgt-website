"""
QAレビューで検出されたP0/P1問題をdirector/task-queue/queue.jsonに追加する。
環境変数: REPO, PR_NUMBER, PR_BRANCH, PR_TITLE, MAX_SEV, TASK_ID
/tmp/qa_result.json を参照する。

このファイルは boro74/money-mgt の scripts/add_qa_task.py をベンダリングしたもの。
PR差分のレビュー可能性を確保するため、外部リポジトリから実行時に取得せず
本リポジトリ内に複製している。更新する場合は money-mgt 側との同期を忘れないこと。
"""
import json
import os
from datetime import datetime
from pathlib import Path

qa = json.loads(Path("/tmp/qa_result.json").read_text())
repo = os.environ["REPO"]
pr_num = int(os.environ["PR_NUMBER"])
pr_branch = os.environ["PR_BRANCH"]
pr_title = os.environ["PR_TITLE"]
max_sev = os.environ["MAX_SEV"]
task_id = os.environ["TASK_ID"]
issues = qa.get("issues_text", "")

pr_url = f"https://github.com/{repo}/pull/{pr_num}"
sev_label = "P0（必須修正）" if max_sev == "p0" else "P1（要対応）"
desc = (
    f"PR #{pr_num} のQAレビューで {sev_label} 問題が検出されました。\n\n"
    f"【PR情報】\n- リポジトリ: {repo}\n- PR URL: {pr_url}\n"
    f"- ブランチ: {pr_branch}\n- タイトル: {pr_title}\n\n"
    f"【検出された問題】\n{issues}\n\n"
    f"【対応手順】\n"
    f"1. implementation-agent が {pr_url} のレビューコメントを読む\n"
    f"2. ブランチ {pr_branch} にチェックアウトして修正を実装・push する\n"
    f"3. push 後に QAレビューが自動再実行される"
)

queue_path = Path("director/task-queue/queue.json")
data = json.loads(queue_path.read_text(encoding="utf-8"))
tasks = data if isinstance(data, list) else data.get("tasks", [])
now = datetime.now().isoformat()

new_task = {
    "task_id": task_id,
    "title": f"QAレビュー指摘修正: {repo} PR#{pr_num}（{max_sev}）",
    "status": "pending",
    "priority": "high" if max_sev == "p0" else "medium",
    "authority_level": "L1",
    "source_agent": "qa-review-bot",
    "target_agent": "dev-supervisor",
    "description": desc,
    "input_files": [],
    "output_path": "dev-headquarters/product-dev/implementation/",
    "output_filename": f"qa-fix-{repo.replace('/', '-')}-pr{pr_num}.md",
    "created_at": now,
    "updated_at": now,
    "blocked_reason": None,
    "depends_on": [],
    "metadata": {
        "pr_repo": repo,
        "pr_number": pr_num,
        "pr_branch": pr_branch,
        "max_severity": max_sev,
        "source": "qa-review-workflow",
    },
}

tasks.append(new_task)
if isinstance(data, list):
    queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
else:
    data["tasks"] = tasks
    queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

print(f"タスク追加完了: {new_task['task_id']}")
