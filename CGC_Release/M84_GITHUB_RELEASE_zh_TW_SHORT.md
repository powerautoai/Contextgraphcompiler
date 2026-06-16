# M8.4 GitHub Release 中文版說明（短版）

## Release Title

`M8.4 三平台 Release Build、Dist Manifest 與 Package Size Gate`

## Release Notes

```md
## M8.4 三平台 Release Build、Dist Manifest 與 Package Size Gate

本版本將 `M8.4` 從單機 `cgc build` 檢查，升級為正式三平台 release gate。

### 本版重點

- 驗收 `windows` / `macos` / `linux` 三平台 build matrix
- 驗收 `build_matrix.json` 與 `build_matrix_manifest.json`
- 收斂 `CGC_Release/dist/{windows,macos,linux}`
- 發佈 `release_assets`
- 將 package size 升級為 `soft target / hard limit / warning-fail`

### 正式語義

`m84_cgc_build_release_acceptance` 現在必須同時通過：

- `cgc_build_release_contract`
- `build_matrix_contract`
- `build_dist_manifest_contract`
- `artifact_size_budget`
- `windows_artifact_size_budget`
- `macos_artifact_size_budget`
- `linux_artifact_size_budget`

### 補充說明

- 單機 smoke 可驗邏輯
- 完整 `PASS` 仍需 CI 產出三平台真實 artifacts
```
