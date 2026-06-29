#!/usr/bin/env python3
"""
.htaccess の RewriteRule リダイレクト先を /blog/{slug}/ に再生成する
- frontmatterのslugフィールドを使用（日本語スラッグはID数字に変更済み）
- エイリアス（/archives/ID/）→ /blog/{slug}/ のマッピングを再構築
"""
import os
import re
import glob

BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'blog')
HTACCESS = os.path.join(os.path.dirname(__file__), '..', 'static', '.htaccess')

def build_redirect_map():
    """aliases→slug のマップを frontmatter から構築"""
    redirect_map = {}  # wp_id -> slug
    for fp in sorted(glob.glob(os.path.join(BLOG_DIR, '*.md'))):
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not m:
            continue
        front = m.group(1)

        # aliasesから /archives/ID/ を抽出
        alias_match = re.search(r'/archives/(\d+)/', front)
        if not alias_match:
            continue
        wp_id = int(alias_match.group(1))

        # slugフィールドを優先、なければファイル名
        slug_match = re.search(r'^\s*slug:\s*"?([^"\n]+)"?\s*$', front, re.MULTILINE)
        if slug_match:
            slug = slug_match.group(1).strip()
        else:
            # ファイル名から生成（英数字ファイルのみ）
            basename = os.path.splitext(os.path.basename(fp))[0]
            slug = basename

        redirect_map[wp_id] = slug

    return redirect_map

def write_htaccess(redirect_map):
    lines = [
        "# =================================================",
        "# WordPress /archives/ID/ → Hugo /blog/slug/ 301リダイレクト",
        "# 自動生成: scripts/regen-htaccess.py",
        "# =================================================",
        "RewriteEngine On",
        "",
    ]
    for wp_id in sorted(redirect_map.keys()):
        slug = redirect_map[wp_id]
        lines.append(f"RewriteRule ^archives/{wp_id}/?$ /blog/{slug}/ [R=301,L]")

    content = "\n".join(lines) + "\n"
    with open(HTACCESS, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"書き込み完了: {len(redirect_map)} 件")

if __name__ == '__main__':
    print("=== .htaccess 再生成 ===")
    redirect_map = build_redirect_map()
    write_htaccess(redirect_map)
    print("完了")
