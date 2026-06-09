# money-mgt.net 静的サイト（Hugo）

money-mgt.net の静的ページ（トップ・FPマイポータルLP・法人向け・就職副業）を Hugo で管理するリポジトリ。

## 構成

```
content/
  _index.md          # トップページ
  fp-myportal/
    _index.md        # FPマイポータル専用LP
  business/
    _index.md        # 法人・FP向けサービス
  junior-emp/
    _index.md        # 就職・副業支援
  contact/
    _index.md        # お問い合わせ
themes/
  PaperMod/          # Hugo テーマ（git submodule）
.github/workflows/
  deploy.yml         # Hugo ビルド → LOLIPOP FTP デプロイ
```

## デプロイ

`main` ブランチに push すると GitHub Actions が自動でビルド＆FTPデプロイします。

### 必要な GitHub Secrets

| Secret名 | 値の例 | 説明 |
|---------|--------|------|
| `FTP_SERVER` | `ftp.lolipop.jp` | LOLIPOP FTPサーバー |
| `FTP_USERNAME` | `abc.def@lolipop.jp` | FTPユーザー名 |
| `FTP_PASSWORD` | （パスワード） | FTPパスワード |
| `FTP_SERVER_DIR` | `web/` | デプロイ先ディレクトリ（⚠️ `web/` のみ。絶対パス不可） |

> **⚠️ 重要**: `FTP_SERVER_DIR` は `web/` と設定してください。
> LOLIPOPのFTPルートは `/home/users/0/.../` で、Webサイトのルートは `web/` ディレクトリです。
> `web/web/` にデプロイされる誤爆を防ぐため、`/home/users/.../web/` のような絶対パスは使用しないでください。

### ブログ（WordPress）について

`/blog/` は WordPress のまま運用します。GitHub Actions の exclude 設定で WordPress ファイルは上書きされません。

## ローカル開発

```bash
# 初回
git clone --recurse-submodules https://github.com/boro74/money-mgt-website
cd money-mgt-website

# Hugo 起動
hugo server --buildDrafts

# ブラウザで http://localhost:1313/ を確認
```

## テーマのアップデート

```bash
git submodule update --remote themes/PaperMod
git add themes/PaperMod
git commit -m "chore: PaperMod テーマをアップデート"
```
