# CGC M7.1/M7.2 工業審計與狀態回溯 教學指南

本指南說明如何透過 CGC Engine CLI 進行「可審計」與「可回溯」操作。

## 1. 可審計 (Auditable)
M7 具備 6 段式 Hash Chain 留痕。您可以隨時利用 CLI 驗證整個執行過程是否被竄改。

**驗證命令：**
```bash
python cgc_engine/agent/cli.py audit verify \
    --log <path_to_report_dir>/audit/events.jsonl \
    --head <path_to_report_dir>/audit/chain_head.json
```

**成功輸出：**
```text
[*] 驗證 Hash Chain: .../events.jsonl 與 .../chain_head.json
✅ Hash Chain 驗證通過，所有事件未被竄改。
```

## 2. 可回溯 (Traceable)
透過 CLI，您可以回放與追蹤特定階段 (如 `state`, `run`, `compile`) 的詳細資料。如果該階段包含了「全量狀態壓縮」，系統會提示您這是一筆可解壓縮還原的狀態快照。

**回溯命令：**
```bash
python cgc_engine/agent/cli.py audit trace \
    --log <path_to_report_dir>/audit/events.jsonl \
    --stage state
```

**輸出範例：**
```text
[*] 回溯日誌 (state): .../events.jsonl

[Event Hash: 5f1b...c3a9]
{
  "compressed_bytes": 128,
  "dedup": {
    "bytes_added": 128,
    "unique_chunks": 1,
    "writes": 1
  },
  "ratio": 0.134,
  "raw_bytes": 953,
  "restore_ok": true
}
  -> 發現壓縮狀態，可透過 StateCompressor.decompress 還原。
```

## 3. 長時間 GUI 測試 (如執行一小時)
若要模擬真實的長時間工作流 (例如一小時的 OA 記錄測試)，您可以使用更新後的 Eko-Agent 腳本，透過 `--duration` 參數設定秒數 (1小時 = 3600秒)。

**執行命令：**
```bash
python cgc_engine/agent/eval/eko_gui_agent_demo.py --duration 3600
```
> **注意**：這將會佔用您的實體桌面環境 1 小時，腳本會自動打開記事本，每隔 10 秒打字記錄當前時間與狀態，並在結束後自動不儲存關閉，最後觸發 CGC 的驗收與審計。中途可隨時按下 `Ctrl+C` 提早結束並結算。
