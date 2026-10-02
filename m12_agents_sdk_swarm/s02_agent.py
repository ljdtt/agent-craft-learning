from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from openai import AsyncOpenAI
from agents.agent import Agent
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from m12_agents_sdk_swarm.s01_tools import execute_refund, check_seat,context_variables
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url="https://api.deepseek.com")
model = OpenAIChatCompletionsModel(model="deepseek-chat", openai_client=client)

# 连接模块10创建的本地天气 MCP Server
local_weather_servers = [
    MCPServerStreamableHttp(
        name="local_weather",
        params=MCPServerStreamableHttpParams(
            url="http://127.0.0.1:8001/mcp"
        )
    )
]




# === 1. 创建所有Agent ===

# 定义指令生成函数
def refund_instructions(context_variables):
    name = context_variables.get('user_name')
    flight = context_variables.get('flight_no')
    return f"""你是退票专员。
    始终使用中文回答。
    【客户信息】
    - 姓名: {context_variables.get('user_name')}
    - 航班号: {context_variables.get('flight_no')}

    【核心职责】
    1. 当用户表达退票意图时，立即调用 execute_refund 工具完成退票
    2. 不要问用户是否确认，直接执行
    3. 执行完工具后，告知用户退款状态

    【转接规则】
    - 如果用户改变主意想改签，转接到 ChangeAgent
    - 如果用户询问其他问题，转接到 TriageAgent
    - 退票完成后，询问用户是否还需要其他帮助

    【重要】你已经被转接过来，说明用户想退票，直接执行工具即可，不要犹豫！
    """

def change_instructions(context_variables):
    name = context_variables.get('user_name')
    flight = context_variables.get('flight_no')
    return f"""你是改签专员。
    始终使用中文回答。
    【客户信息】
    - 姓名: {context_variables.get('user_name')}
    - 航班号: {context_variables.get('flight_no')}

    【核心职责】
    1. 当用户表达改签意图时，立即调用 check_seat 工具查询座位
    2. 不要问用户是否确认，直接执行
    3. 执行完工具后，告知用户结果

    【转接规则】
    - 如果用户改变主意想退票，转接到 RefundAgent
    - 如果用户询问其他问题，转接到 TriageAgent
    - 改签完成后，询问用户是否还需要其他帮助

    【重要】你已经被转接过来，说明用户想改签，直接执行工具即可！
    """

def triage_instructions(context_variables):
    name = context_variables.get('user_name')
    flight = context_variables.get('flight_no')
    return f"""你是航空公司前台客服。
    始终使用中文回答。你就是综合服务专员；其他专员转回给你后，请直接接管并处理，不要再声称无法转接到综合服务专员。

    【客户信息】
    - 姓名: {context_variables.get('user_name')}
    - 航班号: {context_variables.get('flight_no')}
    
    【转接规则】
    1. 用户说"退票"、"退款"、"取消航班" → 刻转接到 RefundAgent
    2. 用户说"改签"、"换航班"、"改时间" → 转接到 ChangeAgent
    3. 用户查询天气时 → 必须调用 local_weather MCP Server
    4. 其他问题由你自己回答
    
    【重要】
    - 转接时要明确告知用户："我帮您转接到XX专员"
    - 不要重复询问用户意图，识别后立即转接
    """


# 退票专员
refund_agent = Agent(
    name="RefundAgent",
    instructions=refund_instructions(context_variables),
    tools=[execute_refund],
    model=model
)

# 改签专员
change_agent = Agent(
    name="ChangeAgent",
    instructions=change_instructions(context_variables),
    tools=[check_seat],
    model=model,
)

# 前台分诊员
triage_agent = Agent(
    name="TriageAgent",
    instructions=triage_instructions(context_variables),
    mcp_servers=local_weather_servers,
    model=model,
)

# === 2. 建立 Handoff 网络 ===

# 前台可转给两位专员
triage_agent.handoffs = [refund_agent, change_agent]

# 专员之间也可互相转接，并能回退到前台
refund_agent.handoffs = [change_agent, triage_agent]
change_agent.handoffs = [refund_agent, triage_agent]
