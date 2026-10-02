# 🧩 模块说明：Streamlit 实战篇 - 构建 AI Agent Web 应用

> 📌 核心知识点：Streamlit 基础组件｜对话式 UI 设计｜Agents SDK 集成｜多智能体协作系统｜状态持久化与会话管理

---

### 个人学习作品版：`s05_portfolio.py`

新增的云端入口通过前台、退票和改签专员展示多智能体协作；天气使用 Python 演示工具，不依赖 `127.0.0.1:8001`。所有业务结果均为模拟。

```bash
python -m pip install -r m13_streamlit/requirements.txt
python -m streamlit run m13_streamlit/s05_portfolio.py
```

单次输入最多 300 字符，每个浏览器会话最多 5 轮；清空对话不恢复次数。请求失败也计入次数，避免重复失败请求增加费用。密钥通过 `.env` 或 Streamlit Secrets 配置。完整说明见 [云端部署说明](../docs/cloud-deployment.md)。

同目录 `requirements.txt` 仅供此作品版使用；原课程入口需要根目录的完整依赖。

---

### 1. `s01_st_basics.py` （Streamlit 基础组件）

全面介绍 Streamlit 的核心 UI 组件，为构建 AI Agent 应用打下基础。

- ✅ 掌握点：
  - 使用 `st.chat_input` 实现用户对话输入
  - 使用 `st.chat_message` 创建对话气泡，支持自定义头像
  - 使用 `st.status` 实现可折叠的中间步骤展示
  - 使用 `st.empty()` 创建动态占位符，实现实时内容更新
  - 使用 `st.session_state` 实现跨会话的状态持久化
  - 使用 `st.sidebar` 设计侧边栏布局
  - 使用 `st.rerun()` 触发页面重新渲染，保持 UI 与状态同步

- 输出：
  - 展示一个包含输入框、对话气泡、折叠状态栏、动态占位符的完整交互界面
  - 演示会话状态的管理和侧边栏的设计
  - 静态演示 `st.rerun()` 的使用场景和注意事项

> 💡 此文件是 Streamlit 的入门指南，适合初次接触 Streamlit 的开发者快速掌握核心组件。

---

### 2. `s02_st_layout_demo.py` （布局与页面配置）

演示 Streamlit 的页面布局配置和聊天界面的基础构建方式。

- ✅ 掌握点：
  - 使用 `st.set_page_config` 配置页面标题和布局模式
  - 实现 `layout="wide"` 宽屏布局，适合复杂应用场景
  - 使用 `st.sidebar` 构建侧边栏监控面板
  - 使用 `st.header`、`st.subheader`、`st.info` 设计侧边栏信息展示
  - 实现模拟的聊天历史展示流程

- 输出：
  - 一个带有专业标题和侧边栏监控面板的智能客服驾驶舱界面
  - 展示用户和助手的对话气泡模拟效果
  - 包含用户画像信息展示的侧边栏布局

> 💡 此示例展示了如何构建专业的管理驾驶舱界面，适合需要监控功能的 AI 应用场景。

---

### 3. `s03_agent_single_mvp.py` （单智能体 MVP 实现）

基于 Agents SDK 实现一个完整的单智能体客服系统，集成 OpenAI 兼容接口。

- ✅ 掌握点：
  - 配置 OpenAIChatCompletionsModel 和 AsyncOpenAI 客户端
  - 使用 DeepSeek 模型构建智能客服 Agent
  - 定义 Agent 的系统指令，包含业务逻辑判断（退票、改签等）
  - 使用 `st.spinner` 显示加载动画
  - 使用 `Runner.run_sync` 同步执行智能体任务
  - 实现聊天历史的状态管理和自动渲染

- 输出：
  - 一个可交互的智能航空客服助手
  - 支持退票申请、改签服务等业务场景
  - 完整的对话历史记录和上下文管理
  - 带侧边栏用户画像展示的监控界面

> 💡 这是构建 AI Agent Web 应用的基础模板，展示了如何将 Agents SDK 与 Streamlit 无缝集成。

---

### 4. `s04_agent_multi_session.py` （多智能体多会话系统）

基于 Agents SDK 构建完整的多智能体协作系统，实现智能路由和会话持久化。

- ✅ 掌握点：
  - 使用 `SQLiteSession` 实现对话历史的数据库持久化
  - 实现多智能体协作（TriageAgent、RefundAgent、ChangeAgent）
  - 使用 `MCP` 协议连接高德地图等外部服务
  - 实现智能体之间的动态转接和状态切换
  - 使用流式输出 `Runner.run_streamed` 实现实时响应
  - 捕获和处理智能体事件（工具调用、转接事件）
  - 实现会话管理和历史消息回放功能
  - 设计可复用的侧边栏渲染函数

- 输出：
  - 完整的智能航空客服多智能体系统
  - 自动根据用户需求转接至对应的专业坐席（退票专员、改签专员）
  - 实时展示工具调用日志和智能体转接过程
  - 支持会话历史持久化，页面刷新后依然保持对话上下文
  - 动态更新的驾驶舱监控界面，显示当前坐席、用户画像和会话统计

> 💡 这是接近生产环境的多智能体应用示例，展示了如何构建可扩展、可维护的复杂 AI Agent 系统。

---

### 🔔 全局注意事项

- **学习路径建议**：
  `s01.`（基础组件） → `s02.`（布局配置） → `s03.`（单智能体集成） → `s04.`（多智能体协作）
- 所有 `.py` 文件依赖根目录 `.env` 中的 `OPENAI_API_KEY`
- `s03` 和 `s04` 使用 DeepSeek API 作为 OpenAI 兼容端点
- `s04_agent_multi_session.py` 需要依赖 `m12_agents_sdk_swarm` 模块中的智能体定义
- 运行前确保已安装相关依赖：`streamlit`、`agents`、`openai`、`nest-asyncio`

- **运行方式**：
  ```bash
  cd m13_streamlit
  streamlit run s01_st_basics.py      # 基础组件演示
  streamlit run s02_st_layout_demo.py # 布局配置演示
  streamlit run s03_agent_single_mvp.py  # 单智能体 MVP
  streamlit run s04_agent_multi_session.py # 多智能体系统
  ```

---

### 💡 **建议**

- 尝试扩展 `s04_agent_multi_session.py`，添加更多专业坐席（如投诉处理、行李查询）
- 实验不同的 Agent 路由逻辑，优化用户体验
- 将真实的服务 API（如航班查询、支付系统）集成到系统中
- 探索 SQLiteSession 的高级用法，如会话分析、对话导出等
- 考虑添加语音输入、多语言支持等扩展功能
- 研究 Streamlit 的自定义组件，构建更丰富的可视化界面
