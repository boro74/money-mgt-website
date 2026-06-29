#!/usr/bin/env python3
"""
WordPress → Hugo アイキャッチ画像移行スクリプト

1. WP REST API で全記事のアイキャッチ画像URLを取得
2. static/images/blog/ へダウンロード
3. Hugo記事のfrontmatter cover.image を更新
   （アイキャッチなし記事はカテゴリSVGをそのまま維持）
"""
import os
import re
import glob
import json
import urllib.request
import urllib.parse
import time

WP_BASE = "https://www.money-mgt.net"
BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'blog')
IMG_DIR  = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'blog')
IMG_URL_PREFIX = "/images/blog/"

os.makedirs(IMG_DIR, exist_ok=True)

# ────────────────────────────────────────────
# 1. Hugo記事を読み込み aliases → filepath マップを作成
# ────────────────────────────────────────────
def build_hugo_map():
    """aliases: [/archives/ID/] からWP記事IDをキーにしたマップを返す"""
    alias_map = {}   # wp_id(int) -> filepath
    cat_map   = {}   # filepath -> [categories]
    for fp in glob.glob(os.path.join(BLOG_DIR, '*.md')):
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not m:
            continue
        front = m.group(1)
        # aliases から /archives/ID/ を抽出
        for alias in re.findall(r'/archives/(\d+)/', front):
            alias_map[int(alias)] = fp
        # categories
        cats = re.findall(r'^\s+- "?(.*?)"?\s*$', front, re.MULTILINE)
        cat_map[fp] = cats
    print(f"Hugo記事マップ: {len(alias_map)} 件")
    return alias_map, cat_map

# ────────────────────────────────────────────
# 2. WP REST API で全記事 + アイキャッチURLを取得
# ────────────────────────────────────────────
def fetch_wp_posts():
    """WP REST APIから全記事のfeatured_mediaと埋め込みURLを取得"""
    posts = []
    page = 1
    while True:
        url = (f"{WP_BASE}/wp-json/wp/v2/posts"
               f"?per_page=100&page={page}"
               f"&_fields=id,slug,featured_media,_links"
               f"&_embed")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"API取得エラー page={page}: {e}")
            break
        if not data:
            break
        posts.extend(data)
        print(f"  page {page}: {len(data)} 件取得")
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.5)
    print(f"WP記事合計: {len(posts)} 件")
    return posts

def extract_featured_url(post):
    """記事データからアイキャッチ画像URLを抽出"""
    try:
        embedded = post.get('_embedded', {})
        media_list = embedded.get('wp:featuredmedia', [])
        if media_list and isinstance(media_list[0], dict):
            # フルサイズ
            return media_list[0].get('source_url', '')
    except Exception:
        pass
    return ''

# ────────────────────────────────────────────
# 3. 画像ダウンロード
# ────────────────────────────────────────────
def download_image(url, wp_id):
    """画像をダウンロードしてローカルパスを返す。失敗時は None"""
    if not url:
        return None
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or '.jpg'
    filename = f"{wp_id}{ext}"
    local_path = os.path.join(IMG_DIR, filename)
    if os.path.exists(local_path):
        return IMG_URL_PREFIX + filename
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(local_path, 'wb') as f:
            f.write(data)
        size_kb = len(data) // 1024
        print(f"  DL: {filename} ({size_kb}KB)")
        time.sleep(0.2)
        return IMG_URL_PREFIX + filename
    except Exception as e:
        print(f"  DLエラー {url}: {e}")
        return None

# ────────────────────────────────────────────
# 4. Hugo frontmatterを更新
# ────────────────────────────────────────────
def update_frontmatter(filepath, image_url):
    """cover.image を新しいURLで置き換える"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.match(r'^(---\n.*?\n---\n)(.*)', content, re.DOTALL)
    if not m:
        return False
    front_block = m.group(1)
    body = m.group(2)
    # cover.image を置き換え
    new_front = re.sub(
        r'(cover:\n\s+image:\s*)".+?"',
        f'\\1"{image_url}"',
        front_block
    )
    if new_front == front_block:
        return False
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_front + body)
    return True

# ────────────────────────────────────────────
# メイン
# ────────────────────────────────────────────
def main():
    print("=== Hugo記事マップ構築 ===")
    alias_map, cat_map = build_hugo_map()

    print("\n=== WP REST API から記事取得 ===")
    wp_posts = fetch_wp_posts()

    updated = 0
    no_image = 0
    no_match = 0

    print("\n=== アイキャッチ移行処理 ===")
    for post in wp_posts:
        wp_id = post['id']
        hugo_fp = alias_map.get(wp_id)
        if not hugo_fp:
            no_match += 1
            continue

        img_url = extract_featured_url(post)
        if not img_url:
            no_image += 1
            continue

        local_url = download_image(img_url, wp_id)
        if not local_url:
            no_image += 1
            continue

        if update_frontmatter(hugo_fp, local_url):
            updated += 1
        else:
            print(f"  frontmatter更新失敗: {os.path.basename(hugo_fp)}")

    print(f"""
=== 完了 ===
  更新済み    : {updated} 件（WP画像に差し替え）
  画像なし    : {no_image} 件（カテゴリSVGのまま）
  マッチなし  : {no_match} 件（新規記事等）
""")

if __name__ == '__main__':
    main()
