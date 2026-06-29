#!/usr/bin/env python3
"""
アイキャッチSVG生成 + ブログ記事frontmatterへ cover 追記スクリプト
"""
import os
import re
import glob

EYECATCH_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'eyecatch')
BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'blog')

# カテゴリ → (画像ファイル名, グラデ色1, グラデ色2, アイコンpath, ラベル)
CATEGORIES = {
    "ライフプラン": ("life-plan.svg", "#1a56db", "#0891b2", "life", "ライフプラン"),
    "金融資産運用設計": ("investment.svg", "#047857", "#0d9488", "chart", "金融資産運用設計"),
    "タックスプランニング": ("tax.svg", "#7c3aed", "#a855f7", "tax", "タックスプランニング"),
    "リスクと保険": ("insurance.svg", "#dc2626", "#f59e0b", "shield", "リスクと保険"),
    "不動産運用設計": ("realestate.svg", "#0e7490", "#06b6d4", "building", "不動産運用設計"),
    "相続・事業承継": ("inheritance.svg", "#b45309", "#f59e0b", "tree", "相続・事業承継"),
    "未分類": ("default.svg", "#374151", "#6b7280", "default", "マネーマネジメント"),
}
DEFAULT_IMAGE = "default.svg"

# SVGアイコンパス定義
ICONS = {
    "life": """
        <!-- House -->
        <polygon points="600,160 760,280 760,420 440,420 440,280" fill="rgba(255,255,255,0.25)" stroke="rgba(255,255,255,0.6)" stroke-width="4" stroke-linejoin="round"/>
        <polygon points="600,120 800,290 400,290" fill="rgba(255,255,255,0.35)" stroke="rgba(255,255,255,0.7)" stroke-width="4" stroke-linejoin="round"/>
        <rect x="540" y="330" width="120" height="90" fill="rgba(255,255,255,0.4)" stroke="rgba(255,255,255,0.7)" stroke-width="3"/>
    """,
    "chart": """
        <!-- Bar chart -->
        <rect x="420" y="320" width="60" height="100" rx="4" fill="rgba(255,255,255,0.35)" stroke="rgba(255,255,255,0.6)" stroke-width="2"/>
        <rect x="510" y="250" width="60" height="170" rx="4" fill="rgba(255,255,255,0.45)" stroke="rgba(255,255,255,0.7)" stroke-width="2"/>
        <rect x="600" y="200" width="60" height="220" rx="4" fill="rgba(255,255,255,0.55)" stroke="rgba(255,255,255,0.8)" stroke-width="2"/>
        <rect x="690" y="280" width="60" height="140" rx="4" fill="rgba(255,255,255,0.4)" stroke="rgba(255,255,255,0.6)" stroke-width="2"/>
        <rect x="780" y="220" width="60" height="200" rx="4" fill="rgba(255,255,255,0.5)" stroke="rgba(255,255,255,0.7)" stroke-width="2"/>
        <line x1="400" y1="430" x2="860" y2="430" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
    """,
    "tax": """
        <!-- Calculator -->
        <rect x="470" y="140" width="260" height="300" rx="16" fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.6)" stroke-width="4"/>
        <rect x="490" y="160" width="220" height="70" rx="8" fill="rgba(255,255,255,0.4)"/>
        <circle cx="515" cy="270" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="565" cy="270" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="615" cy="270" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="665" cy="270" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="715" cy="270" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="515" cy="320" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="565" cy="320" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="615" cy="320" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="665" cy="320" r="14" fill="rgba(255,255,255,0.5)"/>
        <rect x="700" y="305" width="30" height="60" rx="8" fill="rgba(255,255,255,0.7)"/>
        <circle cx="515" cy="370" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="565" cy="370" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="615" cy="370" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="665" cy="370" r="14" fill="rgba(255,255,255,0.5)"/>
        <circle cx="715" cy="370" r="14" fill="rgba(255,255,255,0.5)"/>
    """,
    "shield": """
        <!-- Shield -->
        <path d="M600,140 L760,200 L760,340 Q760,440 600,490 Q440,440 440,340 L440,200 Z"
              fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.7)" stroke-width="5" stroke-linejoin="round"/>
        <path d="M600,170 L740,222 L740,336 Q740,418 600,460 Q460,418 460,336 L460,222 Z"
              fill="rgba(255,255,255,0.15)"/>
        <text x="600" y="345" font-size="90" text-anchor="middle" dominant-baseline="middle"
              fill="rgba(255,255,255,0.85)" font-family="serif">✓</text>
    """,
    "building": """
        <!-- Building -->
        <rect x="450" y="200" width="300" height="240" fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.6)" stroke-width="4"/>
        <rect x="480" y="170" width="80" height="30" fill="rgba(255,255,255,0.3)" stroke="rgba(255,255,255,0.5)" stroke-width="2"/>
        <rect x="640" y="170" width="80" height="30" fill="rgba(255,255,255,0.3)" stroke="rgba(255,255,255,0.5)" stroke-width="2"/>
        <rect x="480" y="230" width="50" height="40" rx="2" fill="rgba(255,255,255,0.4)"/>
        <rect x="575" y="230" width="50" height="40" rx="2" fill="rgba(255,255,255,0.4)"/>
        <rect x="670" y="230" width="50" height="40" rx="2" fill="rgba(255,255,255,0.4)"/>
        <rect x="480" y="295" width="50" height="40" rx="2" fill="rgba(255,255,255,0.4)"/>
        <rect x="575" y="295" width="50" height="40" rx="2" fill="rgba(255,255,255,0.4)"/>
        <rect x="670" y="295" width="50" height="40" rx="2" fill="rgba(255,255,255,0.4)"/>
        <rect x="540" y="360" width="120" height="80" rx="4" fill="rgba(255,255,255,0.5)" stroke="rgba(255,255,255,0.6)" stroke-width="2"/>
        <line x1="430" y1="440" x2="770" y2="440" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
    """,
    "tree": """
        <!-- Family tree / inheritance -->
        <circle cx="600" cy="175" r="40" fill="rgba(255,255,255,0.3)" stroke="rgba(255,255,255,0.7)" stroke-width="3"/>
        <line x1="600" y1="215" x2="600" y2="270" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
        <line x1="600" y1="270" x2="490" y2="270" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
        <line x1="600" y1="270" x2="710" y2="270" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
        <line x1="490" y1="270" x2="490" y2="310" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
        <line x1="710" y1="270" x2="710" y2="310" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
        <circle cx="490" cy="345" r="35" fill="rgba(255,255,255,0.25)" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
        <circle cx="710" cy="345" r="35" fill="rgba(255,255,255,0.25)" stroke="rgba(255,255,255,0.6)" stroke-width="3"/>
        <line x1="490" y1="380" x2="490" y2="420" stroke="rgba(255,255,255,0.5)" stroke-width="2"/>
        <line x1="490" y1="420" x2="430" y2="420" stroke="rgba(255,255,255,0.5)" stroke-width="2"/>
        <line x1="490" y1="420" x2="550" y2="420" stroke="rgba(255,255,255,0.5)" stroke-width="2"/>
        <circle cx="430" cy="445" r="25" fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.5)" stroke-width="2"/>
        <circle cx="550" cy="445" r="25" fill="rgba(255,255,255,0.2)" stroke="rgba(255,255,255,0.5)" stroke-width="2"/>
    """,
    "default": """
        <!-- Coin / Money -->
        <circle cx="600" cy="290" r="170" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.5)" stroke-width="5"/>
        <circle cx="600" cy="290" r="140" fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.4)" stroke-width="3"/>
        <text x="600" y="310" font-size="130" text-anchor="middle" dominant-baseline="middle"
              fill="rgba(255,255,255,0.7)" font-family="Arial, sans-serif" font-weight="bold">¥</text>
    """,
}

def make_svg(color1, color2, icon_key, label):
    icon_svg = ICONS.get(icon_key, ICONS["default"])
    # category label font size
    label_size = 52 if len(label) <= 6 else 44
    return f'''<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color1}"/>
      <stop offset="100%" stop-color="{color2}"/>
    </linearGradient>
  </defs>
  <!-- Background -->
  <rect width="1200" height="630" fill="url(#bg)"/>
  <!-- Decorative circles -->
  <circle cx="80" cy="80" r="220" fill="rgba(255,255,255,0.06)"/>
  <circle cx="1120" cy="550" r="280" fill="rgba(255,255,255,0.06)"/>
  <circle cx="1050" cy="80" r="160" fill="rgba(255,255,255,0.04)"/>
  <!-- Icon area -->
  {icon_svg}
  <!-- Bottom bar -->
  <rect x="0" y="530" width="1200" height="100" fill="rgba(0,0,0,0.25)"/>
  <!-- Category label -->
  <text x="600" y="480" font-size="{label_size}" text-anchor="middle" dominant-baseline="middle"
        fill="white" font-family="Noto Sans JP, Hiragino Kaku Gothic Pro, Yu Gothic, Meiryo, sans-serif"
        font-weight="900" letter-spacing="2">{label}</text>
  <!-- Site name -->
  <text x="600" y="580" font-size="26" text-anchor="middle" dominant-baseline="middle"
        fill="rgba(255,255,255,0.75)" font-family="Noto Sans JP, Hiragino Kaku Gothic Pro, Yu Gothic, Meiryo, sans-serif"
        font-weight="500" letter-spacing="4">マネーマネジメント</text>
</svg>'''


def generate_svgs():
    os.makedirs(EYECATCH_DIR, exist_ok=True)
    for cat, (filename, c1, c2, icon, label) in CATEGORIES.items():
        svg = make_svg(c1, c2, icon, label)
        path = os.path.join(EYECATCH_DIR, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(svg)
        print(f"Generated: {filename}")


def get_category_image(categories):
    for cat in categories:
        cat = cat.strip('"').strip("'").strip()
        if cat in CATEGORIES:
            return '/images/eyecatch/' + CATEGORIES[cat][0]
    return '/images/eyecatch/' + DEFAULT_IMAGE


def add_cover_to_posts():
    pattern = os.path.join(BLOG_DIR, '*.md')
    files = glob.glob(pattern)
    updated = 0
    skipped = 0

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # frontmatter を抽出
        m = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
        if not m:
            print(f"SKIP (no frontmatter): {os.path.basename(filepath)}")
            skipped += 1
            continue

        front = m.group(1)
        body = m.group(2)

        # すでに cover: があればスキップ
        if re.search(r'^cover:', front, re.MULTILINE):
            skipped += 1
            continue

        # categories を読み取る
        cats = re.findall(r'^\s+- "?(.*?)"?\s*$', front, re.MULTILINE)
        image_path = get_category_image(cats)

        # cover ブロックを追加
        cover_block = f'cover:\n  image: "{image_path}"\n  alt: ""\n  hidden: false\n  hiddenInList: false'
        new_front = front.rstrip() + '\n' + cover_block
        new_content = f'---\n{new_front}\n---\n{body}'

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        updated += 1

    print(f"\nDone: {updated} updated, {skipped} skipped")


if __name__ == '__main__':
    print("=== SVG生成 ===")
    generate_svgs()
    print("\n=== frontmatter更新 ===")
    add_cover_to_posts()
