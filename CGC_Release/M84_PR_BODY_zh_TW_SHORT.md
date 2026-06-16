# M8.4 PR 內文（中文短版）

## PR Title

`補齊 M8.4 三平台 release dist、manifest 與 package size gate`

## PR Body

```md
## 摘要

本 PR 將 `M8.4` 從「僅驗證當前主機 `cgc build` 可執行」升級為「正式 release productization gate」。

## 主要變更

- 新增三平台 `windows` / `macos` / `linux` build matrix 驗收
- 新增 `build_matrix_manifest.json` 與 `CGC_Release/dist/{windows,macos,linux}` 收斂驗收
- 將 package size 升級為 `soft target / hard limit / warning-fail` 兩段式規格
- 補齊 GitHub Actions / Jenkins 的 release asset 收斂流程

## 驗收語義

`m84_cgc_build_release_acceptance` 現在要求同時通過：

- `cgc_build_release_contract`
- `build_matrix_contract`
- `build_dist_manifest_contract`
- `artifact_size_budget`
- `windows_artifact_size_budget`
- `macos_artifact_size_budget`
- `linux_artifact_size_budget`

## 驗證結果

- `macos` 單平台 smoke 可通過 size budget 驗收
- 缺少 `windows` / `linux` 時，matrix / dist manifest 會正確 `FAIL`

這表示 `M8.4` 已能拒絕不完整的三平台 release 證據，而不再只是單機 build 檢查。
```
