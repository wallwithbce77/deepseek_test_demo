# DeepSeek 大模型接口自动化测试与字段抽取评估

基于 Python、pytest 和 Requests 的大模型测试项目，覆盖接口响应、对话输出规则、采购文本字段抽取及异常处理。

项目将测试数据、接口调用、断言和结果统计分开组织，支持离线模拟和真实接口两种运行模式。

## 测试范围

| 模块 | 内容 |
|---|---|
| 对话测试 | 正常功能、指令遵循、资料忠实度、安全、边界场景 |
| 字段抽取 | 订单号、供应商、金额、交付日期、明细行数及合计金额 |
| 稳定性检查 | 重复请求固定 JSON 输出，默认运行 5 次 |
| 接口异常 | 本地模拟 401、429、500 和非 JSON 响应，检查错误处理与重试次数 |
| 真实接口检查 | 无效密钥、不存在的模型、响应结构与 Token 统计关系 |
| 离线自检 | 数据集结构、用例 ID、规则配置、归一化和评分函数 |

当前包含 30 条对话用例（5 类各 6 条）、12 条采购文本抽取样本，以及本地 HTTP Stub 测试和评分规则测试。抽取样本包含中文、英文和德文。

采购样本以文本形式输入，不包含图片 OCR 或 PDF 解析流程。

## 目录结构

```text
.
├── .github/workflows/
│   └── offline-tests.yml  # GitHub Actions 离线回归
├── core/
│   ├── client.py          # 真实 HTTP 客户端
│   ├── config.py          # 环境变量、运行模式和阈值
│   ├── dataset.py         # 测试数据加载
│   ├── fake_client.py     # 离线模拟客户端
│   ├── metrics.py         # 指标统计与 JSON 报告保存
│   └── validators.py      # 输出断言、归一化和字段评分
├── data/
│   ├── cases_functional.json
│   ├── cases_instruction.json
│   ├── cases_grounding.json
│   ├── cases_safety.json
│   ├── cases_boundary.json
│   └── extract_samples.json
├── tests/
│   ├── conftest.py        # 客户端 fixture、运行上下文和报告输出
│   ├── stub_server.py     # 本地 HTTP 模拟服务
│   ├── test_chat.py       # 对话与固定 JSON 输出稳定性测试
│   ├── test_extraction.py # 字段抽取评估与阈值断言
│   ├── test_negative.py   # 本地异常测试及真实接口检查
│   └── test_offline.py    # 数据与校验函数自检
├── docs/
│   └── defects.md         # 问题分析、修改与验证记录
├── artifacts/            # 运行生成的指标报告，默认不提交到 Git
├── client2.py            # 简化客户端学习代码，主测试流程未使用
├── .env.example
├── pytest.ini
└── requirements.txt
```

## 环境准备

使用 Python 3.10 或以上版本；GitHub Actions 当前配置 Python 3.13。以下命令以 Windows PowerShell 为例，在项目根目录执行。

已有 Python 环境时，可直接安装依赖：

```powershell
python -m pip install -r requirements.txt
```

如需创建独立环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

后续命令中的 `python` 应指向安装了项目依赖的解释器，也可以替换为 `.\.venv\Scripts\python.exe`。

## 离线运行

```powershell
$env:USE_FAKE = "1"
python -m pytest --html=artifacts/report_fake.html --self-contained-html
```

离线模式下：

- 对话和字段抽取使用 `FakeClient`。
- 本地 HTTP 异常测试仍会启动回环地址上的 Stub 服务。
- 需要真实接口的专用用例会跳过。
- 不需要 API Key，不调用远程模型。

`FakeClient` 根据用例标注生成回答，延迟和 Token 用量包含模拟值。离线结果用于检查测试流程与规则，不代表真实模型的准确率、速度或稳定性。

## 真实接口运行

首次配置时，将 `.env.example` 复制为 `.env`，已有 `.env` 时不要覆盖：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

在 `.env` 中配置：

```dotenv
DEEPSEEK_API_KEY=填写实际密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com/chat/completions
DEEPSEEK_MODEL=填写当前接口支持的模型名称
```

`DEEPSEEK_BASE_URL` 应填写完整的聊天接口地址，客户端不会自动追加路径。请显式配置实际可用的模型，不要把源码默认模型名视为服务可用性保证。

执行测试：

```powershell
$env:USE_FAKE = "0"
python -m pytest --html=artifacts/report_real.html --self-contained-html
```

真实运行会产生接口请求及相应费用。运行后检查报告中的 `mode` 和 `model`，确认使用了预期配置。

如果没有读取到 API Key，当前代码会自动使用离线模式，即使设置了 `USE_FAKE=0` 也一样。已设置的进程环境变量优先于 `.env` 中的同名值。

不要将 `.env` 或真实密钥提交到仓库。

## 单独运行测试

数据集和校验函数自检：

```powershell
python -m pytest tests/test_offline.py
```

本地接口异常与重试测试：

```powershell
python -m pytest tests/test_negative.py -m "not live"
```

仅运行字段抽取评估：

```powershell
python -m pytest tests/test_extraction.py
```

仅运行标记为 `live` 的接口检查：

```powershell
python -m pytest -m live
```

运行字段抽取或对话测试前，应明确设置 `USE_FAKE`。真实接口检查还需要有效的接口配置。

`live` 标记仅用于部分真实接口专用测试。对整个项目执行 `-m "not live"`，并不能保证离线；对话和抽取测试仍由 `USE_FAKE` 与密钥配置决定使用哪个客户端。

## 常用配置

配置由 `core/config.py` 从环境变量和项目根目录的 `.env` 读取。

| 配置项 | 默认值 | 用途 |
|---|---|---|
| `USE_FAKE` | 未设置；无密钥时自动离线 | 设为 `1`、`true` 或 `yes` 启用离线模式 |
| `DEEPSEEK_TIMEOUT` | `60` | HTTP 读取超时，单位秒 |
| `DEEPSEEK_TEMPERATURE` | `0` | 请求温度参数 |
| `DEEPSEEK_MAX_TOKENS` | `1024` | 默认输出 Token 上限，部分测试单独指定 |
| `STABILITY_RUNS` | `5` | 固定 JSON 输出重复请求次数 |
| `MAX_LATENCY_S` | `20` | 对话用例的单次响应时延上限 |
| `GATE_JSON_VALID_RATE` | `0.95` | 抽取 JSON 格式合规率阈值 |
| `GATE_FIELD_ACCURACY` | `0.85` | 抽取字段准确率阈值 |
| `GATE_P95_LATENCY_S` | `15` | 汇总报告中的 P95 阈值 |
| `FAKE_ERROR_RATE` | `0` | 离线模拟输出破坏概率 |
| `FAKE_SEED` | `7` | 离线随机种子 |
| `ARTIFACT_DIR` | 项目下的 `artifacts` | 指标报告保存目录 |

## 指标定义

### JSON 格式合规率

针对字段抽取样本，直接解析模型原始回答，并要求顶层为 JSON 对象。

```text
JSON 格式合规率 = 格式合规的抽取样本数 / 全部抽取样本数
```

- 允许首尾空白，不提前移除 Markdown 代码围栏。
- 数组、字符串、数字、布尔值和顶层 `null` 不合规。
- 空对象 `{}` 格式合规，但不代表字段完整。
- HTTP 成功率单独统计。

当前实现使用 Python 默认 JSON 解析器，尚未额外拒绝 `NaN`、`Infinity` 等非标准数值。

### 字段准确率

将抽取字段与标注值进行归一化比较：

```text
字段准确率 = 判定正确的字段数 / 全部预期字段数
```

归一化包括部分日期、金额、全角字符及文本格式处理。该指标衡量当前规则下的值匹配，不等于严格字段类型检查。

### 整条匹配率

```text
整条匹配率 = 全部预期字段均判定正确的样本数 / 全部抽取样本数
```

这是预期字段的整体匹配结果，不是原始 JSON 文本完全相同；当前额外字段不扣分。

### 时延与 Token

报告记录平均时延、P95 时延及 Token 用量。

真实客户端的时延取自 `response.elapsed`，不代表包含全部重试、退避和响应体读取的端到端耗时。离线模式下的时延和 Token 数据不能用于性能结论。

### 阈值是否影响测试结果

- JSON 格式合规率和字段准确率有 pytest 断言，低于阈值会导致对应测试失败。
- 对话用例会检查 `MAX_LATENCY_S`。
- 汇总 P95 阈值当前用于报告展示，超限不会单独改变 pytest 退出码。

## 测试报告

对话或抽取测试运行后，默认生成：

```text
artifacts/
├── <run_id>/
│   └── metrics.json
└── latest/
    └── metrics.json
```

`metrics.json` 包含运行 ID、开始时间、模式、模型名称、对话分类统计、抽取指标、逐字段结果、样本明细及阈值比较结果。

其中 `total` 统计的是写入运行上下文的对话及稳定性记录，不是 pytest 全部测试数量。抽取结果单独保存在 `extraction` 中。

HTML 报告需通过 `--html` 参数生成，用于查看 pytest 的通过、失败和跳过情况。仅运行离线单元测试或接口异常测试时，不一定生成 `metrics.json`。

保留按 `run_id` 命名的目录；`latest` 会被后续运行覆盖。比较不同运行结果时，应同时确认代码版本、模型、模式、数据集和指标口径。旧 JSON 合规口径下的报告不能直接视为新口径的验证结果。

## GitHub Actions 离线回归

工作流配置位于 [`.github/workflows/offline-tests.yml`](.github/workflows/offline-tests.yml)。将配置提交并推送到 GitHub 后，推送代码或提交、更新 PR 时会自动执行离线回归，也支持手动触发。

工作流使用 Ubuntu 和 Python 3.13，安装 `requirements.txt` 中的依赖，并设置 `USE_FAKE=1`、`FAKE_ERROR_RATE=0`、`FAKE_SEED=7`。不需要配置真实 API Key。

执行命令：

```bash
python -m pytest -m "not live" --html=artifacts/ci/report.html --self-contained-html --junitxml=artifacts/ci/junit.xml
```

对话与字段抽取使用 FakeClient，接口异常测试使用本地 HTTP Stub；标记为 `live` 的真实接口测试被排除。本工作流同时通过 `USE_FAKE=1` 明确启用模拟模式。

### 查看结果

进入 GitHub 仓库的 **Actions → Offline tests**，选择一次运行查看测试日志。在该次运行页面的 **Artifacts** 区域下载 `offline-test-reports`，其中包含：

- `report.html`：pytest HTML 报告，下载解压后用浏览器打开。
- `junit.xml`：JUnit 格式测试结果。
- `metrics/`：对话与抽取指标及样本明细。

报告保留 14 天。测试失败时也会尝试上传已生成的报告；如果安装依赖等前置步骤失败，报告可能尚未生成。

需要手动运行时，在工作流进入默认分支后，打开 **Actions → Offline tests → Run workflow**，选择分支并执行。

CI 通过表示离线回归通过，不代表真实模型的准确率、性能或稳定性达标。真实接口评测应单独运行并保留记录。

## 当前边界

- 资料忠实度使用预设答案的归一化匹配，覆盖资料不足和冲突场景，未实现长回答的逐事实证据溯源。
- 部分对话规则使用关键词或格式匹配，不能代替完整语义评价。
- 字段评分目前可能混淆缺失字段与显式 `null`，需要进一步完善。
- 对话 JSON 检查与抽取 JSON 格式合规率不是同一口径，部分对话检查仍会清洗代码围栏。
- 数据集规模较小，单次真实运行不能代表模型在所有业务场景下的表现。
- `client2.py` 是独立学习代码，不作为项目主客户端使用。

## 问题与回归记录

问题记录保存在 [`docs/defects.md`](docs/defects.md)，建议每条记录包含：

1. 问题现象与关联用例。
2. 预期行为、实际行为及影响。
3. 定位过程和修改内容。
4. 反例验证结果。
5. 回归命令、代码版本、运行日期和报告位置。

区分“代码已修改”和“回归已验证”。历史报告用于追溯，不代表当前版本已经重新验证。
