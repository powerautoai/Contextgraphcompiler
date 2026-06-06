# CGC M7.3 物理具身智能一体化底座・最终验收方案 (v1.0)

## 1. 核心定位 (云端训练 + 端侧推理 Bridge)

M7.3 专为 **物理世界具身智能 (Robotics)** 设计。与数字世界的 GUI Agent (M7.2) 不同，物理机器人的操作具有极高的动态性与实时性要求。

*   **严禁端侧训练**：物理机器人的端侧（如鸿蒙 PC 或工控机）算力与内存有限，不应在端侧进行繁重的训练微调任务。
*   **模型选型 (云端)**：**严禁使用 7B 级别大模型**作为动作输出层。必须在 **云端 (Cloud)** 使用轻量级的 **Psi-Zero (Ψ₀) Action Expert** 进行高效的 L1 动态轨迹编译与 SFT/RLHF 微调。
*   **端侧推理桥接 (Bridge) 与 TrueOrthoKDA**：云端完成模型微调后，通过专属 **Bridge** 机制（静态计算图导出、权重静态量化），将模型下发至端侧，实现毫无 Python Overhead 的毫秒级极速推理。且所有端侧部署强制绑定 TrueOrthoKDA 一致性策略，确保与云端效能对齐。

## 2. 数据与模型存储规范

*   **云端训练数据路径**：AgiBot-World 等物理轨迹数据集统一存放于云端服务器的 `/root/cgc-engine/embodied/data/agibot_world/` 目录。
*   **云端训练 Checkpoint**：Psi-Zero 在云端微调后产出的模型权重 (safetensors) 与优化器状态，保存于云端的 `/root/cgc-engine/embodied/checkpoints/psi_zero_sft/`。
*   **端侧推理模型路径**：通过 Bridge 机制导出的静态计算图与量化权重 (GGUF/ORT Bundle)，下发并部署于端侧 (鸿蒙 PC 或工控机) 的 `~/.cgc_engine/edge_models/psi_zero_bridge/` 目录。

## 3. 物理轨迹数据与环境配置

*   **物理轨迹数据**：严格使用 **AgiBot-World** 等真实机器人的物理轨迹数据 (包含 10~50Hz 的 6D 位姿、RGB-D，且必须是第一人称头眼相机)，彻底消除 Embodiment Gap（具身差异）。
*   **训练环境**：云端 Linux 服务器 (A/B 源)，不受桌面 GUI 环境限制，专注于 Tensor 级的高速吞吐与编译。

## 4. M7.3 官方验收指标 (Gate)

*   **云端 Psi-Zero 动态轨迹编译 L1**
    *   编译成功率 = 100%
    *   缓存命中率 ≥ 2/3 (0.6667)
*   **端侧推理桥接 (Bridge)**
    *   Bridge 导出成功率 = 100%
    *   端侧推理延迟 ≤ 20ms
*   **物理轨迹状态压缩**
    *   压缩比 ≤ 0.6
    *   还原一致性 = 100%
*   **全链路工业审计**
    *   6D 轨迹事件完整率 = 100%
    *   哈希链 (Hash Chain) 校验 = 100%

## 5. 验收配置 (m73_gate.yaml)

```yaml
name: "CGC_M7.3_Physical_Embodiment_Gate"
description: "M7.3 物理具身智能 Psi-Zero 云端训练与端侧推理桥接 验收标准"
version: "1.0-final"

metrics:
  - name: cloud_training_psi0
    description: "云端 Psi-Zero 动态轨迹编译 L1 训练"
    rules:
      - metric: compile_success_rate
        operator: ">="
        threshold: 1.0
      - metric: cache_hit_rate
        operator: ">="
        threshold: 0.6667

  - name: edge_inference_bridge
    description: "端侧推理 Bridge (云端训练后下发至端侧)"
    rules:
      - metric: bridge_export_success
        operator: "=="
        threshold: 1.0
      - metric: edge_latency_ms
        operator: "<="
        threshold: 20.0

  - name: state_compression
    description: "物理轨迹全量状态压缩与去重"
    rules:
      - metric: compression_ratio
        operator: "<="
        threshold: 0.6
      - metric: restore_consistency
        operator: "=="
        threshold: 1.0

  - name: industrial_audit
    description: "全链路 6D 轨迹 Hash Chain 审计"
    rules:
      - metric: event_integrity
        operator: "=="
        threshold: 1.0
      - metric: hash_chain_valid
        operator: "=="
        threshold: 1.0

output:
  format: ["json", "html"]
  report_file: "report_m73.json"
  pass_fail_strategy: "all_must_pass"
```

## 6. 验收命令

**执行云端训练与 Bridge 下发**
```bash
python cgc_engine/train/agibot_sft_runner.py
```

**触发 M7.3 Gate 自动化评测**
```bash
python run_m73_eval.py report_m73.json m73_gate.yaml
```