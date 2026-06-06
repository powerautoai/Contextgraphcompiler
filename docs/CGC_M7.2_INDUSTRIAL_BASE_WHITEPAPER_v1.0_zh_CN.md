# M7.2 工业级一体化底座・最终验收方案

## 整体定位 (雙軌架構)

CGC M7.2 具備**雙軌 (Dual-Track) 具身智能與自動化**架構，涵蓋了數位世界的桌面 GUI Agent 與實體物理世界的機器人軌跡，兩者皆基於 CGC Engine 構建 **可审计、可回溯、可预编译、软实时、状态压缩** 的端到端自动化验收体系。不依赖外部闭源服务，全部基于开源栈 + CGC 自研内核，可一键跑通、输出标准 `report.json`。

### Track A: 數位世界 GUI Agent (鸿蒙 PC / 政企桌面)
*   **基準模型選型**：`UI-TARS-2B` (≥6GB 記憶體主力)、`Phi-3-Vision` (≤4GB 記憶體低配)
*   **測試集**：OSWorld (跨平台作業系統級軌跡)
*   **環境限制声明**：M7.2 的 GUI 验收体系严禁使用 Mock。真实的 GUI 执行用例必须在具备 **真实桌面环境（如 macOS, Windows 或带桌面系统的 鸿蒙 PC/AI PC）** 的实体机上运行。由于云端 Linux 服务器通常为 Headless（无显示设备）状态，默认无法执行完整的 GUI 自动化测试。

### Track B: 物理世界具身智能 (Robotics)
*   **基準模型選型**：Psi-Zero Action Expert (以輕量級 LLM/VLM 為骨幹微調)
*   **測試集**：AgiBot-World (智元機器人實體搬運、拆碼垛等 6D 位姿物理軌跡)
*   **環境支援**：物理軌跡為純數值/影像 Tensor，不受桌面環境限制，**可完美於雲端 Linux 伺服器進行 L1 動態編譯、微調與 M7.2 審計驗收**。

## 1. 整体架构（优化版，极简且强闭环）

*   **执行层**：
    **Eko-Agent + PyAutoGUI**（鸿蒙 PC/Windows 桌面 GUI 自动化）
    执行基础的系统 GUI 交互（例如：打开计算器、输入文字等），用于产生真实的第一视角动作轨迹。
*   **内核层（CGC 自研 M7.1）**：
    *   `ort_state/compression.py`：全量状态压缩（目标≤0.6）+ 去重 + 100% 还原
    *   `audit/chain.py`：全链路 6 段式审计 + JSON 规范化序列化 + Hash Chain 不可抵赖
    *   Pipeline 动态轨迹编译 L1（shape 动态 + 固定 control-flow）
    *   Soft-RT 回放（10ms deadline，p99≤10ms）
*   **评测 Gate 层（AgentEval 标准）**：
    固定 YAML 配置 → 读取 CGC 原生 `report.json` → 自动判定 PASS/FAIL → 输出标准化报告
*   **環境防伪與嚴格驗收（Strict Fingerprint Gate & Consistency）**：
    为了避免环境依赖变动、Backend 库被覆盖导致 Fallback/Simulated 执行，M7.2 强制导入硬件感知的双轨防伪验证，以及跨后端一致性策略：
    1. **本机端 (macOS)**：通过设置 `CGC_REQUIRE_MLX=1`，强制绑定 MLX Backend 进行验收。系统会自动侦测 `darwin` 平台并放行 MLX 测试，禁止 CUDA 相关的 `vllm._C` 验证。
    2. **云端 (Linux)**：强制开启 `CGC_REQUIRE_CUDA=1` 与指纹锁 `CGC_BACKEND_FINGERPRINT_LOCK=/path/to/lock.json`。流水线会严格比对 CUDA/vLLM/CGC_C++ 的版本、路径、二进制 Hash 等。
    3. **TrueOrthoKDA 一致性策略**：所有 LLM Gate 强制要求启用 TrueOrthoKDA (`--enable-ortho-kda`)。若未开启，将触发 Fail-Close，确保评估口径高度一致。
    4. **Headless 防伪**：若在无桌面显示的云端 Linux 运行 GUI 用例，脚本会自动跳过 PyAutoGUI 的虚假录制，直接触发底层审计验收，彻底杜绝 Mock 数据。
*   **入口层**：
    `run_m72_eval.py` 一键启动：GUI 用例 → CGC 执行 → 指标采集 → Gate 判定

**优势**： 完全自研闭环、无第三方依赖、可在鸿蒙 PC 裸跑、可进产线验收。

## 2. M7.2 官方验收指标（最终锁定版）

*   **动态轨迹编译 L1**
    *   编译成功率 = 100%
    *   缓存命中率 ≥ 2/3 (0.6667)
    *   重复执行输出 hash 一致性 = 100%
*   **全量状态压缩**
    *   压缩比 ≤ 0.6
    *   状态还原一致性 = 100%
    *   重复写入去重膨胀率 ≤ 1.2
*   **毫秒级软实时回放（Soft-RT）**
    *   回放 deadline = 10ms
    *   p99 延迟 ≤ 10ms
    *   丢帧 / 超时 miss rate ≤ 0.1%
*   **全链路工业审计 Hash Chain**
    *   6 大类事件完整率 = 100%
    *   哈希链校验通过 = 100%

## 3. 最终版 m72_gate.yaml（可直接入库）

```yaml
name: "CGC_M7.2_Industrial_Base_Gate"
description: "M7.2 工业级一体化底座 政企GUI Agent 自动验收标准"
version: "1.0-final"

metrics:
  - name: dynamic_trace_l1
    description: "动态轨迹编译 L1（shape动态 + 固定控制流）"
    rules:
      - metric: compile_success_rate
        operator: ">="
        threshold: 1.0
      - metric: cache_hit_rate
        operator: ">="
        threshold: 0.6667
      - metric: correctness_consistency
        operator: "=="
        threshold: 1.0

  - name: state_compression
    description: "全量状态压缩与去重"
    rules:
      - metric: compression_ratio
        operator: "<="
        threshold: 0.6
      - metric: restore_consistency
        operator: "=="
        threshold: 1.0
      - metric: dedup_expansion_ratio
        operator: "<="
        threshold: 1.2

  - name: soft_rt_replay
    description: "10ms软实时回放"
    rules:
      - metric: deadline_ms
        operator: "<="
        threshold: 10.0
      - metric: p99_latency_ms
        operator: "<="
        threshold: 10.0
      - metric: miss_rate
        operator: "<="
        threshold: 0.001

  - name: industrial_audit
    description: "全链路Hash Chain审计不可抵赖"
    rules:
      - metric: event_integrity
        operator: "=="
        threshold: 1.0
      - metric: hash_chain_valid
        operator: "=="
        threshold: 1.0

output:
  format: ["json", "html"]
  report_file: "report.json"
  pass_fail_strategy: "all_must_pass"
```

## 4. 验收命令

**运行**
```bash
python run_m72_eval.py <你的report.json> m72_gate.yaml
```

**输出示例**
```plaintext
========================================
  CGC_M7.2_Industrial_Base_Gate v1.0
========================================

▶ 动态轨迹编译 L1:  PASS
▶ 全量状态压缩:      PASS
▶ 软实时回放(10ms):  PASS
▶ 全链路审计Hash链:  PASS

========================================
最终 M7.2 Gate 验收结果: ✅ PASS
========================================
```

## 5. 这套方案为什么能直接用于鸿蒙 PC & 政企标案

1.  **真实对应政企最大需求**：GUI Agent 占比 60%+。
2.  **可审计、可回放、不可篡改** = 等保 / 合规 / 金融 / 国资强制要求。
3.  **压缩比、回放时延、审计完整性** = 可量化、可演示、可上 PPT。
4.  **全链路自动化** = 可成为鸿蒙 PC AI 能力的官方验收标准。
5.  **不依赖云、不依赖第三方** = 满足内网 / 信创 / 离线环境。
