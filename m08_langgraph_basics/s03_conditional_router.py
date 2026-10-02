from config import OPENAI_API_KEY,LANGCHAIN_API_KEY
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, END,START
from langgraph.prebuilt import ToolNode
import os

# ========== 关键修改：关闭LangSmith追踪，彻底屏蔽403报错 ==========
# 把原来的 "true" 改为 "false"，脚本里的设置优先级最高，会覆盖config.py
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_PROJECT"] = "demo01"
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY

# LLM配置
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=OPENAI_API_KEY,
    base_url="https://api.deepseek.com"
)

# 工具定义
@tool
def get_weather(location):
    """模拟获取天气"""
    return f'{location}当前天气：23℃，晴，风力2级'


tools = [get_weather]
llm_with_tools = llm.bind_tools(tools)


# --- 核心组件:拆解AgentExecutor ---
def call_model(state:MessagesState):
    response = llm_with_tools.invoke(state['messages'])
    return {"messages":[response]}

tool_node = ToolNode(tools)

def should_continue(state:MessagesState):
    last_msg = state["messages"][-1]
    if hasattr(last_msg,"tool_calls") and last_msg.tool_calls:
        return "tools"
    return END


# --- 构建 ReAct 循环图---
workflow = StateGraph(MessagesState)
workflow.add_node("agent",call_model)
workflow.add_node("tools",tool_node)
workflow.add_edge(START,"agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools":"tools", END:END}
)
workflow.add_edge("tools","agent")
app = workflow.compile()

if __name__ == '__main__':
    # 触发工具
    result = app.invoke({"messages":[HumanMessage(content="北京天气如何?")]})
    print('工具调用结果:',result['messages'][-1].content)
    # 不触发工具
    result = app.invoke({"messages":HumanMessage(content="你好")})
    print('直接回答:',result['messages'][-1].content)
