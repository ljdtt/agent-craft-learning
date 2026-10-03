# 航空客服在线作品部署

这是基于 [Annyfee/agent-craft](https://github.com/Annyfee/agent-craft) 的个人学习实践版，原作者 Annyfee，许可证 MIT。云端作品展示多智能体转接、工具调用、会话记忆和流式输出。

## 已部署作品

- 在线体验：[ljdtt-agent-craft.streamlit.app](https://ljdtt-agent-craft.streamlit.app/)
- 仓库：[ljdtt/agent-craft-learning](https://github.com/ljdtt/agent-craft-learning)
- 运行配置：`main` 分支，入口 `m13_streamlit/s05_portfolio.py`，Python 3.11。
- 2026-10-04 在云端验证了退票、改签和天气流程；工具记录确认了三次专员转接，以及 `execute_refund`、`check_seat` 和 `get_weather` 的实际调用。
- 同日验证了跨轮记忆、第 5 轮后禁用输入、清空对话不恢复次数，以及新会话具有独立的 5 轮额度。分享设置已确认公开。

## 本地运行

使用 Python 3.11，在仓库根目录执行：

```powershell
python -m pip install -r m13_streamlit/requirements.txt
Copy-Item .env.example .env
# 在 .env 中填写 DeepSeek API Key，不要提交 .env。
python -m streamlit run m13_streamlit/s05_portfolio.py
```

如果已经有 `.env`，直接编辑现有文件，不要覆盖。云端入口只需要 `OPENAI_API_KEY`，不需要 LangSmith、OpenAI 追踪或高德 Key。

## Streamlit Community Cloud

1. 代码已上传到公开仓库 [ljdtt/agent-craft-learning](https://github.com/ljdtt/agent-craft-learning)。
2. 登录 [Streamlit Community Cloud](https://share.streamlit.io/)，连接拥有仓库管理权限的 GitHub 账户。
3. 创建应用，选择仓库、`main` 分支和入口 `m13_streamlit/s05_portfolio.py`。
4. 在 Advanced settings 中选择 **Python 3.11**，填写 Secrets：

```toml
OPENAI_API_KEY = "你的 DeepSeek API Key"
PORTFOLIO_GITHUB_URL = "https://github.com/ljdtt/agent-craft-learning"
```

5. 部署后检查聊天、转接、工具记录和次数限制。选择可用子域名，获得真实的 `https://名称.streamlit.app` 网址。
6. 在 README 添加已验证的在线体验网址。

Streamlit 优先读取入口目录下的 `requirements.txt`；该列表只安装作品所需的依赖。不需要根目录的全部 RAG 依赖。

真实 Key 只能放在平台 Secrets 或本地已忽略的配置文件中。`.streamlit/secrets.example.toml` 是空值模板，不能存放真实 Key。

## 演示内容和费用

- 固定用户画像：小何、杭州、白金会员和演示航班 CA1234。
- 退票工具返回模拟申请结果；改签工具返回模拟余票，不预订座位。
- 天气固定返回晴、25℃、风力3级，明确标注不是实时天气。
- 云端天气采用 Python 工具；本地 MCP 流程可运行模块 10～12。
- 一轮提问可能多次调用模型，用于转接、调用工具和生成回答。
- 每个浏览器会话最多 5 轮，每轮最多 300 字符。清空对话不恢复次数，失败请求也占一轮。
- 每轮最多执行 6 个模型步骤，每个步骤最多生成 600 tokens；客户端不自动重试，单次请求超时 30 秒，整体流式处理超时 90 秒。
- 刷新、更换浏览器或新建会话可能绕过会话限额，它不是全站费用硬上限。API 费用由部署者承担，公开分享前应准备自己能接受的预算。

## 会话和隐私

每位访客使用随机会话 ID 和独立的临时 SQLite 数据库。临时目录不可写时退回内存。对话文件不会上传 GitHub，服务重启后不保证保存。

清空对话删除当前历史并重置前台，已用次数保留。访客输入和历史会发送到 DeepSeek，请勿输入真实身份证、手机号或订单信息。

## 验证

```powershell
python -m unittest discover -s tests -v
```

测试在模型 HTTP 边界提供模拟流式响应，并运行实际 Agents SDK，验证限额、输入长度、访客隔离、历史清理、数据库回退、转接、工具、错误脱敏和缺密钥页面，不产生模型费用。

上线后用公开网址检查：退票 → 改签 → 杭州天气 → 用户画像 → 第五轮后禁用输入。缺密钥、认证失败或限流时应出现友好提示，不输出堆栈或 Key。

## 官方文档

- [部署应用](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [配置密钥](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [云端依赖查找](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)
