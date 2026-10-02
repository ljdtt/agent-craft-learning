from typing import TypedDict
from langgraph.graph import StateGraph, END, START
import os

# 从项目根目录的 .env 读取 LangSmith 配置，避免把密钥写进源码
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "agent_craft_demo")

if not os.getenv("LANGCHAIN_API_KEY"):
    raise ValueError("请先在 .env 中配置 LANGCHAIN_API_KEY")

# 状态定义
class State(TypedDict):
    count: int

# 节点定义
def node_a(state: State):
    print(f"[Node A]收到状态: {state}")
    return {"count": state["count"] + 1}

def node_b(state: State):
    print(f"[Node B]收到状态: {state}")
    return {"count": state["count"] + 1}

# 构建线性流程
workflow = StateGraph(State)
workflow.add_node("A", node_a)
workflow.add_node("B", node_b)
workflow.add_edge(START, "A")
workflow.add_edge("A", "B")
workflow.add_edge("B", END)

# 编译并执行
app = workflow.compile()
print("---开始执行---")
result = app.invoke({"count": 0})
print("最终状态:", result)
