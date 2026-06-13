#!/usr/bin/env python3
"""
WordPress to Hugo blog migration script.
Converts 75 articles from www.money-mgt.net to Hugo markdown format.
Generates static/.htaccess with 301 redirects.

Usage:
  pip install html2text requests
  python scripts/migrate-blog.py
"""

import requests
import os
import re
import html as html_module
from pathlib import Path

WP_API_BASE = "https://www.money-mgt.net/wp-json/wp/v2"
REPO_ROOT   = Path(__file__).parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "blog"
STATIC_DIR  = REPO_ROOT / "static"

DIY_CATEGORY_ID     = 13
UNCATEGORIZED_ID    = 1

# slugが数字のみの記事はタイトルからslugを生成する代替slug
SLUG_OVERRIDES = {
    442: "bonus-midage-2024",
    551: "kiso-kojo-2025",
}

# ===== ユーティリティ =====

def sanitize_slug(slug: str) -> str:
    """WPのpost_name（slug）をHugoファイル名として安全な形式に変換。"""
    from urllib.parse import unquote
    # URL%エンコードをデコード（例: %E3%83%96... → ブ）
    slug = unquote(slug)
    slug = html_module.unescape(slug)
    # URLで問題になる文字を除去（%は unquote 後なので安全）
    slug = re.sub(r'[?/\\:*"<>|#%&=+@!]', '', slug)
    slug = slug.strip('-').strip()
    return slug or "post"


def html_to_markdown(html_content: str) -> str:
    """HTML → Markdown 変換。html2text がなければ簡易変換。"""
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links   = False
        h.ignore_images  = True   # AdobeStock素材はライセンス確認が必要なのでスキップ
        h.body_width     = 0
        h.unicode_snob   = True
        return h.handle(html_content).strip()
    except ImportError:
        # フォールバック：正規表現で簡易変換
        t = html_content
        t = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', t, flags=re.DOTALL)
        t = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', t, flags=re.DOTALL)
        t = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1', t, flags=re.DOTALL)
        t = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', t, flags=re.DOTALL)
        t = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', t, flags=re.DOTALL)
        t = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', t, flags=re.DOTALL)
        t = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', t, flags=re.DOTALL)
        t = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', t, flags=re.DOTALL)
        t = re.sub(r'<br\s*/?>', '\n', t)
        t = re.sub(r'<[^>]+>', '', t)
        t = html_module.unescape(t)
        return t.strip()


def yaml_str(value: str) -> str:
    """YAML文字列をダブルクォートで安全にエスケープ。"""
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

# ===== API取得 =====

def fetch_all_posts():
    posts, page = [], 1
    while True:
        resp = requests.get(f"{WP_API_BASE}/posts", params={
            'per_page': 100, 'page': page,
            '_fields': 'id,slug,title,date,categories,tags,content,excerpt',
            'orderby': 'date', 'order': 'asc',
        }, timeout=60)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        posts.extend(data)
        if len(data) < 100:
            break
        page += 1
    return posts


def fetch_map(endpoint: str) -> dict:
    resp = requests.get(f"{WP_API_BASE}/{endpoint}",
                        params={'per_page': 100, '_fields': 'id,name'}, timeout=30)
    return {item['id']: item['name'] for item in resp.json()} if resp.ok else {}

# ===== メイン =====

def main():
    print("=== WordPress → Hugo 移行スクリプト ===\n")

    print("① カテゴリ・タグ取得中...")
    cat_map = fetch_map("categories")
    tag_map = fetch_map("tags")
    print(f"   カテゴリ {len(cat_map)}件 / タグ {len(tag_map)}件")

    print("② 全記事取得中（本文含む、時間がかかります）...")
    posts = fetch_all_posts()
    print(f"   取得完了: {len(posts)}件\n")

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    htaccess_lines = [
        "# =================================================",
        "# WordPress /archives/ID/ → Hugo /blog/slug/ 301リダイレクト",
        "# 自動生成: scripts/migrate-blog.py",
        "# =================================================",
        "RewriteEngine On",
        "",
    ]

    migrated, skipped = [], []

    for post in posts:
        post_id      = post['id']
        title_raw    = html_module.unescape(post['title']['rendered'])
        date         = post['date'][:10]
        category_ids = post.get('categories', [])
        tag_ids      = post.get('tags', [])

        # DIYカテゴリはスキップ
        if DIY_CATEGORY_ID in category_ids:
            skipped.append(f"[DIY SKIP] id={post_id} | {title_raw[:40]}")
            continue

        # スラッグ決定（数字のみ → オーバーライド、それ以外はサニタイズ）
        raw_slug = post['slug']
        if post_id in SLUG_OVERRIDES:
            slug = SLUG_OVERRIDES[post_id]
        else:
            slug = sanitize_slug(raw_slug)

        if not slug:
            slug = f"post-{post_id}"

        # カテゴリ名（未分類は除外、複数対応）
        categories = [cat_map[cid] for cid in category_ids
                      if cid in cat_map and cid != UNCATEGORIZED_ID]
        if not categories and UNCATEGORIZED_ID in category_ids:
            categories = ["未分類"]

        # タグ名（上限10個）
        tags = [tag_map[tid] for tid in tag_ids if tid in tag_map][:10]

        # description（excerpt から生成）
        excerpt_html = post.get('excerpt', {}).get('rendered', '')
        description  = re.sub(r'<[^>]+>', '', excerpt_html).strip()
        description  = html_module.unescape(description)[:160]

        # 本文変換
        body_md = html_to_markdown(post['content']['rendered'])

        # --- frontmatter 生成 ---
        fm = ['---', f'title: {yaml_str(title_raw)}', f'date: {date}']

        if description:
            fm.append(f'description: {yaml_str(description)}')

        if categories:
            fm.append('categories:')
            fm.extend(f'  - {yaml_str(c)}' for c in categories)

        if tags:
            fm.append('tags:')
            fm.extend(f'  - {yaml_str(t)}' for t in tags)

        # aliases: Hugo が /archives/ID/index.html を生成してメタリフレッシュで誘導
        fm.append('aliases:')
        fm.append(f'  - /archives/{post_id}/')
        fm.append('---')

        content = '\n'.join(fm) + '\n\n' + body_md + '\n'

        # ファイル保存
        filepath = CONTENT_DIR / f"{slug}.md"
        if filepath.exists():
            # 衝突時はIDをサフィックスに追加
            filepath = CONTENT_DIR / f"{slug}-{post_id}.md"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        # .htaccess 301ルール（[NE]でURLエンコードをそのまま通す）
        htaccess_lines.append(
            f"RewriteRule ^archives/{post_id}/?$ /blog/{slug}/ [R=301,L]"
        )

        migrated.append(f"[OK] id={post_id} | {slug[:35]} | {title_raw[:40]}")

    # .htaccess 保存
    htaccess_path = STATIC_DIR / ".htaccess"
    with open(htaccess_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(htaccess_lines) + '\n')

    # サマリー
    print(f"[DONE] 移行完了: {len(migrated)}件")
    print(f"[SKIP] スキップ: {len(skipped)}件")
    print()
    for s in skipped:
        print(f"  {s}")
    print(f"\n出力先:   {CONTENT_DIR}")
    print(f".htaccess: {htaccess_path}")


if __name__ == '__main__':
    main()
