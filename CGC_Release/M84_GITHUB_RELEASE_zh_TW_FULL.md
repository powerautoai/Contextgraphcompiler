# M8.4 GitHub Release 中文版說明（完整版）

## Release Title

`M8.4 三平台 Release Build、Dist Manifest 與 Package Size Gate`

## Release Notes

```md
## M8.4 三平台 Release Build、Dist Manifest 與 Package Size Gate

本版本將 `M8.4` 從「只驗證當前主機可執行 `cgc build`」正式升級為「可交付、可發佈、可在 CI/產線被驗收的 release gate」。

### 本版重點

- 補齊 `windows` / `macos` / `linux` 三平台真實 build matrix 驗收
- 補齊 `build_matrix.json` 聚合驗收
- 補齊 `CGC_Release/dist/{windows,macos,linux}` 正式收斂目錄
- 補齊 `build_matrix_manifest.json`
- 補齊 `release_assets` 產物收斂與發佈流程
- 將 package size 升級為 `soft target / hard limit / warning-fail` 正式產品規格

### 正式驗收語義

`m84_cgc_build_release_acceptance` 現在要求同時滿足：

- `cgc_build_release_contract`
- `build_matrix_contract`
- `build_dist_manifest_contract`
- `artifact_size_budget`
- `windows_artifact_size_budget`
- `macos_artifact_size_budget`
- `linux_artifact_size_budget`

### Release 產物

CI 成功後，三平台產物會收斂到：

- `CGC_Release/dist/windows`
- `CGC_Release/dist/macos`
- `CGC_Release/dist/linux`
- `CGC_Release/dist/build_matrix_manifest.json`
- `CGC_Release/dist/release_assets/cgc-windows.zip`
- `CGC_Release/dist/release_assets/cgc-macos.zip`
- `CGC_Release/dist/release_assets/cgc-linux.tar.gz`

### 這代表什麼

`M8.4 PASS` 現在不再表示：

- 某台機器上曾經成功跑過一次 `cgc build`

而是表示：

- host build 證據成立
- 三平台 matrix 證據齊全
- dist 收斂證據齊全
- release asset 證據齊全
- package size 符合正式產品規格

### 補充說明

- 單機 smoke 可驗證邏輯與 FAIL 語義
- 真正完整 `PASS` 仍需 CI runner 產出 `windows` / `macos` / `linux` 三平台真實 artifacts
```
