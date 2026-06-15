#!/usr/bin/env python3
"""
Hugo ブログ手動投稿 Web UI

起動方法:
    python scripts/blog_ui.py

アクセス:
    http://localhost:8080/

機能:
    - ダッシュボード: 下書き一覧・公開済み記事一覧
    - 新規記事作成フォーム（Markdownファイル生成）
    - 下書きの公開（draft: true 削除）
"""

import http.server
import json
import os
import re
import urllib.parse
import webbrowser
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BLOG_DIR = REPO_ROOT / "content" / "blog"
PORT = 8080

CATEGORIES = [
    "ライフプラン",
    "タックスプランニング",
    "金融資産運用設計",
    "未分類",
]

# ============================================================
# ファイル操作ユーティリティ
# ============================================================

def parse_frontmatter(filepath: Path) -> dict:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        kv = re.match(r'^(\w+):\s*(.+)', line.strip())
        if kv:
            key, val = kv.group(1), kv.group(2).strip().strip('"\'')
            fm[key] = val
    return fm


def list_posts() -> tuple[list[dict], list[dict]]:
    drafts, published = [], []
    for md in sorted(BLOG_DIR.glob("*.md")):
        if md.name == "_index.md":
            continue
        fm = parse_frontmatter(md)
        info = {
            "slug": fm.get("slug", md.stem),
            "title": fm.get("title", md.stem),
            "date": fm.get("date", ""),
            "filename": md.name,
            "draft": fm.get("draft", "").lower() == "true",
        }
        if info["draft"]:
            drafts.append(info)
        else:
            published.append(info)
    published.sort(key=lambda x: x["date"], reverse=True)
    return drafts, published[:10]


def write_post(title: str, slug: str, post_date: str, category: str,
               tags: str, description: str, body: str, is_draft: bool) -> Path:
    slug = re.sub(r'[^a-z0-9-]', '', slug.lower().replace(' ', '-').replace('_', '-'))
    if not slug:
        slug = f"post-{post_date}"

    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
    tags_yaml = "\n".join(f'  - "{t}"' for t in tag_list) if tag_list else '  []'

    draft_line = "draft: true\n" if is_draft else ""

    content = f"""---
title: "{title}"
date: {post_date}
slug: "{slug}"
{draft_line}description: "{description}"
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

{body}
"""
    filepath = BLOG_DIR / f"{slug}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath


def publish_post(slug: str) -> tuple[bool, str]:
    # ファイルを検索（filename または slug フィールドで一致）
    target = None
    for md in BLOG_DIR.glob("*.md"):
        if md.name == "_index.md":
            continue
        fm = parse_frontmatter(md)
        if fm.get("slug", md.stem) == slug or md.stem == slug:
            target = md
            break

    if not target:
        return False, f"slug '{slug}' のファイルが見つかりません"

    text = target.read_text(encoding="utf-8")
    if "draft: true" not in text:
        return False, "すでに公開済みです（draft: true がありません）"

    new_text = re.sub(r'^draft: true\n?', '', text, flags=re.MULTILINE)
    target.write_text(new_text, encoding="utf-8")
    return True, str(target)


# ============================================================
# HTML テンプレート
# ============================================================

CSS = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f8fafc; color: #1e293b; }
  header { background: #1e40af; color: white; padding: 1rem 2rem;
           display: flex; align-items: center; gap: 1rem; }
  header h1 { font-size: 1.25rem; font-weight: 700; }
  header a { color: white; text-decoration: none; opacity: 0.85; font-size: 0.9rem; }
  header a:hover { opacity: 1; }
  .container { max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; }
  .card { background: white; border: 1px solid #e2e8f0; border-radius: 8px;
          padding: 1.5rem; margin-bottom: 1.5rem; }
  h2 { font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem;
       color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  th { text-align: left; padding: 0.5rem 0.75rem; background: #f1f5f9;
       font-weight: 600; color: #475569; }
  td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #f1f5f9; }
  tr:last-child td { border-bottom: none; }
  .badge { display: inline-block; padding: 0.15em 0.6em; border-radius: 999px;
           font-size: 0.75rem; font-weight: 600; }
  .badge-draft { background: #fef3c7; color: #92400e; }
  .badge-pub   { background: #d1fae5; color: #065f46; }
  .btn { display: inline-block; padding: 0.4rem 1rem; border-radius: 6px;
         font-size: 0.875rem; font-weight: 600; cursor: pointer; border: none;
         text-decoration: none; }
  .btn-primary { background: #1e40af; color: white; }
  .btn-success { background: #059669; color: white; }
  .btn-sm { padding: 0.25rem 0.6rem; font-size: 0.8rem; }
  form label { display: block; font-size: 0.875rem; font-weight: 600;
               color: #374151; margin-bottom: 0.25rem; margin-top: 1rem; }
  form input, form select, form textarea {
    width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #d1d5db;
    border-radius: 6px; font-size: 0.875rem; font-family: inherit; }
  form textarea { resize: vertical; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  .actions { margin-top: 1.5rem; display: flex; gap: 0.75rem; }
  .alert { padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
  .alert-success { background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7; }
  .alert-error   { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
  .hint { font-size: 0.8rem; color: #6b7280; margin-top: 0.25rem; }
  .cmd { font-family: monospace; background: #1e293b; color: #e2e8f0;
         padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.85rem;
         margin-top: 0.75rem; overflow-x: auto; white-space: pre; }
</style>
"""

def page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Hugo ブログ管理</title>
{CSS}
</head>
<body>
<header>
  <h1>Hugo ブログ管理</h1>
  <a href="/">ダッシュボード</a>
  <a href="/new">新規記事</a>
</header>
<div class="container">
{body}
</div>
</body>
</html>"""


def dashboard_html(drafts: list, published: list) -> str:
    def draft_rows(items):
        if not items:
            return '<tr><td colspan="4" style="color:#94a3b8;text-align:center;padding:1rem">下書きはありません</td></tr>'
        rows = ""
        for p in items:
            rows += f"""<tr>
  <td>{p['date']}</td>
  <td>{p['title']}</td>
  <td><span class="badge badge-draft">下書き</span></td>
  <td><a href="/publish?slug={p['slug']}" class="btn btn-success btn-sm">公開する</a></td>
</tr>"""
        return rows

    def pub_rows(items):
        if not items:
            return '<tr><td colspan="3" style="color:#94a3b8;text-align:center;padding:1rem">記事がありません</td></tr>'
        rows = ""
        for p in items:
            rows += f"""<tr>
  <td>{p['date']}</td>
  <td>{p['title']}</td>
  <td><span class="badge badge-pub">公開中</span></td>
</tr>"""
        return rows

    return page("ダッシュボード", f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem">
  <h2 style="border:none;margin:0;font-size:1.3rem">ダッシュボード</h2>
  <a href="/new" class="btn btn-primary">+ 新規記事</a>
</div>

<div class="card">
  <h2>下書き記事（{len(drafts)}件）</h2>
  <table>
    <tr><th>日付</th><th>タイトル</th><th>状態</th><th>操作</th></tr>
    {draft_rows(drafts)}
  </table>
</div>

<div class="card">
  <h2>公開済み（直近10件）</h2>
  <table>
    <tr><th>日付</th><th>タイトル</th><th>状態</th></tr>
    {pub_rows(published)}
  </table>
</div>
""")


def new_post_html(alert: str = "") -> str:
    today = date.today().isoformat()
    cat_options = "".join(
        f'<option value="{c}"{"selected" if c == "ライフプラン" else ""}>{c}</option>'
        for c in CATEGORIES
    )
    return page("新規記事", f"""
<h2 style="font-size:1.3rem;border:none;margin-bottom:1.5rem">新規記事作成</h2>
{alert}
<div class="card">
<form method="POST" action="/new">
  <div class="form-row">
    <div>
      <label>タイトル *</label>
      <input type="text" name="title" required placeholder="記事タイトルを入力">
    </div>
    <div>
      <label>スラッグ（URL）*</label>
      <input type="text" name="slug" required placeholder="nisa-reform-2026"
             pattern="[a-z0-9\\-]+" title="英小文字・数字・ハイフンのみ">
      <p class="hint">URL: /blog/スラッグ/ になります</p>
    </div>
  </div>

  <div class="form-row">
    <div>
      <label>公開日</label>
      <input type="date" name="date" value="{today}">
    </div>
    <div>
      <label>カテゴリ</label>
      <select name="category">{cat_options}</select>
    </div>
  </div>

  <label>タグ（カンマ区切り）</label>
  <input type="text" name="tags" placeholder="NISA, 積立投資, 老後資金">

  <label>説明文（メタディスクリプション）</label>
  <textarea name="description" rows="2" placeholder="80〜120文字の説明文"></textarea>

  <label>本文（Markdown）*</label>
  <textarea name="body" rows="20" required
            placeholder="## 見出し&#10;&#10;本文をMarkdownで書いてください..."></textarea>

  <div class="actions">
    <button type="submit" name="mode" value="draft" class="btn btn-primary">下書きとして保存</button>
    <button type="submit" name="mode" value="publish" class="btn btn-success">公開記事として保存</button>
  </div>
</form>
</div>
""")


def success_html(filepath: Path, slug: str, is_draft: bool) -> str:
    mode = "下書き" if is_draft else "公開記事"
    git_cmd = f"git add content/blog/{slug}.md && git commit -m \"{'draft' if is_draft else 'feat'}: {slug}\" && git push origin develop"
    return page("保存完了", f"""
<div class="card">
  <div class="alert alert-success">✅ {mode}として保存しました: <code>{filepath.name}</code></div>

  <h2>次のステップ</h2>
  <p style="margin-top:0.5rem;font-size:0.9rem">以下のコマンドでGitにコミット・Pushしてください：</p>
  <div class="cmd">{git_cmd}</div>

  {"<p style='margin-top:0.75rem;font-size:0.875rem;color:#6b7280'>Pushするとステージング（dev-hugo.money-mgt.net）に自動デプロイされます。</p>" if is_draft else ""}

  <div class="actions" style="margin-top:1.5rem">
    <a href="/" class="btn btn-primary">ダッシュボードへ</a>
    <a href="/new" class="btn" style="background:#f1f5f9;color:#374151">続けて書く</a>
  </div>
</div>
""")


def publish_confirm_html(slug: str) -> str:
    return page("公開確認", f"""
<div class="card">
  <h2>下書きを公開しますか？</h2>
  <p style="margin:1rem 0">slug: <strong>{slug}</strong></p>
  <p style="font-size:0.875rem;color:#6b7280">
    ファイルから <code>draft: true</code> を削除します。<br>
    その後、git push → develop → main のマージで本番反映されます。
  </p>
  <form method="POST" action="/publish">
    <input type="hidden" name="slug" value="{slug}">
    <div class="actions" style="margin-top:1.5rem">
      <button type="submit" class="btn btn-success">公開する</button>
      <a href="/" class="btn" style="background:#f1f5f9;color:#374151">キャンセル</a>
    </div>
  </form>
</div>
""")


def publish_done_html(slug: str, filepath: str) -> str:
    git_cmd = f"git add content/blog/{slug}.md && git commit -m \"publish: {slug}\" && git push origin develop"
    return page("公開完了", f"""
<div class="card">
  <div class="alert alert-success">✅ 公開状態に変更しました: <code>{Path(filepath).name}</code></div>

  <h2>次のステップ</h2>
  <p style="margin-top:0.5rem;font-size:0.9rem">以下のコマンドでGitにコミット・Pushしてください：</p>
  <div class="cmd">{git_cmd}</div>

  <div class="actions" style="margin-top:1.5rem">
    <a href="/" class="btn btn-primary">ダッシュボードへ</a>
  </div>
</div>
""")


# ============================================================
# HTTP ハンドラ
# ============================================================

class BlogHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    def send_html(self, html: str, status: int = 200):
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, path: str):
        self.send_response(302)
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "":
            drafts, published = list_posts()
            self.send_html(dashboard_html(drafts, published))

        elif path == "/new":
            self.send_html(new_post_html())

        elif path == "/publish":
            slug = params.get("slug", [""])[0]
            if not slug:
                self.redirect("/")
                return
            self.send_html(publish_confirm_html(slug))

        else:
            self.send_html("<h1>404</h1>", 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = urllib.parse.parse_qs(body, keep_blank_values=True)

        def get(key: str, default: str = "") -> str:
            return data.get(key, [default])[0]

        if self.path == "/new":
            try:
                filepath = write_post(
                    title=get("title"),
                    slug=get("slug"),
                    post_date=get("date", date.today().isoformat()),
                    category=get("category", "ライフプラン"),
                    tags=get("tags"),
                    description=get("description"),
                    body=get("body"),
                    is_draft=(get("mode") == "draft"),
                )
                slug = get("slug")
                is_draft = get("mode") == "draft"
                self.send_html(success_html(filepath, slug, is_draft))
            except Exception as e:
                alert = f'<div class="alert alert-error">❌ エラー: {e}</div>'
                self.send_html(new_post_html(alert))

        elif self.path == "/publish":
            slug = get("slug")
            ok, result = publish_post(slug)
            if ok:
                self.send_html(publish_done_html(slug, result))
            else:
                alert = f'<div class="alert alert-error">❌ {result}</div>'
                drafts, published = list_posts()
                self.send_html(dashboard_html(drafts, published))

        else:
            self.redirect("/")


# ============================================================
# 起動
# ============================================================

def main():
    os.chdir(REPO_ROOT)
    print(f"Hugo ブログ管理 UI を起動します")
    print(f"  リポジトリ : {REPO_ROOT}")
    print(f"  ブログ記事 : {BLOG_DIR}")
    print(f"  URL        : http://localhost:{PORT}/")
    print(f"  停止       : Ctrl+C")
    print()

    webbrowser.open(f"http://localhost:{PORT}/")

    server = http.server.HTTPServer(("localhost", PORT), BlogHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました")


if __name__ == "__main__":
    main()
