#!/usr/bin/env python3
"""
static/images/blog/ の画像を一括最適化
- 長辺を最大1200pxにリサイズ
- PNG/WEBP/JPEG → JPEG に変換（拡張子 .jpg で保存）
- 品質85でエンコード
- frontmatterのカバーパスをリネーム後のパスに更新
"""
import os
import re
import glob
from PIL import Image

IMG_DIR  = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'blog')
BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'blog')
MAX_SIZE = (1200, 800)
QUALITY  = 85

def optimize_images():
    rename_map = {}  # old_url -> new_url  (for frontmatter update)
    files = glob.glob(os.path.join(IMG_DIR, '*'))
    for fp in files:
        ext = os.path.splitext(fp)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            continue
        try:
            img = Image.open(fp)
            # RGBA / Palette → RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                bg.paste(img, mask=img.split()[-1] if img.mode in ('RGBA','LA') else None)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            # リサイズ（縮小のみ）
            img.thumbnail(MAX_SIZE, Image.LANCZOS)
            # 保存先: 常に .jpg
            base = os.path.splitext(fp)[0]
            new_fp = base + '.jpg'
            img.save(new_fp, 'JPEG', quality=QUALITY, optimize=True)
            old_size = os.path.getsize(fp)
            new_size = os.path.getsize(new_fp)
            # 元ファイルと異なる場合は削除
            if fp != new_fp:
                os.remove(fp)
            print(f"  {os.path.basename(fp)} → {os.path.basename(new_fp)} "
                  f"({old_size//1024}KB → {new_size//1024}KB)")
            # URLマップ
            old_url = '/images/blog/' + os.path.basename(fp)
            new_url = '/images/blog/' + os.path.basename(new_fp)
            if old_url != new_url:
                rename_map[old_url] = new_url
        except Exception as e:
            print(f"  ERROR {os.path.basename(fp)}: {e}")
    return rename_map

def update_frontmatter(rename_map):
    """cover.image のURLを変換後パスに置き換え"""
    if not rename_map:
        return
    updated = 0
    for fp in glob.glob(os.path.join(BLOG_DIR, '*.md')):
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = content
        for old_url, new_url in rename_map.items():
            new_content = new_content.replace(f'"{old_url}"', f'"{new_url}"')
        if new_content != content:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated += 1
    print(f"frontmatter更新: {updated} 件")

if __name__ == '__main__':
    print("=== 画像最適化 ===")
    rename_map = optimize_images()
    print(f"\n=== frontmatter更新 ({len(rename_map)} 件リネーム) ===")
    update_frontmatter(rename_map)
    print("\n完了")
