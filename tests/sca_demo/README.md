# SCA 扫描演示测试用例

本目录用于演示 DevSecOps 平台的 SCA（Software Composition Analysis，软件成分分析）能力。测试材料故意包含多个生态的历史易受影响依赖版本，可用于展示依赖识别、漏洞匹配、严重级别统计、修复版本建议、许可证提示和报告导出效果。

> 安全边界：这些文件只作为扫描输入和演示夹具使用，不要在真实业务环境中安装其中的依赖版本。

## 文件说明

| 文件 | 生态 | 演示重点 |
| --- | --- | --- |
| `requirements-vulnerable.txt` | Python / pip | 常见 Web 框架、HTTP 客户端、模板和 YAML 解析库的历史漏洞版本 |
| `requirements-mixed.txt` | Python / pip | 同时包含安全版本、漏洞版本和直接依赖，便于展示“有风险 / 无风险”对比 |
| `package-vulnerable.json` | Node.js / npm | 旧版 Express、lodash、minimist、axios、serialize-javascript 等依赖风险 |
| `pom-vulnerable.xml` | Java / Maven | Spring、Jackson、Log4j、Commons Collections 等典型组件风险 |
| `expected-findings.md` | 演示说明 | 预期可讲解的风险点、演示流程和验收要点 |

## 推荐演示流程

1. 启动 DevSecOps 平台并进入新建扫描任务页面。
2. 选择扫描类型为 `SCA` 或依赖安全扫描。
3. 上传整个 `tests/sca_demo` 目录；如果平台只支持单文件上传，可依次上传各依赖清单。
4. 等待任务完成后进入报告详情页。
5. 演示以下能力：
   - 识别不同包管理器文件：pip、npm、Maven。
   - 展示组件名称、当前版本、漏洞编号、严重级别和修复版本。
   - 按严重级别统计风险数量。
   - 区分直接依赖与间接依赖（如果平台支持）。
   - 给出升级建议或安全版本范围。
   - 导出报告并用于整改闭环。

## 演示讲解建议

可以将该目录作为“历史项目依赖未升级”的案例：

- Python 服务使用旧版 Django、Flask、PyYAML 和 Jinja2。
- 前端或 Node 服务使用旧版 Express、lodash、axios 和 serialize-javascript。
- Java 服务使用旧版 Spring、Jackson、Log4j 和 Commons Collections。

扫描结果中如果出现 CVE、GHSA、PYSEC、OSV 等编号，都可以用于展示平台的漏洞情报聚合能力。不同 SCA 工具和漏洞数据库的命中结果会有差异，演示时以平台实际报告为准。

## 注意事项

- 不要执行 `pip install -r requirements-vulnerable.txt`、`npm install` 或 `mvn install`。
- 如果必须在隔离环境中验证第三方扫描器，请使用临时容器或无外网的测试环境。
- 演示完成后，可用 `expected-findings.md` 对照说明“发现风险、定位组件、给出修复建议、复扫验证”的完整闭环。
