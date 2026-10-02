import sys
import os
import asyncio
import nest_asyncio
import uuid
from agents import Runner, set_tracing_disabled, SQLiteSession
from openai.types.responses import ResponseTextDeltaEvent

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from m12_agents_sdk_swarm.s01_tools import context_variables
from m12_agents_sdk_swarm.s02_agent import triage_agent, local_weather_servers

nest_asyncio.apply()
set_tracing_disabled(True)

# 生成/获取动态 Session ID
if "session_id" not in st.session_state:
	st.session_state.session_id = f"session_{uuid.uuid4().hex[:8]}"


mcp_status = "✅ 本地天气 MCP（提问时连接）"

st.set_page_config(page_title="智能客服驾驶舱", layout="wide")
st.title("✈️ 智能航空客服 Multi-Agent 系统")
st.caption(f"🚀 实战三：基于 Agents SDK 的多智能体协作 (ID: {st.session_state.session_id})") # 小字体显示文本

# 初始化持久化 Session
if "session" not in st.session_state:
	# 使用绝对路径定位数据库，确保跨环境稳定性
	PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

	st.session_state.session = SQLiteSession( # 持久化内存，将AI对话历史搬到数据库中
		session_id=st.session_state.session_id,
		db_path=os.path.join(PROJECT_ROOT, "m13_streamlit", "conversations.db")
	)

if "display_messages" not in st.session_state: # 存储对话记录
	st.session_state.display_messages = []

if "tool_logs_history" not in st.session_state: # 存储工具调用记录
	st.session_state.tool_logs_history = []


# 封装侧边栏渲染函数，以便在初次加载和转接发生时，都能向同一个占位符刷新内容
def render_agent_status(placeholder, agent):
	name = agent.name
	if name == "TriageAgent":
		placeholder.info("当前坐席: 前台 TriageAgent")
	elif name == "RefundAgent":
		placeholder.success("当前坐席: 退票专员 RefundAgent 🚨")
	elif name == "ChangeAgent":
		placeholder.warning("当前坐席: 改签专员 ChangeAgent 🔄")


with st.sidebar:
	st.header("🖥️ 驾驶舱监控")

	# 确保有大脑（session_state）记住当前 Agent
	if "current_agent" not in st.session_state:
		st.session_state.current_agent = triage_agent

	# 当代码执行到对应位置时，自动更新上方侧边栏内容
	agent_status_placeholder = st.empty()

	# 初始渲染：基于当前state里的Agent
	render_agent_status(agent_status_placeholder, st.session_state.current_agent)

	st.subheader("👤 用户画像")
	st.json(context_variables)

	st.subheader("🔌 MCP 状态")
	st.caption(mcp_status)

	st.subheader("📊 会话统计")
	st.metric("消息数", len(st.session_state.display_messages))

	if st.button("🗑️ 清空对话"):
		asyncio.run(st.session_state.session.clear_session()) # 调用SQLiteSession对象的clear_session的方法，删除所有session_id等于当前ID的记录
		st.session_state.session_id = f"session_{uuid.uuid4().hex[:8]}" # 生成新的session_id
		st.session_state.display_messages = [] # 重置UI缓存
		st.session_state.tool_logs_history = []
		st.session_state.current_agent = triage_agent
		st.rerun()

# 渲染历史消息
for i, msg in enumerate(st.session_state.display_messages):
	avatar = "👤" if msg["role"] == "user" else "🤖"
	with st.chat_message(msg["role"], avatar=avatar):
		st.write(msg["content"])
		if i < len(st.session_state.tool_logs_history) and st.session_state.tool_logs_history[i]: # 确保列表索引存在且实际工具调用有记录
			with st.expander("🔧 查看工具调用", expanded=False): # 默认折叠
				for log in st.session_state.tool_logs_history[i]:
					st.caption(log)

prompt = st.chat_input("请输入您的问题")

if prompt:
	st.session_state.display_messages.append({"role": "user", "content": prompt})
	st.session_state.tool_logs_history.append([]) # 提前占座，保证索引顺序

	with st.chat_message("user", avatar="👤"): # 直接写入气泡
		st.write(prompt)

	with st.chat_message("assistant", avatar="🤖"):
		message_placeholder = st.empty() # 先占位，AI思考后再填入

	with st.status("Agent 正在思考...", expanded=True) as status:
		async def process_stream():
			mcp_server = local_weather_servers[0]
			await mcp_server.connect()
			status.write("🔌 已连接本地天气 MCP")
			try:
				stream = Runner.run_streamed(
					st.session_state.current_agent,
					input=prompt, # 问题
					context=context_variables, # 全局上下文
					session=st.session_state.session # 读:从数据库提取聊天记录/写:回复结束，自动将新一轮对话存入数据库
				)

				# 收集局部变量，再一起叠加到全局变量中
				reply = "" # 回复内容累加器
				tool_logs = [] # 工具日志收集

				current_agent_name = st.session_state.current_agent.name

				async for event in stream.stream_events(): # 流式事件
					if event.type == "raw_response_event":
						if isinstance(event.data, ResponseTextDeltaEvent):
							delta = event.data.delta or "" # 提取新字符
							reply += delta
							message_placeholder.write(reply) # 实时刷新UI

					# 当agent转换时
					elif event.type == "agent_updated_stream_event":
						new_agent = event.new_agent
						if current_agent_name != new_agent.name:
							log_msg = f"🔀 转接: {current_agent_name} → {new_agent.name}"
							status.write(log_msg) # 写入折叠栏
							tool_logs.append(log_msg)

							# 1. 更新“大脑”（状态持久化）
							st.session_state.current_agent = new_agent
							# 2. 实时更新“脸面”（让侧边栏占位符立刻变色/变字）
							render_agent_status(agent_status_placeholder, new_agent)

							current_agent_name = new_agent.name

					elif event.type == "run_item_stream_event":
						if event.name == "tool_called":
							tool_name = event.item.raw_item.name # 提取被调用工具的名字
							log_msg = f"🔧 调用: {tool_name}"
							status.write(log_msg) # 写入折叠栏
							tool_logs.append(log_msg)

				return reply, tool_logs # 返回完整回复的字符串与收集到的动作日志
			finally:
				await mcp_server.cleanup()


		reply, tool_logs = asyncio.run(process_stream())
		status.update(label="✅ 处理完成", state="complete", expanded=False) # 标识处理成功

	# 将(本轮)对话记录/工具调用，分别存入(总)对话记录/工具调用
	st.session_state.display_messages.append({"role": "assistant", "content": reply})
	st.session_state.tool_logs_history.append(tool_logs)
