# Semgrep 接入设计（归档）

> 说明：原文件未能完整取回，以下内容依据当前代码实现状态重建为归档版设计摘要。

## 1. 设计目标

- 在现有 Bandit 之外，为 SAST 增加可切换的 Semgrep 引擎
- 复用现有任务模型、结果入库流程与导出能力
- 让前端与接口层能感知 `scanner_engine` 维度

## 2. 当前代码侧线索

- `backend/app/config.py` 中存在 `SAST_ALLOWED_ENGINES`、`SEMGREP_CMD`、`SEMGREP_RULESET`
- `backend/app/services/sast_service.py` 中存在 `run_semgrep_scan` 及 Semgrep 结果归一化逻辑
- `backend/app/workers/sast_tasks.py` 中已按 `scanner_engine` 分发到 Bandit 或 Semgrep
- `backend/tests/test_sast_service.py` 与 `backend/tests/test_tasks.py` 中存在 Semgrep 相关测试

## 3. 设计要点

### 3.1 配置层
- 通过环境变量声明允许的 SAST 引擎
- 支持自定义 Semgrep 命令路径与规则集

### 3.2 执行层
- 创建任务时记录 `scanner_engine`
- Worker 根据 `scanner_engine` 路由到对应扫描函数
- 统一落到已有任务状态流转体系中

### 3.3 结果层
- 对 Semgrep 结果做严重度、置信度、文件路径、更多信息等字段的归一化
- 复用现有 SAST 结果持久化与导出链路

## 4. 归档说明

- 当前主线文档仍以 Bandit / Wapiti 主链路演示为核心
- 本文档保留为扩展设计参考，供后续增强 SAST 能力时使用
