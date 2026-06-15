#!/usr/bin/env python3
"""
Hugo ブログ草案自動生成スクリプト
- claude CLI (-p) で Markdown 草案を生成（ANTHROPIC_API_KEY 不要）
- content/blog/{slug}.md に draft: true で保存
- data/hugo-blog-topic-log.json を更新
- git commit & push (develop ブランチ)
- money-mgt に L3 Issue 起票

使用環境変数:
  GH_TOKEN  : GitHub Personal Access Token (repo スコープ)
  GH_REPO   : リポジトリ名 (例: boro74/money-mgt-website)
"""

import json
import os
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import requests

# ============================================================
# 定数
# ============================================================

PILLARS = {
    "①": "税制・制度最前線（NISA改正・年収の壁・確定申告・ふるさと納税・社会保険）",
    "②": "資産形成の基礎と実践（新NISA活用・積立投資・アセットアロケーション・住宅ローンvs投資）",
    "③": "ライフプランとキャッシュフロー設計（住宅購入・教育費・老後資金・家計の見える化）",
    "④": "保険見直し・リスク管理（保障ギャップ分析・医療保険・収入保障・必要保障額）",
}

CATEGORIES = {
    "①": "タックスプランニング",
    "②": "金融資産運用設計",
    "③": "ライフプラン",
    "④": "ライフプラン",
}

REPO_ROOT = Path(__file__).parent.parent
TOPIC_LOG_PATH = REPO_ROOT / "data" / "hugo-blog-topic-log.json"
BLOG_DIR = REPO_ROOT / "content" / "blog"
STAGING_URL = "https://dev-hugo.money-mgt.net"
MGT_REPO = "boro74/money-mgt"

_FP_BIZDEV_KEYWORDS = [
    "FPマイポータル", "FP My Portal", "Smart Associator",
    "FP業務効率化", "提案書作成 FP", "独立FP向け", "FP事務所向け",
    "マネーマネジメント サービス", "FPツール",
]


# ============================================================
# Step 1: ピラー選択
# ============================================================

def load_topic_log() -> dict:
    if TOPIC_LOG_PATH.exists():
        return json.loads(TOPIC_LOG_PATH.read_text(encoding="utf-8"))
    return {"pillars": PILLARS, "posts": []}


def select_pillar(log: dict) -> str:
    posts = log.get("posts", [])
    recent = [p["pillar"] for p in posts[-8:]]
    counts = {k: recent.count(k) for k in PILLARS}
    return min(counts, key=lambda k: (counts[k], list(PILLARS.keys()).index(k)))


# ============================================================
# Step 2: 既存記事タイトル収集（重複チェック用）
# ============================================================

def collect_existing_titles() -> list[str]:
    titles = []
    for md in BLOG_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text, re.MULTILINE)
        if m:
            titles.append(m.group(1))
    return titles


# ============================================================
# Step 3: claude CLI で草案生成
# ============================================================

def generate_draft(pillar_key: str, existing_titles: list[str]) -> dict:
    today = date.today().isoformat()
    pillar_desc = PILLARS[pillar_key]
    existing_str = "\n".join(f"- {t}" for t in existing_titles[:30])

    prompt = f"""あなたはFP（ファイナンシャルプランナー）の知識を持つブログライターです。
以下の条件でブログ記事の草案を JSON 形式で生成してください。

## 今回のテーマピラー
{pillar_key}: {pillar_desc}

## ターゲット読者
一般の現役世代（30〜50代）。FPとして仕事をする人ではなく、
お金の悩みを抱えている普通のサラリーマン・共働き夫婦など。

## 禁止事項
- FP事業者向けコンテンツ（FPツール、FP業務効率化等）は書かない
- 投資・金融商品の具体的な推奨（利回り保証など）はしない
- 下記の既存記事と同じまたは類似のテーマは避ける

## 既存記事タイトル（重複禁止）
{existing_str}

## 出力形式（必ずこの JSON のみを出力すること。説明文・前置き不要）
{{
  "title": "記事タイトル（30〜50文字・SEOを意識）",
  "slug": "url-slug-in-english-hyphenated",
  "description": "メタディスクリプション（80〜120文字）",
  "tags": ["タグ1", "タグ2", "タグ3"],
  "body_markdown": "記事本文（Markdown形式・1500〜2000字）"
}}

生成日: {today}
"""

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI 失敗 (exit {result.returncode}):\n{result.stderr[:500]}")

    raw = result.stdout.strip()

    # JSON ブロック抽出
    json_match = re.search(r'\{[\s\S]+\}', raw)
    if not json_match:
        raise ValueError(f"JSON が見つかりませんでした:\n{raw[:300]}")

    data = json.loads(json_match.group())

    # FP事業者向けキーワードチェック
    combined = data.get("title", "") + data.get("body_markdown", "")
    for kw in _FP_BIZDEV_KEYWORDS:
        if kw in combined:
            raise ValueError(f"FP事業者向けキーワード '{kw}' が含まれています。再生成してください。")

    return data


# ============================================================
# Step 4: Markdown ファイル生成
# ============================================================

def write_markdown(pillar_key: str, data: dict) -> tuple[Path, str]:
    today = date.today().isoformat()
    category = CATEGORIES[pillar_key]
    slug = re.sub(r'[^a-z0-9-]', '', data["slug"].lower().replace(' ', '-'))
    if not slug:
        slug = f"auto-{today}"

    tags_yaml = "\n".join(f'  - "{t}"' for t in data.get("tags", []))

    frontmatter = f"""---
title: "{data['title']}"
date: {today}
slug: "{slug}"
draft: true
description: "{data['description']}"
categories:
  - "{category}"
tags:
{tags_yaml}
cover:
  image: ""
  alt: ""
  hidden: false
  hiddenInList: false
---

"""

    content = frontmatter + data["body_markdown"]
    filepath = BLOG_DIR / f"{slug}.md"
    filepath.write_text(content, encoding="utf-8")
    print(f"[Step 4] 保存完了: {filepath}")
    return filepath, slug


# ============================================================
# Step 5: topic-log 更新
# ============================================================

def update_topic_log(log: dict, slug: str, pillar_key: str) -> None:
    log.setdefault("posts", []).append({
        "date": date.today().isoformat(),
        "pillar": pillar_key,
        "slug": slug,
        "draft": True,
    })
    TOPIC_LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[Step 5] topic-log 更新完了")


# ============================================================
# Step 6: git commit & push
# ============================================================

def git_commit_push(filepath: Path, slug: str) -> None:
    gh_token = os.environ.get("GH_TOKEN", "")
    today = date.today().isoformat()

    askpass = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False)
    askpass.write(f'#!/bin/sh\necho "{gh_token}"\n')
    askpass.close()
    os.chmod(askpass.name, 0o700)

    env = {**os.environ, "GIT_ASKPASS": askpass.name}

    def run(cmd, **kwargs):
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, **kwargs)
        if result.returncode != 0:
            raise RuntimeError(f"コマンド失敗: {cmd}\n{result.stderr}")
        return result.stdout.strip()

    cwd = str(REPO_ROOT)
    run(["git", "config", "user.name", "hugo-blog-draft-bot"], cwd=cwd)
    run(["git", "config", "user.email", "bot@money-mgt.net"], cwd=cwd)
    run(["git", "add", str(filepath), str(TOPIC_LOG_PATH)], cwd=cwd)
    run(["git", "commit", "-m", f"draft: ブログ草案追加 {slug} ({today}) [auto]"], cwd=cwd)

    for attempt in range(1, 4):
        try:
            run(["git", "push", "origin", "develop"], cwd=cwd)
            print("[Step 6] git push 完了")
            break
        except RuntimeError:
            if attempt == 3:
                raise
            print(f"push retry {attempt}/3...")
            import time; time.sleep(attempt * 3)

    os.unlink(askpass.name)


# ============================================================
# Step 7: money-mgt に L3 Issue 起票
# ============================================================

def create_issue(slug: str, title: str) -> None:
    gh_token = os.environ.get("GH_TOKEN", "")
    today = date.today().isoformat()
    staging_url = f"{STAGING_URL}/blog/{slug}/"
    filepath = f"content/blog/{slug}.md"

    body = f"""## 代表アクション

👉 **[ステージングで記事を確認する]({staging_url})**

確認後、このIssueに以下のいずれかをコメントしてください：
- `承認：公開` — GitHub Actions の publish-blog-draft を実行
- `修正：○○` — 修正内容を記載（エージェントが対応）
- `保留` — 次回以降に持ち越し

---

## 草案情報

| 項目 | 内容 |
|------|------|
| タイトル | {title} |
| ファイル | `{filepath}` |
| ステージングURL | [{staging_url}]({staging_url}) |
| 生成日 | {today} |

## 公開手順

1. ステージング（[dev-hugo.money-mgt.net]({STAGING_URL})）で記事を確認
2. `承認：公開` とコメント
3. money-mgt-website の Actions → **publish-blog-draft** → slug `{slug}` で実行
4. develop → main の PR をマージ → 本番反映

---
*Hugo ブログ草案自動生成ボット 自動起票 {today}*"""

    resp = requests.post(
        f"https://api.github.com/repos/{MGT_REPO}/issues",
        headers={
            "Authorization": f"Bearer {gh_token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": f"【L3・代表承認】Hugoブログ草案確認・公開依頼（{today}）",
            "body": body,
            "labels": ["L3-approval", "blog"],
        },
        timeout=30,
    )
    if resp.status_code == 201:
        print(f"[Step 7] Issue 起票完了: {resp.json().get('html_url', '')}")
    else:
        print(f"[Step 7] Issue 起票失敗 ({resp.status_code}): {resp.text[:200]}")


# ============================================================
# メイン
# ============================================================

def main():
    print("=== Hugo ブログ草案自動生成 開始 ===")

    print("[Step 1] ピラー選択...")
    log = load_topic_log()
    pillar_key = select_pillar(log)
    print(f"  選択ピラー: {pillar_key} — {PILLARS[pillar_key]}")

    print("[Step 2] 既存記事収集...")
    existing_titles = collect_existing_titles()
    print(f"  既存記事数: {len(existing_titles)}")

    print("[Step 3] claude CLI で草案生成...")
    draft_data = generate_draft(pillar_key, existing_titles)
    print(f"  タイトル: {draft_data['title']}")

    print("[Step 4] Markdown ファイル生成...")
    filepath, slug = write_markdown(pillar_key, draft_data)

    print("[Step 5] topic-log 更新...")
    update_topic_log(log, slug, pillar_key)

    print("[Step 6] git commit & push...")
    git_commit_push(filepath, slug)

    print("[Step 7] money-mgt に L3 Issue 起票...")
    create_issue(slug, draft_data["title"])

    print("=== 完了 ===")
    print(f"  スラッグ   : {slug}")
    print(f"  ステージング: {STAGING_URL}/blog/{slug}/")


if __name__ == "__main__":
    main()
