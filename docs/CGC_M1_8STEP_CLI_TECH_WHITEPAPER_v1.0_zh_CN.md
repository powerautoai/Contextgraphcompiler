# CGC 八步流水线 / CLI 技术白皮书 v1.4（简体中文）

本文件路径沿用历史命名（文件名仍含 v1.0），内容版本以本文标题为准。

## v1.4 更新记录（相对 v1.3）

- 重构并定稿 M1–M5 的里程碑迭代顺序：M1 基座打底 → M2 推理内核与安全验收 → M3 模型固化与端侧落地 → M4 训练与分布式规模化 → M5 终态闭环。
- 将 M2“标准化四向 Gate（等价 / 内存 / PPL / 速度）”写成可直接入库的分层验收条款：明确 required contexts（2k/4k/8k/16k）、阈值、以及 report.json 的对齐字段。
- 增补“当前 M2 进展”章节：记录已验证通过项、已知阻塞项与复跑配置（不改变既有 schema，仅作为工程状态说明）。
- 增补 M4“oMLX+FlashMoE 双粒度按需加载 Gate（按 layer + 层内 expert）”：明确文件布局、CLI 开关与 report.json evidence 字段。
- 新增 M7“工业级一体化底座 Gate（动态轨迹编译 + 全量状态压缩 + 毫秒级软实时回放 + 全链路工业审计）”：固化最小可验收指标与 report.json PASS/FAIL 口径。

## v1.3 更新记录（相对 v1.2）

- 增补 M2~M5 “runtime gate + 自动回退 + 报告留痕” 的 MVP Contract，并与现有 8-step report 结构做零破坏性对齐（不改既有 key，仅新增字段）。
- 给出生产可用的精简 JSON Schema（Draft 2020-12），Schema 与示例完全一致，且兼容 `status` 与 `ok` 双语义。
- 明确与现有实现的兼容点：`step3_skvm_verify` 与 `step3_equivalence_gate` 在 report 中为顶层 step（可选），同时允许在 `step3_analyze` 中挂摘要信息。
- 统一枚举与别名兼容策略：保留 `fail_reason`（允许原始字符串），新增 `fail_reason_canonical`（严格枚举）用于入库聚合与线上一致性。
- 将端云协同推理（PD 分离 + 固定 KV + 存储加速）的可选场景内化到本白皮书：仅抽取与现有 8-step/产物契约兼容的通用部分，避免绑定特定硬件与平台假设。

## v1.2 更新记录（相对 v1.1）

- 整合 docs/ 下多份“架构/分类/8-step”原稿，将可复用内容收敛到本文件，并以“统一 8-step 契约 + 后端分流”重写章节结构。
- 将“推理（llama.cpp/vLLM/MLX 等）”与“训练/微调（megatrain/mlx-tune）”纳入同一条 8-step 验收闭环：同一 CLI 入口、同一 report.json 真源、同一产物索引方式。
- 固化 CUDA 侧 `megatrain/train` 的可验收闭环标准：必须产出可索引的编译缓存目录与 `.so`（必要时镜像到 run 目录），并在 report.json 中可直接定位。

---

## 0. 目标与范围

本白皮书定义“可验收闭环”的统一标准：对任一后端/任务，均应做到：

- 有确定的 CLI 命令可复现
- 有固定产物目录结构（cache/dumps/logs 可索引）
- 有一次真实 dispatch（实跑）
- 有 compare（对照或自检）
- 有 combine（输出汇总），最终落到单一真源 `report.json`

---

## 0.1 M1–M5 里程碑（重构版，最优工程节奏）

工程落地优先级：先“可用”（推理安全 + 可验收 + 可回退）→ 再“优秀”（可分发固化产物 + 端侧落地）→ 后“规模化”（训练 + 分布式 + AOT 终态闭环）。

### M1：Partition + Workspace + Tap/Dump（底层基座搭建）

- 核心产出：可分段执行的 runtime 调度框架；workspace 内存池化；图 dump 与 tensor tap 全量可观测能力。
- 阶段边界：不做模型结构/权重/KV 优化；不涉及训练/微调/分布式训练能力。

### M2：Attention 子图替换 + Copy/Sync 自动化 + 四向 Gate 验收（推理安全底座）

- 核心产出：Attention 子图全量替换为自研 KDA 内核；Copy/Sync 自动化调度；标准化四向 Gate（等价/内存/PPL/速度）+ 自动回退 + 报告留痕。
- 阶段边界：仅运行时生效（编译缓存/临时产物），不输出可离线分发的固化优化模型文件；不覆盖整图融合与训练链路。

### M3：Attention Block 整段替换 + KV 连续布局 + 整图融合 + 可分发模型产出（端侧落地）

- 核心产出：Transformer block 级替换与整图编排；全局 KV 连续布局（降低碎片与长上下文膨胀）；固化权重/KV 布局并导出可分发产物（增强 GGUF/CGC）。
- 目标画像：低配端侧设备可稳定运行（例如 8GB 内存 + 核显设备）。

### M4：RMSNorm + MLP 子图替换 + 权重布局优化 + 编译缓存持久化 + 训练/分布式能力（规模化训练）

- 核心产出：补齐 Transformer 全模块内核替换（norm/mlp）；权重 tile/align/layout 预处理；编译产物持久化缓存；单卡训练性能与多卡分布式训练能力落地。
- 训练侧入库 Gate：性能 Gate + 编译 Gate + 分布式 Gate（见后续章节）。

### M5：AOT 预编译 + 终极优化模型 + 训推闭环（技术终态）

- 核心产出：整图 AOT 预编译、彻底消除运行时编译；固化最优权重/KV 布局与内核 bundle；形成可复现的预训练/精调全流程闭环。

---

## 1. 统一架构（对齐最新八步流水线）

### 1.1 统一入口与分流

统一入口为 CLI 的 `pipeline` 子命令。逻辑上分为两条分流：

- 推理：`task_type=inference`（llama.cpp/vLLM/MLX 等推理后端）
- 训练/微调：`task_type=train|tune`（megatrain/mlx-tune），结果作为 `megatrain_8step` 挂回同一份 report

### 1.2 三层职责（概念对齐）

- 控制面（调度/路由）：决定任务类型、后端、策略与产物目录；不要求承载具体 kernel 实现细节
- 数据面（执行/计算）：执行实际算子（推理或训练），产出可复用的编译产物（如 inductor/triton artifacts）
- 资源面（缓存/存储）：统一管理 cache、dumps、报告汇总（以 run output_dir 为边界）

### 1.3 后端分类（用于路由与验收口径）

- llama.cpp：GGUF 推理（可选 ggml backend plugin）
- vLLM：CUDA 推理（torch.compile/inductor 产物）
- MLX：Apple Silicon 推理/调优（Metal/MLX runtime）
- megatrain：训练/微调闭环（以 torch.compile/inductor 为“编译产物”验收基线）

### 1.4 环境口径与指纹锁定（强制）

为避免“环境飘移导致假通过”，所有里程碑默认启用 backend 指纹 gate，并要求版本/路径一致（Fail-Close）：

- 端侧（macOS）：以 MLX-only 口径验收
  - 运行前置：`CGC_REQUIRE_MLX=1`
  - 强制条件：必须满足 Apple GPU（MPS/Metal）可用（`torch.backends.mps.is_available()==true`），且禁止使用 CUDA-only 后端（如 vLLM），否则直接 FAIL
- 云侧（Linux + CUDA）：以 CUDA-only 口径验收
  - 运行前置：`CGC_REQUIRE_CUDA=1`
  - 强制条件：C++/torch runtime 必须绑定 CUDA（禁止 CPU fallback），否则直接 FAIL
- 版本/路径锁定（必须）
  - 默认 `CGC_BACKEND_FINGERPRINT_LOCK_REQUIRED=1`，未设置 `CGC_BACKEND_FINGERPRINT_LOCK=/path/to/lock.json` 将直接 FAIL
  - 每次运行都会在 `output_dir/` 生成 `backend_fingerprint.lock.suggested.json`，用于沉淀并固化 lock 基线；后续所有验收必须绑定同一份 lock（不一致直接 FAIL）
- LLM gate 一致性策略（trueorthkda，Fail-Close）
  - 默认 `CGC_REQUIRE_TRUEORTHOKDA=1`
  - 当 `mode=llm` 且 `task_type in {inference, multimodal}` 且后端属于 `llama.cpp/vLLM/MLX` 时，必须开启 `--enable-ortho-kda`，否则直接 FAIL
  - 该条款用于统一“性能口径/结果一致性”，不构成“必然提速”保证
  - CLI 等价写法：`cgc pipeline --require-cuda/--require-mlx --fingerprint-lock /path/to/lock.json ...`（等价于设置对应环境变量）

---

## 2. 8-step 统一契约（可验收闭环）

统一 8-step 的语义如下（所有后端都要尽可能对齐这些输出字段；允许个别 step 标记为 SKIP，但必须给出 reason）：

- Step0 Scenario：写入分类信息（task_type/backend/task_domain/model_family/model_tag/hardware_profile）
- Step1 Hardware：检测 device 与 runtime 能力
- Step2 Capture：捕获可复现的图/配置快照（GGUF header / HF config / FX graph / train wrapper 等）
- Step3 Analyze：对捕获物做静态分析（图统计、shape/schema 统计等）
- Step4 Identify：确定需要生成/优化的目标（op_types/transform_spec/strategy）
- Step5 Generate：生成并落盘“可复用产物”（编译缓存、kernel 源码骨架、插件 dumps 等）
- Step6 Dispatch：至少一次真实运行（推理 prefill/decode 或训练 step）
- Step7 Compare：baseline vs optimized（或自检）输出对照结果
- Step8 Combine：把产物路径、关键指标汇总写入 report.json（单一真源）

---

## 3. Output 目录契约（单一真源）

每次 run 都应产生一个 `output_dir`，至少包含：

- `report.json`（单一真源）
- `train_tune_artifacts/` 或 `dump_dir/` 这类“可索引产物根目录”（随后端不同而不同）

约束：

- 后端插件（如 ggml-cgc）只输出碎片化产物，不写 report.json
- report.json 由 pipeline 汇总生成，且要能反向定位所有碎片化产物路径

### 3.1 M2~M5 MVP Contract（Gate / 回退 / 审计）与 8-step 对齐（零破坏扩展）

目标：把每次“子图替换 / 权重布局 / KV 布局 / AOT 编译”等优化，变成可控、可采样、可审计、可回退的线上能力。对齐原则如下：

- 不新增 report 顶层字段；只在现有 step 下追加子字段
- Schema 与示例完全一致，可直接用于自动校验与回归测试
- 同时兼容 `status: PASS|FAIL|SKIP` 与历史 `ok: true|false`
- `scope` 命名锁定：单点用 `block_index`，范围用 `block_range`

字段挂载位置（不改现有 key，仅新增）：

- Step2 Capture：记录替换单元、block 范围、node-range/partition 边界（用于稳定定位）
- Step3 Analyze：记录 Gate 计划（stage/采样率/阈值/fail budget）；允许挂 `skvm_verify` 摘要
- Step6 Dispatch：记录实际执行路径、是否 fallback、fallback 原因（runtime 事实）
- Step7 Compare：记录数值等价、性能、topk 一致性、Gate 最终结果（可审计）
- Step8 Combine：记录上线决策、回退计划 ID、所有产物 hash 索引（单一真源）
- `megatrain_8step`：训练/微调侧复用完全相同结构，统一 schema（挂在 `steps.megatrain_8step.*`）

兼容点（与现有实现一致）：

- `step3_skvm_verify` 与 `step3_equivalence_gate` 在 report 中为顶层 step（可选），同时允许在 `step3_analyze` 下挂摘要字段（例如 `step3_analyze.skvm_verify`），以便统一分析视图与兼容现有输出。

### 3.1.1 M2 四向 Gate（正式入库标准，分层验收条款）

M2 目标：在“数值等价 + 内存可控 + 语义无损 + 性能合规”的前提下启用 KDA 推理内核；任何不满足条件的情形必须自动回退并可审计。

#### 1) 等价 Gate（数值安全底线）

- 硬性准入：`steps.step3_equivalence_gate.status == "PASS"`（不得为 SKIP/FAIL）。
- 指标留痕：在 `steps.step7_compare.*` 下产出 `max_abs_err / max_rel_err`（或等价的 per-output 统计）。
- 运行路径要求：`steps.step6_dispatch.exec.fallback.triggered == false`（不允许默认回退兜底后仍宣称通过）。

#### 2) 内存 Gate（长上下文安全壁垒）

- 覆盖上下文：必须包含 2k / 4k / 8k / 16k（对应 `required_contexts` 为 `[2048, 4096, 8192, 16384]`）。
- 阈值：`optimized.peak_memory_gb / baseline.peak_memory_gb <= ratio_limit`（默认 ratio_limit=2.0）。
- 防“微小基线”误判：当 baseline 过小，需满足 `delta_min_gb`（例如 0.05GB）后才计入判定（以 gate 输出字段为准）。

#### 3) PPL Gate（语义能力无退化）

- 基准：标准 WikiText2（`steps.step7_compare.gate_result.ppl_gate.corpus.test == "wikitext2"`）。
- 阈值：`delta_max <= 0.1` 且 `ratio_max <= 1.02`（以 gate 输出字段为准）。
- 可靠性：baseline 与 optimized 都必须在 timeout 内成功跑完（不得出现 timeout / crash / missing corpus）。

#### 4) 速度 Gate（推理性能合规）

- 覆盖上下文：必须包含 2k / 4k / 8k / 16k。
- 阈值：`prefill_ratio_min >= 1.0` 且 `decode_ratio_min >= 1.0`（以 gate 输出字段为准）。
- 备注：速度 Gate 以“同 runner / 同 commit / 同参数”的 baseline vs optimized 对照为前提，否则不具可比性。

### 3.1.2 当前 M2 进展（截至 2026-05-31）

- 已通过：等价 Gate（`step3_equivalence_gate: PASS`），且已确认 attention 替换范围为全层 block_range `[0, n_layers-1]`（以 Step2 Capture 为准）。
- 已识别问题（上一轮）：contexts 缺少 16k 导致 memory/speed gate 以 `missing_required_contexts` 失败；PPL（WikiText2）在 baseline 路径上出现 timeout（需要更长 timeout 或更小 batch）。
- 复跑策略（进行中）：补齐 16k contexts；将 `CGC_LLAMA_PPL_TIMEOUT_S` 拉长并降低 `CGC_M2_PPL_BATCH_SIZE`，以确保 baseline/optimized PPL 都能稳定产出后再做 delta 判定。

### 3.1.3 M4 三向 Gate（正式入库标准，训练/分布式验收条款）

M4 目标：补齐 Transformer 全模块优化与编译工程底座，并形成可规模化训练的“单卡性能 + 编译产物 + 分布式”闭环验收。

#### 1) 性能 Gate（单卡训练性能）

- 验收对象：`steps.megatrain_8step.step7_compare`（或等价挂载位置）。
- 指标：训练吞吐（samples/s 或 tokens/s）、step time、MFU 等；需明确 baseline（例如 DeepSpeed ZeRO-3）与 optimized（MegaTrain）对照来源。
- 门槛：在同等硬件/模型/超参前提下，optimized 训练速度应达到预设倍率门槛（例如 ≥ 1.84x），且训练过程无 OOM/抖动/异常回退。

#### 2) 编译 Gate（工程底座与可复用产物）

- 验收对象：`steps.megatrain_8step.step5_generate` 与 `steps.megatrain_8step.step8_combine`。
- 门槛：必须产出可索引的编译缓存目录与关键产物（例如 `.so/.dylib/.ptx` 或等价 bundle），并能在 report.json 中反向定位到路径与 hash（用于入库聚合与审计）。

#### 3) 分布式 Gate（多卡规模化能力）

- 验收对象：`steps.megatrain_8step.step6_dispatch` 与 `steps.megatrain_8step.step7_compare`。
- 门槛：支持 DP/TP/PP 等组合并行的可复现启动方式；训练过程稳定、通信开销可控、负载均衡合理，并能在 report.json 中记录并行策略与关键日志/产物索引。

#### 4) oMLX+FlashMoE 双粒度按需加载 Gate（端侧超内存兜底，M4 可选硬门槛）

M4 目标之一是保证“当 MoE 权重规模超出端侧内存预算”时，仍能通过 oMLX+FlashMoE 做可验收的按需加载落地。双粒度含义：

- 层粒度：权重与缓存按 `layer_id` 维度分开，避免跨层混用；推理/训练逐层执行时，只需维护当前层（或小窗口）的热数据。
- 专家粒度：同一层内仅加载本轮被路由选中的 top-k experts，其余 experts 常驻 SSD/远端，按需下载/按需载入。

验收位置（以训练闭环为例）：

- `steps.megatrain_8step.step7_compare.gate_result.m4.omlx_flashmoe_ondemand_gate`
- evidence：`...omlx_flashmoe_ondemand_gate.smoke.manifest_path`（`omlx_flashmoe_manifest.json`）

核心 evidence 字段（用于证明“按层 + 按 expert + 按需下载”成立）：

- `smoke.num_layers` + `smoke.loaded_unique_experts_by_layer`：证明 cache key 含 layer 维度，且多层不会混权重。
- `smoke.remote_total_files` vs `smoke.local_total_files`（要求 local < remote）：证明不是全量搬运，而是按需下载/按需载入。

文件布局（smoke 产物示例）：

- 远端（模拟）：`train_tune_artifacts/step7_compare/omlx_flashmoe_smoke/remote_experts/layer_{L}/expert_{E}.bin`
- 本地 FlashMoE cache：`.../local_experts/layer_{L}/expert_{E}.bin`
- 本地 oMLX SSD cache：`.../local_experts/omlx_ssd_cache/layer_{L}/expert_{E}.pt.w{1|3|2}.pt`

CLI 开关（M4）：

- `--m4-require-omlx-flashmoe`：启用并作为 gate 约束（超内存预算时必须可跑通）
- `--m4-force-omlx-flashmoe`：即使未判定 oversize 也强制跑 smoke（用于回归与验收）
- `--m4-omlx-flashmoe-mem-util <0-1>`：端侧内存预算比例
- `--m4-omlx-flashmoe-smoke-num-layers <N>`：smoke 覆盖的 layer 数（写入 evidence）

#### 5) M6 产品化里程碑（build/run/模板库/ORT 状态层，可验收 Gate）

M6 的定位是“把可跑的引擎能力，升级为可交付的产品化链路”，对应本仓库内的最小可验收实现包含：

- 模板库：以 JSON 模板描述“运行形态”（例如 ORT state smoke），并可扩展到不同 EP/模型/设备组合。
- build：将模板解析为可运行的 bundle（包含 config、manifest、模型文件与索引）。
- run：从 bundle 启动一次真实推理并落地 ORT 状态层（SQLite + 文件锁），要求同一输入可命中 cache（证明状态层可重放/可复用）。
- require-both：端侧与云侧分别产出 `report.json` 后，再做“端云都 PASS 才算 PASS”的聚合验收。

CLI（M6）：

- `cgc build --template <name> --output-dir <dir>`
- `cgc run --output-dir <dir>`
- `cgc product --template <name> --output-dir <dir>`（build+run 一键）
- `cgc verify --edge-report <edge_report.json> --cloud-report <cloud_report.json> --output <verify_report.json>`

验收字段（以 `cgc product` 为例）：

- `gate_result.m6.build_bundle_gate`：bundle 结构、manifest、模型 sha256、路径索引齐全。
- `gate_result.m6.run_bundle_gate`：ORT 真跑推理 + SQLite 状态写入，且 `second.cache_hit=true` 且 output_hash 与首轮一致。

#### 6) M7 工业级一体化底座（动态轨迹编译 + 全量状态压缩 + 毫秒级软实时回放 + 全链路工业审计，可自动验收 Gate）

M7 的定位是“把产品化链路升级为政企/金融/国资可交付的工业底座”，要求所有指标可自动化落地、可程式判定、并输出标准化 `report.json`（PASS/FAIL），用于统一研发、测试、商务与对接（鸿蒙 PC / AI PC / 政企标案）。

M7 的最小可验收门槛（官方固化版）：

1) 动态轨迹编译（Dynamic Trace Compile）

- 等级：L1（输入 shape 动态变化；control-flow 固定）
- 场景：同一模型/计算图，覆盖 3 组不同动态 shape（例如 batch/seq_len 浮动）
- 指标：
  - 编译成功率 = 100%
  - 编译图缓存命中率 ≥ 67%（2/3）
  - 推理一致性：相同输入两次重跑，输出 Hash 完全一致 = 100%
- 证据（写入 `report.json.gate_result.m7.dynamic_trace`）：
  - `compile_variants[]`: `shape_sig / graph_hash / compile_ms / cache_hit / status`
  - `correctness[]`: `input_hash / output_hash / repeat_consistent`

2) 全量状态压缩（Full-State Compression）

- 门槛：压缩比 ≤ 0.6
- 最小状态覆盖字段：
  - 模型版本 ID、编译产物 ID、推理硬件 Provider、输入摘要、输出摘要、KV 缓存快照指标（可为“present=false”的度量字段）
- 指标：
  - 压缩比（compressed/raw）≤ 0.6
  - 还原一致性：restore 后输出 Hash 与原始完全一致 = 100%
  - 重复去重：同一状态连续写入 10 次，增量存储膨胀 ≤ 1.2 倍（允许索引开销）
- 证据（写入 `report.json.gate_result.m7.state_compression`）：
  - `raw_bytes / compressed_bytes / ratio`
  - `restore_ok`
  - `dedup`: `writes / unique_chunks / bytes_added`

3) 毫秒级实时回放（Real-Time Replay）

- 定义：Soft-RT（商用 PC / 鸿蒙 PC 可量产落地；不宣称硬实时）
- 门槛：Deadline = 10ms
- 指标：
  - P99 ≤ 10ms
  - P999 ≤ 15ms（1.5x 门槛）
  - Miss Rate ≤ 0.1%
  - 连续稳定回放 ≥ 10000 次 workload
- 证据（写入 `report.json.gate_result.m7.replay`）：
  - `mode=soft_rt`
  - `deadline_ms / total_count / miss_rate`
  - `latency_ms`: `p50/p90/p99/p999/max`

4) 全链路工业审计一体化（End-to-End Industrial Audit）

- 覆盖：Build / Compile / Run / State / Replay / Exception 六段式全链路留痕
- 不可抵赖链式证据：
  - 单笔事件 canonical JSON → SHA256 EventHash
  - ChainHash(i) = SHA256(ChainHash(i-1) + EventHash(i))
  - 固定输出：`audit/events.jsonl` + `audit/chain_head.json`
- 验收门槛：
  - 事件完整率 = 100%
  - 链式哈希可完整复算，一致性校验通过 = 100%
  - `audit.verify_ok = true`

M7 最终 PASS/FAIL 规则（全满足才算达标）：

- `dynamic_trace.status == PASS`
- `state_compression.status == PASS`
- `replay.status == PASS`（标注 soft_rt）
- `audit.status == PASS`
- 最终 `report.json.gate_result.m7.status == PASS`

CLI（M7）：

- `cgc pipeline --milestone m7 ...`：在正常 8-step pipeline 结束后追加 M7 gate，并把结果写入同一份 `report.json`。
- 当前实现状态：M7.1 已落地真实验收逻辑与防呆。`report.json` 必定包含 `dynamic_trace/state_compression/replay/audit` 四大结构；若缺依赖或任一指标不达标则明确 FAIL，不会“造假宣称 PASS”。
- 顺序跑多里程碑（同目录/同一把 lock）：使用 `--milestone-seq m3,m4,m5,m6,m7`；配合 `--seq-output-dir-template /tmp/cgc_cloud_localdir_{milestone}_lock` 为每个 milestone 固定独立 `output_dir`，确保每个阶段都有单独的 `report.json`（PASS/FAIL 都算 evidence）。
  - 注意：启用 `--milestone-seq` 时，`--report-path` / `--bundle-export-dir` 需保持为空，或包含 `{milestone}` 占位符，避免多个里程碑覆盖同一个文件/目录（Fail-Close）。

### 3.1.4 当前 M1–M7 最新 Gate 状态（截至 2026-06-03）

说明：

- 本节为“当前工程状态快照”，以 `report.json` 为唯一证据来源；历史章节（例如 3.1.2 的“截至 2026-05-31”）保留其时点含义。
- 端侧（macOS）与云侧（CUDA）能力边界不同：端侧以 MLX-only 口径验收（`CGC_REQUIRE_MLX=1`，后端必须为 mlx），云侧以 CUDA-only 口径验收（`CGC_REQUIRE_CUDA=1`）。
- 版本/路径一致性默认 Fail-Close：必须提供 `CGC_BACKEND_FINGERPRINT_LOCK` 且与当前环境指纹一致，否则禁止继续跑后续 gate（避免“错误环境下假通过”）。
- 端侧不具备 CUDA 多卡分布式 smoke 条件；因此 M4 在端侧的可验收口径以 “单机闭环 + 编译缓存可索引” 为主，分布式 smoke 标记为 SKIP。

| Milestone | 端侧（macOS）最新状态 | 云侧（CUDA）最新状态 |
|---|---|---|
| M1 | PASS（ok=true）<br>report: `_local_m1_rerun2_20260601_135511/report.json` | N/A（未发现 M1 milestone report） |
| M2 | PASS（ok=true）<br>report: `_local_m2_rerun_20260601_135602/report.json`<br>Gate：equivalence=PASS，memory=PASS，speed=PASS，ppl=PASS | PASS（ok=true）<br>report: `_cloud_m2_strict_pass_final_20260601_011343/report.json`<br>Gate：equivalence=PASS，memory=PASS，speed=PASS，ppl=PASS |
| M3 | PASS（ok=true）<br>report: `_local_m3_full_metal_20260601_114624/report.json`<br>Gate：memory=PASS，speed=PASS，ppl=PASS | vLLM 路线 PASS（ok=true）<br>report: `vllm/distilgpt2/run_20260601_162555_0/report.json`<br>Gate：vllm.fullgraph_compile_gate=PASS |
| M4 | PASS（ok=true）<br>report: `/tmp/cgc_m4_local_layered_omlx_run/report.json`<br>Gate：m4.performance=PASS，m4.compile=PASS，m4.distributed_smoke=SKIP，m4.omlx_flashmoe_ondemand_gate=PASS（smoke.num_layers=3） | PASS（ok=true）<br>report: `/tmp/cgc_m4_cloud_layered_omlx_run2/report.json`<br>Gate：m4.performance=PASS（speedup_min=1.2），m4.compile=PASS，m4.distributed_smoke=PASS，m4.omlx_flashmoe_ondemand_gate=PASS（smoke.num_layers=3） |
| M5 | PASS（ok=true）<br>report: `_local_m5_rerun2_20260601_150048/report.json`<br>Gate：m5.aot_precompile_gate=PASS | PASS（ok=true）<br>report: `_cloud_m5_llamacpp_milestone/report.json`<br>Gate：m5.aot_precompile_gate=PASS |
| M6 | PASS（ok=true）<br>report: `/tmp/cgc_m6_local_product_run1/report.json`<br>Gate：m6.build_bundle_gate=PASS，m6.run_bundle_gate=PASS（second.cache_hit=true） | PASS（ok=true）<br>report: `/tmp/cgc_m6_cloud_product_run1/report.json`<br>Gate：m6.build_bundle_gate=PASS，m6.run_bundle_gate=PASS（second.cache_hit=true） |
| M7 | 已落地 M7.1 真验收（未达标即 FAIL）<br>证据：`gate_result.m7.dynamic_trace/state_compression/replay/audit` + `m7_industrial/audit/*` | 已落地 M7.1 真验收（未达标即 FAIL）<br>证据：`gate_result.m7.dynamic_trace/state_compression/replay/audit` + `m7_industrial/audit/*` |

端侧 report 绝对路径（便于检索）：

- M1：`/Users/alexchuang/Documents/embodied/ComputeGraphCompiler-main/Output/PipelineRuns/_local_m1_rerun2_20260601_135511/report.json`
- M2：`/Users/alexchuang/Documents/embodied/ComputeGraphCompiler-main/Output/PipelineRuns/_local_m2_rerun_20260601_135602/report.json`
- M3：`/Users/alexchuang/Documents/embodied/ComputeGraphCompiler-main/Output/PipelineRuns/_local_m3_full_metal_20260601_114624/report.json`
- M4：`/tmp/cgc_m4_local_layered_omlx_run/report.json`
- M5：`/Users/alexchuang/Documents/embodied/ComputeGraphCompiler-main/Output/PipelineRuns/_local_m5_rerun2_20260601_150048/report.json`
- M6：`/tmp/cgc_m6_local_product_run1/report.json`
- M7：运行 `cgc pipeline --milestone m7` 后生成的 `report.json`

云侧 report 绝对路径（便于检索）：

- M2：`/root/cgc-engine/embodied/ComputeGraphCompiler-main/Output/PipelineRuns/_cloud_m2_strict_pass_final_20260601_011343/report.json`
- M3（vLLM）：`/root/cgc-engine/embodied/ComputeGraphCompiler-main/Output/PipelineRuns/vllm/distilgpt2/run_20260601_162555_0/report.json`
- M4：`/tmp/cgc_m4_cloud_layered_omlx_run2/report.json`
- M5：`/root/cgc-engine/embodied/ComputeGraphCompiler-main/Output/PipelineRuns/_cloud_m5_llamacpp_milestone/report.json`
- M6：`/tmp/cgc_m6_cloud_product_run1/report.json`
- M7：运行 `cgc pipeline --milestone m7` 后生成的 `report.json`

### 3.2 统一枚举字典（全线共用，含别名兼容策略）

说明：

- `fail_reason`：允许任何字符串（兼容历史/别名/后续扩展）
- `fail_reason_canonical`：严格枚举（用于入库聚合与线上一致性）

```json
{
  "unit": ["attention", "norm", "mlp", "block", "aot_bundle", "training_loop"],
  "stage": ["A", "B", "C"],
  "path_selected": ["baseline", "optimized"],
  "gate_status": ["PASS", "FAIL", "SKIP"],
  "fail_reason_canonical": [
    "NUMERICAL_MISMATCH",
    "NAN_INF",
    "SHAPE_MISMATCH",
    "DTYPE_MISMATCH",
    "OOM",
    "TIMEOUT",
    "KERNEL_ERROR",
    "CACHE_VERSION_MISMATCH",
    "KV_LAYOUT_INVALID",
    "ABI_MISMATCH"
  ],
  "artifact_kind": ["tap", "dump", "cache", "so", "dylib", "dll", "ptx", "cubin", "gguf", "bundle", "manifest"]
}
```

### 3.3 精简生产级 JSON Schema（Draft 2020-12，可直接入库）

```json
{
  "$schema": "http://json-schema.org/draft/2020-12/schema",
  "title": "CGC 8-step MVP Contract Report (M2~M5)",
  "type": "object",
  "required": ["ok", "steps"],
  "properties": {
    "ok": { "type": "boolean" },
    "steps": {
      "type": "object",
      "required": ["step2_capture", "step3_analyze", "step6_dispatch", "step7_compare", "step8_combine"],
      "properties": {
        "step0_scenario": { "type": "object" },
        "step1_hardware": { "type": "object" },

        "step2_capture": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
            "ok": { "type": "boolean" },
            "replace_target": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["unit", "scope"],
                "properties": {
                  "unit": {
                    "type": "string",
                    "enum": ["attention", "norm", "mlp", "block", "aot_bundle", "training_loop"]
                  },
                  "scope": {
                    "type": "object",
                    "anyOf": [
                      { "required": ["block_index"] },
                      { "required": ["block_range"] }
                    ]
                  },
                  "boundary": { "type": "object" }
                },
                "additionalProperties": true
              }
            }
          },
          "anyOf": [{ "required": ["status"] }, { "required": ["ok"] }],
          "additionalProperties": true
        },

        "step3_analyze": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
            "ok": { "type": "boolean" },
            "gate_plan": {
              "type": "object",
              "required": ["stage", "sample_rate", "metrics_spec"],
              "properties": {
                "stage": { "type": "string", "enum": ["A", "B", "C"] },
                "sample_rate": { "type": "number", "minimum": 0, "maximum": 1 },
                "metrics_spec": {
                  "type": "object",
                  "properties": {
                    "atol": { "type": "number" },
                    "rtol": { "type": "number" },
                    "topk": { "type": "integer", "minimum": 1 }
                  },
                  "additionalProperties": true
                },
                "fail_budget": { "type": "object" }
              },
              "additionalProperties": true
            },
            "skvm_verify": { "type": "object" }
          },
          "anyOf": [{ "required": ["status"] }, { "required": ["ok"] }],
          "additionalProperties": true
        },

        "step6_dispatch": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
            "ok": { "type": "boolean" },
            "exec": {
              "type": "object",
              "required": ["path_selected"],
              "properties": {
                "path_selected": { "type": "string", "enum": ["baseline", "optimized"] },
                "fallback": {
                  "type": "object",
                  "required": ["triggered"],
                  "properties": {
                    "triggered": { "type": "boolean" },
                    "to": { "type": "string", "enum": ["baseline", "optimized"] },
                    "reason": { "type": "string" },
                    "fail_reason": { "type": "string" },
                    "fail_reason_canonical": {
                      "type": "string",
                      "enum": [
                        "NUMERICAL_MISMATCH",
                        "NAN_INF",
                        "SHAPE_MISMATCH",
                        "DTYPE_MISMATCH",
                        "OOM",
                        "TIMEOUT",
                        "KERNEL_ERROR",
                        "CACHE_VERSION_MISMATCH",
                        "KV_LAYOUT_INVALID",
                        "ABI_MISMATCH"
                      ]
                    }
                  },
                  "additionalProperties": true
                }
              },
              "additionalProperties": true
            }
          },
          "anyOf": [{ "required": ["status"] }, { "required": ["ok"] }],
          "additionalProperties": true
        },

        "step7_compare": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
            "ok": { "type": "boolean" },
            "gate_result": {
              "type": "object",
              "required": ["status"],
              "properties": {
                "status": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
                "fail_reason": { "type": "string" },
                "fail_reason_canonical": {
                  "type": "string",
                  "enum": [
                    "NUMERICAL_MISMATCH",
                    "NAN_INF",
                    "SHAPE_MISMATCH",
                    "DTYPE_MISMATCH",
                    "OOM",
                    "TIMEOUT",
                    "KERNEL_ERROR",
                    "CACHE_VERSION_MISMATCH",
                    "KV_LAYOUT_INVALID",
                    "ABI_MISMATCH"
                  ]
                },
                "metrics": { "type": "object" }
              },
              "additionalProperties": true
            }
          },
          "anyOf": [{ "required": ["status"] }, { "required": ["ok"] }],
          "additionalProperties": true
        },

        "step8_combine": {
          "type": "object",
          "properties": {
            "status": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
            "ok": { "type": "boolean" },
            "decision": {
              "type": "object",
              "required": ["allow_optimized"],
              "properties": {
                "allow_optimized": { "type": "boolean" },
                "rollback_plan_id": { "type": "string" }
              },
              "additionalProperties": true
            },
            "artifacts_index": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["kind", "path"],
                "properties": {
                  "kind": {
                    "type": "string",
                    "enum": ["tap", "dump", "cache", "so", "dylib", "dll", "ptx", "cubin", "gguf", "bundle", "manifest"]
                  },
                  "path": { "type": "string" },
                  "sha256": { "type": "string" }
                },
                "additionalProperties": true
              }
            },
            "deploy_unit": { "type": "object" }
          },
          "anyOf": [{ "required": ["status"] }, { "required": ["ok"] }],
          "additionalProperties": true
        },

        "step3_skvm_verify": { "type": "object" },
        "step3_equivalence_gate": { "type": "object" },
        "megatrain_8step": { "type": "object" }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": true
}
```

### 3.4 最终版：M2~M5 完整示例（全部 step 补齐，可直接测试）

M2 Attention 替换：

```json
{
  "ok": true,
  "steps": {
    "step2_capture": {
      "status": "PASS",
      "replace_target": [
        {
          "unit": "attention",
          "scope": { "block_index": 10 },
          "boundary": { "node_range": [900, 1200] }
        }
      ]
    },
    "step3_analyze": {
      "status": "PASS",
      "gate_plan": {
        "stage": "B",
        "sample_rate": 0.1,
        "metrics_spec": { "atol": 0.001, "rtol": 0.001, "topk": 1 }
      }
    },
    "step3_skvm_verify": { "status": "SKIP", "reason": "not enabled" },
    "step3_equivalence_gate": { "status": "SKIP", "reason": "no tap meta provided" },
    "step6_dispatch": {
      "status": "PASS",
      "exec": { "path_selected": "optimized", "fallback": { "triggered": false } }
    },
    "step7_compare": {
      "status": "PASS",
      "gate_result": { "status": "PASS", "metrics": { "max_abs_err": 0.0005, "top1_match": 1.0 } }
    },
    "step8_combine": {
      "status": "PASS",
      "decision": { "allow_optimized": true, "rollback_plan_id": "rbp_m2_v1" },
      "artifacts_index": [{ "kind": "tap", "path": "taps/block_10_out.bin" }]
    }
  }
}
```

M3 Norm + MLP + Cache：

```json
{
  "ok": true,
  "steps": {
    "step2_capture": {
      "status": "PASS",
      "replace_target": [
        { "unit": "norm", "scope": { "block_index": 10 } },
        { "unit": "mlp", "scope": { "block_index": 10 } }
      ]
    },
    "step3_analyze": { "status": "PASS", "gate_plan": { "stage": "B", "sample_rate": 0.1, "metrics_spec": {} } },
    "step3_skvm_verify": { "status": "SKIP", "reason": "not enabled" },
    "step3_equivalence_gate": { "status": "SKIP", "reason": "no tap meta provided" },
    "step6_dispatch": { "status": "PASS", "exec": { "path_selected": "optimized" } },
    "step7_compare": { "status": "PASS", "gate_result": { "status": "PASS" } },
    "step8_combine": {
      "status": "PASS",
      "decision": { "allow_optimized": true },
      "artifacts_index": [
        { "kind": "cache", "path": "cache/mlp_L10" },
        { "kind": "so", "path": "libmlp_opt.so" }
      ]
    }
  }
}
```

M4 Block 整替 + KV 布局：

```json
{
  "ok": true,
  "steps": {
    "step2_capture": {
      "status": "PASS",
      "replace_target": [{ "unit": "block", "scope": { "block_range": [0, 31] } }]
    },
    "step3_analyze": { "status": "PASS", "gate_plan": { "stage": "C", "sample_rate": 0.01, "metrics_spec": {} } },
    "step3_skvm_verify": { "status": "SKIP", "reason": "not enabled" },
    "step3_equivalence_gate": { "status": "SKIP", "reason": "no tap meta provided" },
    "step6_dispatch": { "status": "PASS", "exec": { "path_selected": "optimized" } },
    "step7_compare": { "status": "PASS", "gate_result": { "status": "PASS" } },
    "step8_combine": {
      "status": "PASS",
      "decision": { "allow_optimized": true },
      "artifacts_index": [{ "kind": "gguf", "path": "model.optimized.gguf" }]
    }
  }
}
```

M5 AOT + 训练闭环：

```json
{
  "ok": true,
  "steps": {
    "step2_capture": {
      "status": "PASS",
      "replace_target": [{ "unit": "aot_bundle", "scope": { "block_range": [0, 31] } }]
    },
    "step3_analyze": { "status": "PASS", "gate_plan": { "stage": "C", "sample_rate": 0.001, "metrics_spec": {} } },
    "step3_skvm_verify": { "status": "SKIP", "reason": "not enabled" },
    "step3_equivalence_gate": { "status": "SKIP", "reason": "no tap meta provided" },
    "step6_dispatch": { "status": "PASS", "exec": { "path_selected": "optimized" } },
    "step7_compare": { "status": "PASS", "gate_result": { "status": "PASS" } },
    "step8_combine": {
      "status": "PASS",
      "decision": { "allow_optimized": true },
      "artifacts_index": [
        { "kind": "cubin", "path": "aot_kernel.cubin" },
        { "kind": "bundle", "path": "deploy_bundle/" }
      ]
    },
    "megatrain_8step": {}
  }
}
```

---

## 4. M1 路径：llama.cpp / ggml-cgc（推理侧）

### 4.1 插件产物目录规范（ggml-cgc）

设 `CGC_GGML_GRAPH_DUMP_DIR=$DUMP_DIR`，插件输出：

- `$DUMP_DIR/ggml_graph_*.{json,txt}`：整图 dumps（可选）
- `$DUMP_DIR/partitions.json`：分段信息（建议包含 `block_index` + `node_range`）
- `$DUMP_DIR/stats.json`：统计信息（workspace pool + 分段耗时 + taps 成功标记）
- `$DUMP_DIR/taps/block_%03d_in.bin`、`$DUMP_DIR/taps/block_%03d_out.bin`：inject 边界 taps

注意：插件不生成 `report.json`。

### 4.2 环境变量（ggml-cgc）

- `CGC_LLAMA_CPU_BACKEND=CGC`
- `GGML_BACKEND_PATH=/abs/path/to/libggml-cgc.so`
- `CGC_MODE=native|inject|compile`
- `CGC_GGML_GRAPH_DUMP_DIR=/abs/path/to/dump_dir`
- `CGC_WORKSPACE_POOL_MB=<int>`

### 4.3 CLI 验收（llama.cpp）

构建：

```bash
cmake -S Backend/Llama.cpp/llama.cpp -B Backend/Llama.cpp/llama.cpp/build-cgc \
  -DBUILD_SHARED_LIBS=ON \
  -DGGML_BACKEND_DL=ON \
  -DGGML_CGC=ON \
  -DLLAMA_BUILD_TESTS=OFF

cmake --build Backend/Llama.cpp/llama.cpp/build-cgc --target ggml-cgc llama-cli -j 8
```

native：

```bash
./build-cgc/bin/llama-cli -m /abs/model.gguf -p "hello" -n 8 -c 128 -t 4 -ngl 0
```

inject：

```bash
export GGML_BACKEND_PATH="$(pwd)/build-cgc/bin/libggml-cgc.so"
export CGC_LLAMA_CPU_BACKEND=CGC
export CGC_MODE=inject
export CGC_GGML_GRAPH_DUMP_DIR=/abs/dump_dir
export CGC_WORKSPACE_POOL_MB=64

./build-cgc/bin/llama-cli -m /abs/model.gguf -p "hello" -n 8 -c 128 -t 4 -ngl 0
```

inject 验收点：

- `partitions.json` 存在
- `taps/block_000_in.bin` 与 `taps/block_000_out.bin` 存在（每段均有）
- `stats.json` 存在，且 `workspace_buffer_alloc_count > 0`

compile：

```bash
export CGC_MODE=compile
export CGC_GGML_GRAPH_DUMP_DIR=/abs/dump_dir_compile

./build-cgc/bin/llama-cli -m /abs/model.gguf -p "hello" -n 8 -c 128 -t 4 -ngl 0
```

compile 验收点：

- `partitions.json`、`stats.json` 存在
- 不要求生成 taps（taps 属于 inject）

---

## 5. CUDA 路径：训练/微调闭环（megatrain/train|tune）

本节用于把训练/微调后端提升到与推理侧同标准的“8-step 可验收闭环”。

### 5.1 一键命令

在 CUDA 机器上执行：

```bash
python3 cgc_engine/agent/cli.py pipeline \
  --backend megatrain \
  --task-type train \
  --model dummy \
  --contexts 128 \
  --runs 1 --warmup-runs 0 \
  --output-dir Output/PipelineRuns/_server_megatrain_train
```

### 5.2 产物验收点（必须可索引）

设 `OUTPUT_DIR=Output/PipelineRuns/_server_megatrain_train`：

- 报告：`$OUTPUT_DIR/report.json`
- 训练/微调产物根目录：`$OUTPUT_DIR/train_tune_artifacts/`
- Step 5 inductor cache：`$OUTPUT_DIR/train_tune_artifacts/step5_generate/torchinductor_cache/`
  - 期望至少包含 triton 的 `.ptx/.cubin`（一般在 `triton/0/...`）
  - 期望至少包含 `.so`（用于“可复用编译产物”验收）
    - 若 inductor 默认将 `.so` 输出到 `/tmp/torchinductor_*`，pipeline 会镜像到：
      - `$OUTPUT_DIR/train_tune_artifacts/step5_generate/torchinductor_cache/shared_libs_mirror/*.so`

### 5.3 report.json 关键字段（闭环是否达标）

在 `report.json` 中检查：

- `ok == true`
- `steps.megatrain_8step.step5_generate.status == "PASS"`
- `steps.megatrain_8step.step5_generate.torch_compile.status == "PASS"`
- `steps.megatrain_8step.step5_generate.torch_compile.shared_libs` 至少包含 1 个 `.so` 路径
- `steps.megatrain_8step.step5_generate.torch_compile.cache_dir` 指向本次 run 的 `torchinductor_cache`

### 5.4 说明：为何默认禁用 FSDP（仅限验收路径）

训练闭环的“编译产物验收”优先保证：

- torch.compile 能成功编译并落盘产物
- report.json 能索引到产物路径

因此在验收路径中可将 FSDP 视为“可选增强项”，当 FSDP 与 Dynamo 的约束冲突时，以“先闭环可验收”优先。

---

## 6. CUDA 路径：vLLM（推理侧，待补齐闭环验收）

vLLM 的验收标准与训练侧一致：必须能在 output_dir 内索引到编译缓存目录与 shared libs，并完成一次端到端 dispatch。

环境前置检查：

- Python 环境需可 import vllm
- CUDA/torch.compile 可用

---

## 7. 端云协同（PD 分离 + 固定 KV）（可选场景）

本节用于内化端云协同推理的通用设计点，并将其对齐到统一 8-step 契约与单一真源 `report.json`。该场景不绑定特定硬件型号与操作系统，仅描述“云侧 Prefill + 端侧 Decode”的通用闭环口径。

### 7.1 背景：长上下文的 KV 与延迟压力

传统 Transformer 的 KV Cache 占用与上下文长度线性增长（示意）：

```
KV显存 ≈ batch_size × seq_len × num_layers × num_heads × head_dim × 2(K+V) × sizeof(dtype)
```

当 `seq_len` 增大时，端侧显存与网络同步都会成为瓶颈；仅做 Prefill/Decode 分离（PD 分离）仍可能面临 KV 传输量过大与端侧显存不足的问题。

### 7.2 核心思想：固定大小 KV（投影/压缩）+ PD 分离 + 可回退

高层流程：

1. 云侧执行 Prefill，生成中间态 KV
2. 将 KV 通过“固定基/投影/压缩”等方式转换为固定大小表示（固定 KV）
3. 将固定 KV 同步到端侧
4. 端侧执行 Decode（增量解码）
5. 全程可启用 runtime gate：数值/形状/性能不达标则自动回退到 baseline 路径（例如云端全量推理或禁用固定 KV）

说明：固定 KV 的具体实现可来自多种策略（例如正交基、分块/量化、低秩投影等）。本白皮书仅规定“产物可索引 + 可审计 + 可回退”的工程契约，不强制数学细节。

### 7.3 8-step 对齐（建议字段挂载）

端云协同场景建议复用第 3 章 MVP Contract 的字段骨架：

- Step0 Scenario：`task_type=inference`，并在 scenario 中标记 `execution_mode=edge_cloud_pd`（自定义字符串即可）
- Step1 Hardware：分别记录云侧/端侧的 device 与 runtime 能力（可用 `hardware_profile` 或扩展字段）
- Step2 Capture：记录固定 KV 的配置快照（例如固定维度、dtype、layout_id、投影策略名），以及可定位的分段边界（如 block_range）
- Step3 Analyze：写入 gate 计划（采样率/阈值/fail budget），可同时挂 `skvm_verify` 摘要用于子图级校验
- Step6 Dispatch：写入实际执行路径（cloud prefill + edge decode），并记录是否发生 fallback（以及原因）
- Step7 Compare：写入基线与优化路径的对比结果（数值等价/行为一致性/性能）
- Step8 Combine：汇总上线决策、回退计划 ID、端云协同产物索引（固定 KV blob、同步日志、缓存目录、manifest 等）

### 7.4 产物与索引（最小建议）

为满足“可验收闭环”，端云协同场景至少应能在 `output_dir` 内索引到：

- 固定 KV 产物（例如 `kv_blob.bin` 或同等二进制）
- 固定 KV 的 manifest（例如 `kv_manifest.json`，包含 dtype/shape/layout_id/hash）
- 同步与调度日志（例如 `pd_sync.log` 或等价结构化字段）

上述产物应通过 `steps.step8_combine.artifacts_index[]` 写入 report 真源。

---

## 8. 常见问题

### Q1：为什么 partitions.json 里建议包含 block_index？

为了让 pipeline 端稳定对齐 layer id，避免依赖 tensor/name 的漂移。

### Q2：workspace pool “真正生效” 如何验证？

查看 `$DUMP_DIR/stats.json`：

- `workspace_buffer_alloc_count > 0`
- `workspace_bytes_in_use_peak > 0`

### Q3：为什么 `.so` 可能不在 TORCHINDUCTOR_CACHE_DIR？

部分 torch/inductor/triton 组合会把 triton `.so` 写到 `/tmp/torchinductor_*`（作为运行时编译缓存）。为满足“产物目录可验收”，闭环会将关键 `.so` 镜像到 run 的 `torchinductor_cache/shared_libs_mirror/` 并在 report.json 中引用。
