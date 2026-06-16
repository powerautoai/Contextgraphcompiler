# CGC M8 产品化与开发者体验技术白皮书

**版本**: v1.0  
**状态**: 官方固化版本  
**目标场景**: 端云协同 AI 产品发布、开发者入口验收、CLI/Serve/Claude Code 接管验证、三平台 release 构建交付。  

---

## 一、升级目标：M8 产品化与开发者体验正式验收
为统一开发、测试、CI、交付、GitHub Release 与正式版本发布口径，定义 M8 最小产品化验收门槛。所有指标必须可自动化执行、可程序判断、可输出标准化 `report.json` 与 `summary.json`。

`M8` 的核心职责不是重复 `M7.5 API compatibility`，而是把开发者与交付链真正会接触到的产品入口做成正式 Gate：

- `M7.5` 解决“接口像不像”
- `M8` 解决“入口能不能真实工作、能不能被接管、能不能被交付、能不能正式发布”

### 1. 开发者入口与 Claude Code 双验收（M8.1）｜最小验收规范
**正式命名：`m81_m75_claude_dual_acceptance`**

**覆盖范围定义**
- 以 `M7.5 API compatibility` 为底座
- 以 `cgc list` 为产品入口发现能力
- 以 `Claude Code` 为开发者接管能力验证

**最小可验收指标**
- `M7.5` API 基础相容能力通过
- `cgc list` 可发现 `local`、`nfs`、`registry` 三类来源
- 必须出现要求中的模型 ID
- `Claude Code` 接管链可被真实触发，不接受静态 mock

**标准证据输出（写入 report.json）**
- `models[]`
- `summary.total_models`
- `required_sources[]`
- `required_model_ids[]`
- `claude_takeover_contract.status`
- `claude_takeover_contract.details.output_excerpt`

### 2. `cgc run` 与 route takeover 双验收（M8.2）｜最小验收规范
**正式命名：`m82_cgc_run_route_dual_acceptance`**

**覆盖范围定义**
- 覆盖 `cgc run` 本地成功路径
- 覆盖 route decision 证据输出
- 覆盖 `M7.3 edge-cloud takeover` 接管路径

**最小可验收指标**
- 本地路径必须能得到 `m4_local` 路由与正确 backend
- 接管路径必须能得到 `m73_edge_cloud` 路由与 bridge backend
- local / takeover 两条路线都必须输出完整 evidence paths
- route decision 必须可回溯 `decision_reason.code`

**标准证据输出**
- `selected_route`
- `selected_backend`
- `local_execution`
- `cloud_bridge_used`
- `decision_reason.code`
- `evidence_paths.run_report`
- `evidence_paths.m4_inference_report`
- `evidence_paths.edge_inference_bridge`
- `evidence_paths.route_decision`

### 3. `cgc serve` streaming 与 M7.3 takeover 双验收（M8.3）｜最小验收规范
**正式命名：`m83_serve_streaming_takeover_acceptance`**

**覆盖范围定义**
- 覆盖 `cgc serve` local streaming success
- 覆盖 `cgc serve` final takeover success
- 覆盖 streaming 首包与尾包正式结构

**最小可验收指标**
- first chunk 必须给出 route 与 decision evidence
- final chunk 必须给出 backend、execution、bridge 使用状态
- takeover 场景必须能进入 `M7.3 edge_cloud_bridge`
- local / takeover 两条流式路径都必须可自动判定 PASS/FAIL

**标准证据输出**
- `first.status`, `first.type`, `first.model`
- `first.selected_route`, `first.decision_reason.code`
- `final.selected_route`, `final.selected_backend`
- `final.local_execution`, `final.cloud_bridge_used`
- `final.evidence_paths.local_infer`

### 4. 三平台 release build 与正式交付链验收（M8.4）｜最小验收规范
**正式命名：`m84_cgc_build_release_acceptance`**

**覆盖范围定义**
- 覆盖当前主机 `cgc build` 真构建证据
- 覆盖 `windows` / `macos` / `linux` 三平台 matrix build 证据
- 覆盖 `CGC_Release/dist/{windows,macos,linux}` 正式收敛目录
- 覆盖 `build_matrix_manifest.json`
- 覆盖每平台 package size 的 warning / fail 规格治理

**最小可验收指标**
- 当前主机 build report 字段完整且 package format 正确
- 三平台必须各自有独立 report 证据
- `build_matrix.json` 必须存在且状态为 `PASS`
- `build_matrix_manifest.json` 必须存在且字段完整
- `dist artifact` 与 `release asset` 必须同时存在
- package size 不得超过 `hard limit`

**标准证据输出**
- host build report：`builder`, `platform`, `package_format`, `output_path`, `size_bytes`
- matrix report：`windows.json`, `macos.json`, `linux.json`, `build_matrix.json`
- dist manifest：`build_matrix_manifest.json`
- release dist：`CGC_Release/dist/windows`, `CGC_Release/dist/macos`, `CGC_Release/dist/linux`
- release assets：`cgc-windows.zip`, `cgc-macos.zip`, `cgc-linux.tar.gz`
- budget fields：`budget_status`, `size_budget_level`, `executable_budget_level`

---

## 二、M8.1：M7.5 + Claude Code 双验收

### 4.1 验收定义

`M8.1` 的正式含义是：

- `M7.5 API compatibility`
- `Claude Code`

二者必须同时成立，才算开发者入口通过。

### 4.2 验收目标

确保开发者从产品入口使用系统时：

- API 基础相容能力成立
- `cgc list` 能正确发现本地、NFS、registry 模型来源
- `claude` 接管链可被真实触发，而非伪造字符串或静态 mock

### 4.3 关键检查项

- `m75_api_compat_foundation`
- `product_entry_list_contract`
- `claude_takeover_contract`

### 4.4 最小证据要求

- `models`
- `summary.total_models`
- `required_sources = local / nfs / registry`
- `required_model_ids`
- `Launching Claude Code CLI`
- `Claude Code`

### 4.5 PASS 语义

`M8.1 PASS` 表示：

- 系统不仅 API 面兼容
- 还具备真实可用的开发者入口与 Claude Code 接入能力

---

## 三、M8.2：`cgc run` 与 route takeover 双验收

### 5.1 验收定义

`M8.2` 的正式含义是：

- `cgc run local success`
- `route decision takeover evidence`

既要验证本地路线成功，也要验证在需要时能转入 `M7.3` edge-cloud takeover。

### 5.2 验收目标

确保 `cgc run` 不是只返回一个“看起来成功”的响应，而是能输出真实 route 决策与接管证据。

### 5.3 关键检查项

- `cgc_run_response_contract`
- `route_decision_contract`
- `cgc_run_takeover_contract`
- `route_decision_takeover_contract`

### 5.4 最小证据要求

- `selected_route`
- `selected_backend`
- `local_execution`
- `cloud_bridge_used`
- `decision_reason.code`
- `evidence_paths.run_report`
- `evidence_paths.m4_inference_report`
- `evidence_paths.edge_inference_bridge`
- `evidence_paths.route_decision`

### 5.5 PASS 语义

`M8.2 PASS` 表示：

- 本地推理路线可用
- 接管到 `M7.3` 的路径也可被证据化验证
- route 决策不是黑盒，也不是不可复核的静态结果

---

## 四、M8.3：`cgc serve` streaming 与 M7.3 takeover 双验收

### 6.1 验收定义

`M8.3` 的正式含义是：

- `serve streaming local success`
- `serve streaming M7.3 takeover`

它验证的是在线服务入口，而不是离线 CLI 单次执行。

### 6.2 验收目标

确保 `cgc serve` 对外暴露流式响应时：

- local 路线可返回合规首包与尾包
- 在需要接管时能进入 `M7.3 edge_cloud_bridge`
- final route / backend / evidence 均可回溯

### 6.3 关键检查项

- `serve_response_contract`
- `serve_takeover_contract`

### 6.4 最小证据要求

- first chunk:
  - `status`
  - `type`
  - `model`
  - `selected_route`
  - `decision_reason.code`
- final chunk:
  - `selected_backend`
  - `local_execution`
  - `cloud_bridge_used`
  - `evidence_paths.local_infer`

### 6.5 PASS 语义

`M8.3 PASS` 表示：

- 在线服务流式接口真实可用
- 本地响应与 takeover 响应都可被自动验证
- 接管过程具有完整证据链

---

## 五、M8.4：三平台 release build 与正式交付链验收

### 7.1 验收定义

`M8.4` 的正式名称为：

- `m84_cgc_build_release_acceptance`

它不是“当前机器能跑一次 `cgc build`”这么简单，而是以下多重验收的组合：

- `cgc_build_release_contract`
- `build_matrix_contract`
- `build_dist_manifest_contract`
- `artifact_size_budget`
- `windows_artifact_size_budget`
- `macos_artifact_size_budget`
- `linux_artifact_size_budget`

### 7.2 核心目标

把 `cgc build` 从“构建命令存在”升级为“正式 release 可交付”。

也就是从：

- 命令可执行

升级到：

- 三平台存在真实 build 证据
- release dist 已被收敛
- release asset 已可打包发布
- package size 受到正式产品规格治理

### 7.3 三层证据链

`M8.4` 需要三层证据同时成立：

#### 第一层：当前主机构建证据

来自 `cgc_build_release_contract`，至少要求：

- `builder`
- `platform`
- `package_format`
- `output_path`
- `executable_path`
- `output_exists`
- `size_bytes`
- `executable_size_bytes`
- `supported_platforms`

#### 第二层：三平台 matrix 证据

来自 `build_matrix_contract`，必须覆盖：

- `windows`
- `macos`
- `linux`

并要求每个平台 report 至少带有：

- `generated_at`
- `builder`
- `platform`
- `host_platform`
- `host_arch`
- `package_format`
- `output_path`
- `executable_path`
- `output_exists`
- `size_bytes`
- `executable_size_bytes`
- `artifact_sha256`
- `executable_sha256`
- `supported_platforms`

对应 package format 约束为：

- `windows` -> `exe`
- `macos` -> `app_bundle`
- `linux` -> `elf`

#### 第三层：dist / manifest / release asset 证据

来自 `build_dist_manifest_contract`，必须验证：

- `CGC_Release/dist/windows`
- `CGC_Release/dist/macos`
- `CGC_Release/dist/linux`
- `CGC_Release/dist/build_matrix_manifest.json`
- `CGC_Release/dist/release_assets`

同时要求 manifest 中包含：

- `status`
- `generated_at`
- `matrix_dir`
- `matrix_file`
- `dist_dir`
- `release_assets_dir`
- `required_platforms`
- `platforms`

### 7.4 package size 正式规格

`M8.4` 的 package size 采用两段式策略：

- `soft target`
- `hard limit`

判定规则如下：

- 小于等于 `soft target` -> `PASS`
- 大于 `soft target` 且小于等于 `hard limit` -> `WARN`
- 大于 `hard limit` -> `FAIL`

其目的不是只做一条僵硬死线，而是同时兼顾：

- 产品可交付性
- 包体增长预警
- CI 自动阻断能力

### 7.5 当前规格

以现行 gate 配置为准：

- 通用包体 soft target: `838860800`
- 通用包体 hard limit: `1288490188`
- 可执行文件 soft target: `209715200`

平台 hard limit 差异：

- `macos executable hard limit = 314572800`
- `windows executable hard limit = 524288000`
- `linux executable hard limit = 524288000`

### 7.6 PASS 语义

`M8.4 PASS` 表示：

- 当前主机 build 通过
- 三平台证据齐全
- `build_matrix.json` 合格
- `build_matrix_manifest.json` 合格
- `CGC_Release/dist/{windows,macos,linux}` 收敛完整
- release assets 已形成
- 三平台包体符合 warning / fail 规格

也就是说，`M8.4 PASS` 才能被解释为：

- “这个版本已具备正式 release 交付能力”

而不是：

- “当前机器某次构建没有报错”
- “CI 尚未产出三平台 release 证据也可视为通过”

---

## 六、GitHub Actions / Jenkins 在 M8.4 中的角色

`M8.4` 明确要求进入 CI / 产线流程，不能只靠本地人工构建。

因此需要：

- GitHub Actions 三平台 matrix build
- Jenkins 三平台并行 build
- 聚合 report
- 聚合 build outputs
- 生成 `build_matrix.json`
- 生成 `build_matrix_manifest.json`
- 收敛 `CGC_Release/dist`
- 在 tag build 时发布 release assets

这意味着：

- CI 不是附属脚本
- CI 本身就是 `M8.4` 正式证据链的一部分
- 无 CI 三平台 runner 证据，不得宣称 `M8.4` 已完成正式 release 验收

---

## 七、M8 与白皮书命名对齐原则

为避免 YAML section、summary、report、release note、白皮书之间发生命名漂移，M8 统一采用以下对齐方式：

- Gate alias 与白皮书命名一致
- acceptance contract 与 release note 命名一致
- section 语义必须可从名字直接读出

推荐使用以下正式名称：

- `m81_m75_claude_dual_acceptance`
- `m82_cgc_run_route_dual_acceptance`
- `m83_serve_streaming_takeover_acceptance`
- `m84_cgc_build_release_acceptance`

---

## 八、M8 最终 PASS/FAIL 规则

M8 为产品化 Gate，不接受“部分看起来可用”的松散判定，不接受仅靠说明文字、自报成功、单机烟雾测试替代正式证据链。

最终原则如下：

- `M8.1` 必须通过
- `M8.2` 必须通过
- `M8.3` 必须通过
- `M8.4` 必须通过
- `summary.json` 与 `report.json` 中的整体状态必须一致

其中 `M8.4` 若出现以下任一情况，应直接 `FAIL`：

- 缺少任一平台 `windows` / `macos` / `linux` 证据
- `build_matrix.json` 状态不是 `PASS`
- `build_matrix_manifest.json` 不存在或字段不完整
- dist artifact 或 release asset 缺失
- 包体超过 `hard limit`

若仅超过 `soft target`，但未超过 `hard limit`，则应标记为：

- `WARN`

但整体验收是否允许通过，仍以具体 contract 聚合规则为准。

---

## 九、结论

`M8` 的意义，在于把“兼容接口”推进为“正式产品入口”，再推进为“真实可交付 release 链”。

其中：

- `M8.1` 解决开发者入口与 Claude Code 接入
- `M8.2` 解决 `cgc run` 与 route takeover
- `M8.3` 解决 `cgc serve` 与 streaming takeover
- `M8.4` 解决三平台 release 构建、dist 收敛、manifest、release assets 与包体治理

因此，`M8.4` 不再只是一个 build 检查点，而是 `CGC` 是否具备正式发布资格的关键产品化验收门槛。
