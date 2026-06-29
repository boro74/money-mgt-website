#!/usr/bin/env python3
"""
日本語ファイル名のブログ記事に英数字スラッグを設定する
- aliases: [/archives/ID/] から WP記事IDを抽出
- slug: "ID" をfrontmatterに追加（既にslugがある場合はスキップ）
- 対象: ファイル名に非ASCII文字が含まれる記事
"""
import os
import re
import glob

BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'blog')

def has_non_ascii(s):
    return any(ord(c) > 127 for c in s)

def fix_slugs():
    updated = 0
    skipped = 0
    no_alias = 0

    for fp in sorted(glob.glob(os.path.join(BLOG_DIR, '*.md'))):
        filename = os.path.basename(fp)
        # 英数字ファイル名はスキップ
        if not has_non_ascii(filename):
            continue

        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()

        # frontmatter抽出
        m = re.match(r'^(---\n)(.*?)(\n---\n)(.*)', content, re.DOTALL)
        if not m:
            print(f"  SKIP (no frontmatter): {filename}")
            skipped += 1
            continue

        dash1, front, dash2, body = m.group(1), m.group(2), m.group(3), m.group(4)

        # 既にslugがある場合はスキップ
        if re.search(r'^\s*slug\s*:', front, re.MULTILINE):
            print(f"  SKIP (slug exists): {filename}")
            skipped += 1
            continue

        # aliasesからWP IDを抽出
        alias_match = re.search(r'/archives/(\d+)/', front)
        if not alias_match:
            print(f"  SKIP (no alias): {filename}")
            no_alias += 1
            continue

        wp_id = alias_match.group(1)
        slug = wp_id  # /blog/858/ のようなURL

        # dateフィールドの直後にslugを挿入
        new_front = re.sub(
            r'(^date:.*$)',
            r'\1\nslug: "' + slug + '"',
            front,
            count=1,
            flags=re.MULTILINE
        )

        with open(fp, 'w', encoding='utf-8') as f:
            f.write(dash1 + new_front + dash2 + body)

        print(f"  OK: {filename} → /blog/{slug}/")
        updated += 1

    print(f"\n完了: 更新 {updated} 件 / スキップ {skipped} 件 / エイリアスなし {no_alias} 件")

if __name__ == '__main__':
    print("=== 日本語スラッグ修正 ===")
    fix_slugs()
