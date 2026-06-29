"""
Claudeの出力（stdin）からREVIEW_COMMENTとQA_RESULTを抽出する。
- /tmp/review_body.txt : PRコメント本文（なければ空ファイル）
- /tmp/qa_result.json : {"max_severity": "...", "issues_text": "..."} （なければ書き出さない）
"""
import sys
import re
import json

text = sys.stdin.read()

m_review = re.search(r"REVIEW_COMMENT_START\n(.*?)\nREVIEW_COMMENT_END", text, re.DOTALL)
review_body = m_review.group(1)[:2000] if m_review else ""
with open("/tmp/review_body.txt", "w") as f:
    f.write(review_body)

m_qa = re.search(r"QA_RESULT_START\n(.*?)\nQA_RESULT_END", text, re.DOTALL)
if m_qa:
    try:
        data = json.loads(m_qa.group(1).strip())
        with open("/tmp/qa_result.json", "w") as f:
            json.dump(data, f)
        print("qa_result.json 書き出し完了")
    except Exception as e:
        print(f"JSON解析失敗: {e}", file=sys.stderr)
else:
    print("QA_RESULT_START/END マーカーが見つかりません", file=sys.stderr)
