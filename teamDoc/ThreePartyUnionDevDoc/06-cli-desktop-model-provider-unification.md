# 06. CLI 与 Desktop 模型供应商统一方案

日期：2026-05-25

## 问题

Hermes CLI `/model`、TUI `model.options`、Hermes Dashboard `/api/model/options` 已经使用 `hermes_cli.inventory` 作为共享模型清单基座。Hermes Desktop 过去仍维护独立模型库，导致：

- Desktop `Models` 页与 CLI `/model` 的 provider/model 不一致。
- Chat Tab 底部模型选择器与 Desktop `Models` 页、CLI `/model` 三者不一致。
- Desktop 可能启动旧的本地 Hermes Agent Gateway，从而读取旧 provider registry 和旧 `hermes_cli` 模块。

## 统一原则

`hermes_cli.inventory` 是 CLI、TUI、Dashboard、Desktop 的唯一模型清单来源。

统一调用参数：

```python
build_models_payload(
    load_picker_context(),
    include_unconfigured=True,
    picker_hints=True,
    canonical_order=True,
    max_models=50,
)
```

含义：

- `include_unconfigured=True`：未配置 provider 也出现在列表中，带配置提示。
- `picker_hints=True`：输出认证状态、认证类型、环境变量提示和 warning。
- `canonical_order=True`：按 `CANONICAL_PROVIDERS` 顺序展示，真正的 custom provider 排在后面。
- `max_models=50`：与 TUI picker 的列表规模一致。

## Agent 侧变更

`hermes_cli/web_server.py` 的 `/api/model/options` REST endpoint 改为使用与 TUI `model.options` 一致的参数，避免 Dashboard 成为第三套模型列表。

`hermes_cli.inventory` 继续承担：

- 读取 profile 的 `model` 配置。
- 合并 `providers:` 与 `custom_providers:`。
- 调用 `list_authenticated_providers()` 获取 curated model list。
- 补齐未配置 provider 的提示行。

## Desktop 侧变更

Desktop 新增 `hermes-runtime.ts`，用于解析当前 Local Hermes Agent Runtime。Desktop 不再默认固定到 `~/.hermes/hermes-agent`：

1. Desktop Settings 中的 `localHermesAgentPath`。
2. `HERMES_AGENT_REPO`。
3. `HERMES_REPO`。
4. `PATH` 中 `hermes` 可执行文件反推。
5. 相邻 workspace。
6. `~/.hermes/hermes-agent`。

Desktop `listModels(profile)` 通过该 runtime 执行 `hermes_cli.inventory`，并传入 profile 对应的 `HERMES_HOME`。因此 profile 切换后，Desktop 模型列表与 CLI 对应 profile 一致。

## 配置边界

模型选择仍写入 Hermes profile 的 `config.yaml`：

```yaml
model:
  provider: "openrouter"
  default: "anthropic/claude-sonnet-4.5"
  base_url: ""
```

Desktop 不再把 `~/.hermes/models.json` 作为正常模型列表来源。该文件仅作为 runtime 不可用时的旧环境 fallback。

## 与 Team Mode 的关系

Team mode 下本地人格合并、团队记忆抽取、Desktop Bridge fallback 都依赖当前 Hermes profile 的模型供应商配置。模型清单统一后：

- CLI `/model` 选择的 provider/model 会被 Desktop Chat picker 看到。
- Desktop Chat picker 切换的 provider/model 会写回同一个 profile config。
- Desktop 启动本地 Gateway 时使用同一个 Hermes Agent Runtime，避免旧 gateway 缺失 team/cloud/soul 模块。

## 验收

- CLI `/model`、TUI picker、Agent Dashboard `/api/model/options`、Desktop `Models` 页和 Chat picker 的 provider/model universe 同源。
- Settings 指定 Local Hermes Agent Path 后，Desktop 立即使用该 repo 的 provider registry 与 inventory。
- Desktop 本地 Gateway、CLI fallback 与 Team Bridge fallback 都不再隐式依赖旧 `~/.hermes/hermes-agent`。
