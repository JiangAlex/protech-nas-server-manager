# Versioning Convention

本專案採用 **Semantic Versioning (SemVer)** 搭配 git commit hash 作為版本識別。

## 版本格式

```
v MAJOR.MINOR.PATCH - <short-commit-hash>

範例：v1.2.3-abc1234
```

## 版本號定義

| 位置 | 名稱 | 何時遞增 | 範例 |
|------|------|----------|------|
| 1 | **MAJOR** | 有不相容的 API 變更（breaking change） | 資料庫 schema 大改、API endpoint 移除 |
| 2 | **MINOR** | 新增功能，但向下相容 | 加了新的通知通道、新增 API endpoint |
| 3 | **PATCH** | 修 bug、小修正，向下相容 | 修正推送失敗的 bug、typo 修正 |

## 實際舉例

- `v1.0.0` → 初始正式版本
- `v1.1.0` → 新增 Discord 通知通道（新功能）
- `v1.1.1` → 修正 Telegram 通知送不出去的 bug
- `v1.2.0` → 新增批次 rollback 功能
- `v2.0.0` → 資料庫從 SQLite 改為 PostgreSQL（breaking change，舊資料需 migration）

## Git Commit Hash

```
v1.2.3-abc1234
       └─ 短 hash（7 碼），精確對應到哪個 commit
```

用途：即使同一個版本號在開發過程中有多次 build，也能精確追溯到原始碼的確切位置。特別適合管理多台 NAS 時確認每台跑的到底是哪個版本。

## 參考

- [Semantic Versioning 2.0.0](https://semver.org/)
