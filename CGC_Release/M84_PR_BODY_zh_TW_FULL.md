# M8.4 PR 內文（中文完整版）

## PR Title

`補齊 M8.4 三平台 release dist、manifest 與 package size gate`

## PR Body

```md
## 摘要

本 PR 將 `M8.4` 從「僅驗證當前主機可執行 `cgc build`」升級為「可正式交付的 release productization gate」。

本次調整後，`M8.4` 不再只看單機 build 是否成功，而是同時驗證：

- `windows`、`macos`、`linux` 三平台真實 build 證據
- 聚合後的 `build_matrix.json`
- `CGC_Release/dist/{windows,macos,linux}` 正式收斂目錄
- `build_matrix_manifest.json`
- 每平台 package size 的 `soft target / hard limit / warning-fail` 規則
- GitHub Actions 與 Jenkins 的 release asset 收斂流程

## 變更重點

### 1. M8.4 驗收契約升級

`m84_cgc_build_release_acceptance` 現在包含以下組件：

- `cgc_build_release_contract`
- `build_matrix_contract`
- `build_dist_manifest_contract`
- `artifact_size_budget`
- `windows_artifact_size_budget`
- `macos_artifact_size_budget`
- `linux_artifact_size_budget`

### 2. Gate Runtime 能力補齊

- 在 `CGC_Release/m8_gate.py` 新增 `build_dist_manifest_contract`
- 將 `artifact_size_budget` 從單一硬上限升級為：
  - `PASS`：在 soft target 以內
  - `WARN`：超過 soft target，但未超過 hard limit
  - `FAIL`：超過 hard limit
- 在 gate 輸出中加入：
  - `budget_status`
  - `size_budget_level`
  - `executable_budget_level`

### 3. Release Dist / Asset 收斂

- 新增 `scripts/ci/collect_release_dist.py`
- 將三平台 build 產物收斂到：
  - `CGC_Release/dist/windows`
  - `CGC_Release/dist/macos`
  - `CGC_Release/dist/linux`
- 同時生成：
  - `CGC_Release/dist/build_matrix_manifest.json`
  - `CGC_Release/dist/release_assets/cgc-windows.zip`
  - `CGC_Release/dist/release_assets/cgc-macos.zip`
  - `CGC_Release/dist/release_assets/cgc-linux.tar.gz`

### 4. GitHub Actions / Jenkins 對齊

- 更新 `.github/workflows/m84-build-matrix.yml`
- 更新 `Jenkinsfile`
- 新流程已覆蓋：
  - 下載三平台 report
  - 下載三平台 build outputs
  - 聚合 `build_matrix.json`
  - 收斂 release dist
  - 執行 `M8.4-only` gate
  - tag build 時自動發佈 release assets

## 驗證結果

本地 smoke 驗證結果如下：

- `macos` 單平台 size budget 驗收可通過
- 缺少 `windows` / `linux` 時，`build_matrix_contract` 會正確 `FAIL`
- dist / asset 證據不完整時，`build_dist_manifest_contract` 會正確 `FAIL`

這代表 `M8.4` 已從「只檢查 build 指令存在」升級為「能拒絕不完整三平台 release 證據」的正式 gate。

## 影響檔案

- `CGC_Release/m8_gate.yaml`
- `CGC_Release/m8_gate.py`
- `scripts/ci/render_m84_gate_config.py`
- `scripts/ci/collect_release_dist.py`
- `.github/workflows/m84-build-matrix.yml`
- `Jenkinsfile`

## 補充說明

- `M8.4 PASS` 現在必須依賴真實 CI 產出的 `windows` / `macos` / `linux` 三平台 artifacts
- 單機 smoke 可以驗證 gate 邏輯與失敗語義，但不能取代正式三平台 release 證據
```
