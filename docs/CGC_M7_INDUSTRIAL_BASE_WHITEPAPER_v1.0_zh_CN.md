# CGC M7 工業級一體化底座技術白皮書

**版本**: v1.0
**狀態**: 官方固化版本
**目標場景**: 鴻蒙PC、AI PC、政企商用場景最穩、最合理、可100%量產達標的工業級驗收標準。

---

## 一、升級目標：M7 工業級一體化底座
為統一開發、測試、商務、對接華為鴻蒙PC/緯創/聯想政企標案，定義 M7 最小工業級驗收門檻，所有指標可自動化落地、可程式判斷、可輸出標準化 `report.json`。

### 1. 動態軌跡編譯（Dynamic Trace Compile）｜最小驗收規範
**選定等級：L1**（產業落地最穩、兼容所有AI PC、可快速達標）

**覆蓋範圍定義（L1）**
- 支援：輸入 Shape 動態變化（Batch / SeqLen 浮動）
- 限制：Control-Flow 固定、無隨機分支
- 適配：100% 企業標準工作流、辦公Agent、工廠標準流程、文檔處理場景

**最小可驗收指標**
- 同一模型/計算圖，3組不同動態 Shape 場景
- 編譯成功率 = 100%
- 編譯產生圖緩存命中率 ≥ 67%（2/3）
- 推理一致性：相同輸入兩次重跑輸出 Hash 完全一致 = 100%

**標準證據輸出（寫入 report.json）**
- `compile_variants[]`：`shape_sig`, `graph_hash`, `compile_ms`, `cache_hit`, `status`
- `correctness[]`：`input_hash`, `output_hash`, `repeat_consistent` (bool)

### 2. 全量狀態壓縮（Full-State Compression）｜最小驗收規範
**選定門檻：壓縮比 ≤ 0.6**

**最小狀態覆蓋欄位**
- 模型版本ID、編譯產物ID、推理硬件Provider、輸入摘要、輸出摘要、KV緩存快照指標

**可驗收指標**
- 壓縮比：壓縮後容量 / 原始容量 ≤ 0.6
- 還原一致性：Restore 還原後輸出 Hash 與原始完全一致 = 100%
- 重複去重：同一狀態連續寫入10次，增量存儲膨脹 ≤ 1.2倍（允許索引開銷）

**標準證據輸出**
- `state.raw_bytes`, `state.compressed_bytes`, `state.ratio`
- `state.restore_ok` (bool)
- `state.dedup`：寫入次數、唯一塊數、增量容量

### 3. 毫秒級實時回放（Real-Time Replay）｜最小驗收規範
**最終定義：Soft-RT**（商用PC/鴻蒙PC真實可落地）
說明：消費級/商用PC系統無硬實時內核權限，不強制 Hard-RT，避免無法達標、無法量產。

**選定門檻：Deadline = 10ms**

**可驗收指標**
- 單次回放 Deadline：10ms
- 抖動控制：P99 ≤ 10ms、P999 ≤ 15ms（1.5倍門檻）
- 超時丟幀率：Miss Rate ≤ 0.1%
- 有效測試：連續穩定回放 ≥ 10000 次 Workload

**標準證據輸出**
- `replay.deadline_ms`, `replay.total_count`
- latency 分位數：`p50`, `p90`, `p99`, `p999`, `max`
- `replay.miss_rate`
- `replay.mode`：`soft_rt`（官方標註、真實落地）

### 4. 全鏈路工業審計一體化｜最小驗收規範
實現 Build / Compile / Run / State / Replay / Exception 六段式全鏈路留痕。

**最小必備審計事件清單**
- **Build**：依賴版本、輸入Artifact Hash、輸出Artifact Hash
- **Compile**：計算圖Hash、編譯器版本、編譯參數、產物Hash
- **Run**：模型版本、推理設備、輸入Hash、輸出Hash、資源上限（显存/內存/磁盤）
- **State**：狀態讀寫、壓縮比、去重結果、還原校驗結果
- **Replay**：延遲分佈、超時統計、環境指紋
- **Exception**：異常棧、觸發節點、恢復結果

**不可抵賴鏈式證據（工業級標準）**
- 每筆事件標準 JSON 規範序列化 → SHA256 單筆 Event Hash
- 鏈式哈希串接：`ChainHash(i) = SHA256(ChainHash(i-1) + EventHash(i))`
- 固定輸出：`audit/events.jsonl` + `audit/chain_head.json`

**驗收門檻**
- 事件完整率 = 100%
- 鏈式哈希可完整復算、一致性校驗通過 = 100%
- `audit.verify_ok = true`

---

## 三、M7 整體 Gate 最終 PASS/FAIL 規則（自動化驗收標準）
必須同時滿足全部條件才算 M7 工業級底座達標：

- `dynamic_trace.status == PASS`
- `state_compression.status == PASS`
- `replay.status == PASS`（標註 soft_rt、不造假硬實時）
- `audit.status == PASS`
- **雙軌嚴格防偽驗收 (Dual-Track Strict Fingerprint Gate) 通過**：
  - **本機端 (macOS)**：強制設定 `CGC_REQUIRE_MLX=1`，綁定 MLX 驗收，跳過 CUDA 特定檢查。
  - **雲端 (Linux)**：強制設定 `CGC_REQUIRE_CUDA=1` 搭配 `CGC_BACKEND_FINGERPRINT_LOCK`。必須與基準 `lock.json` 指紋完全一致，包含版本、路徑及 C 擴展（如 `vllm._C`）。任何不一致均立刻 Fail-Close 阻斷，嚴禁降級或 Mock。
- **一致性策略 (TrueOrthoKDA)**：所有 LLM Gate 強制要求啟用 TrueOrthoKDA（未開啟則直接判定 FAIL），確保跨後端的效能與精度口徑完全一致。
- `report.json.gate_result.m7.status == PASS`
