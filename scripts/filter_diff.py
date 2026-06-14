"""
PR差分フィルタリングスクリプト
コードレビュー不要なコンテンツファイルを除外し、コードファイルのみの差分を出力する。

使用方法:
  python3 scripts/filter_diff.py \
    --input /tmp/pr_diff_full.txt \
    --output /tmp/pr_diff.txt \
    --max-lines 5000
"""
import argparse
import re
import sys
from pathlib import Path

CONTENT_PATTERNS = [
    r"^content/",        # Hugo/CMS ブログ記事・コンテンツ
    r"^static/images/",  # 画像ファイルのプレースホルダー
    r"^public/",         # Hugo ビルド成果物
]


def filter_diff(input_path: str, output_path: str, max_lines: int) -> None:
    full_diff = Path(input_path).read_text(errors="replace")
    total_lines = full_diff.count("\n")

    print(f"差分合計: {total_lines} 行")

    if total_lines <= 3000:
        Path(output_path).write_text(full_diff)
        print("3000行以内のためそのまま使用")
        return

    print("3000行超 → コンテンツファイルを除外して再構成")

    sections = re.split(r"(?=^diff --git )", full_diff, flags=re.MULTILINE)

    code_parts = []
    excluded = []

    for section in sections:
        if not section.strip():
            continue
        m = re.match(r"diff --git a/(.+?) b/", section)
        if not m:
            code_parts.append(section)
            continue
        filepath = m.group(1)
        if any(re.match(p, filepath) for p in CONTENT_PATTERNS):
            excluded.append(filepath)
        else:
            code_parts.append(section)

    code_diff = "".join(code_parts)
    code_lines = code_diff.count("\n")

    note = ""
    if excluded:
        file_list = "\n".join(f"  - {f}" for f in excluded[:30])
        if len(excluded) > 30:
            file_list += f"\n  ...他 {len(excluded) - 30} 件"
        note = (
            f"---\n"
            f"📋 レビュー対象外（コンテンツファイル {len(excluded)} 件・コードレビュー不要のため除外）\n"
            f"{file_list}\n"
            f"---\n\n"
        )

    print(f"コードファイル差分: {code_lines} 行 / 除外コンテンツ: {len(excluded)} 件")

    final = note + code_diff
    if code_lines > max_lines:
        lines = final.splitlines()[:max_lines]
        lines.append(f"（コードファイルのみで{max_lines}行超のため以降省略）")
        final = "\n".join(lines)
        print(f"警告: コードファイルのみでも{max_lines}行超 → 先頭{max_lines}行に切り詰め")

    Path(output_path).write_text(final)
    print(f"差分ファイル生成完了: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/tmp/pr_diff_full.txt")
    parser.add_argument("--output", default="/tmp/pr_diff.txt")
    parser.add_argument("--max-lines", type=int, default=5000)
    args = parser.parse_args()
    filter_diff(args.input, args.output, args.max_lines)


if __name__ == "__main__":
    main()
