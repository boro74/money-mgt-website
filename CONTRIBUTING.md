# ブランチ戦略・コントリビューションガイド

## ブランチ構成

| ブランチ | 役割 | 直接 push |
|---|---|---|
| `main` | 本番環境（money-mgt.net） | ❌ 禁止（PR のみ） |
| `develop` | 本番投入前の確認環境 | ❌ 禁止（PR のみ） |
| `feature/*` | コンテンツ追加・デザイン変更 | ✅ OK |
| `hotfix/*` | 本番緊急修正 | ✅ OK |

## 命名規則

```
feature/add-kfsc-partnership-page
feature/update-service-description
hotfix/broken-nav-link
hotfix/ogp-image-missing
```

## 通常フロー

```
develop → feature/xxx （develop からブランチを切る）
feature/xxx → develop  PR 作成（確認環境でチェック後 L2 マージ）
develop → main         PR 作成（L3: 代表承認必須）
```

コンテンツ更新など小規模な変更は `develop` へ直接 commit でもよい（feature ブランチは任意）。

## 本番障害フロー（hotfix）

```
main → hotfix/xxx
hotfix/xxx → main     PR 作成（L2 速攻レビュー → L3 デプロイ承認）
hotfix/xxx → develop  同時にバックポート（必須）
```

## 権限レベル（L1/L2/L3）

- **L1**: エージェント自律実行（feature ブランチへの commit・push）
- **L2**: ディレクター判断（feature → develop の PR マージ）
- **L3**: 代表承認必須（develop → main の PR マージ・本番デプロイ）

## PR 自動レビュー

`feature/*` または `hotfix/*` から `develop` または `main` への PR 作成時に Claude QA レビューが自動実行されます。

Hugo テンプレート・config・リンク切れ・機密情報混入の観点でチェックします。

- `P0` 検出: マージ前に修正必須
- `P1` 検出: 強く推奨
- `P2` 検出: 任意改善

## 注意事項

- `main` へのデプロイは `workflow_dispatch` のみ（自動 push トリガー禁止・L3）
- `develop` へのデプロイワークフローが必要な場合は別途追加すること
- Hugo submodule（テーマ）の更新は `git submodule update --remote` で行うこと
