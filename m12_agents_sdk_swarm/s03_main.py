import asyncio
from openai.types.responses import ResponseTextDeltaEvent
from agents.run import Runner
from m12_agents_sdk_swarm.s02_agent import triage_agent,local_weather_servers
from m12_agents_sdk_swarm.s01_tools import context_variables

# 不启用Chatgpt官方提供的Tracing(无需配置api_key)
from agents.tracing import set_tracing_disabled
set_tracing_disabled(True)

# 启用Chatgpt官方提供的Tracing(需要配置api_key)
# from config import CHATGPT_API_KEY
# from agents.tracing import set_tracing_export_api_key
# set_tracing_export_api_key(CHATGPT_API_KEY)


async def main():
    print('✈️ 客服系统启动...\n')
    messages = []  # 对话历史
    cur_agent = triage_agent  # 当前Agent

    try:
        await local_weather_servers[0].connect()
        print("✅ MCP Server (local_weather) connected.")
    except Exception as e:
        print(f"⚠️  Failed to connect MCP Server: {e}")

    try:
        while True:
            # 获取用户输入
            user_input = input("\nUser: ")
            if user_input == "quit":
                break
            messages.append({"role": "user", "content": user_input})
    
            # 启动流式响应
            result = Runner.run_streamed(
                cur_agent,
                input=messages,
                context=context_variables
            )
    
            # 状态变量
            current_agent_name = None  # 当前Agent名称
            is_printing = False  # 是否正在打印文本
    
            # 处理事件流
            async for event in result.stream_events():
    
                # 事件1: 文本流（逐Token输出）
                if event.type == "raw_response_event":
                    if isinstance(event.data, ResponseTextDeltaEvent):
                        # 第一次打印时显示Agent标签
                        if not is_printing:
                            agent_label = f"[{current_agent_name}]" if current_agent_name else ""
                            print(f"🤖 {agent_label} ", end="", flush=True)
                            is_printing = True
                        # 逐字输出
                        print(event.data.delta, end="", flush=True)
    
                # 事件2: Agent切换
                elif event.type == "agent_updated_stream_event":
                    new_agent = event.new_agent.name
                    if current_agent_name is None:
                        # 第一次设置Agent名称
                        current_agent_name = new_agent
                    else:
                        # Agent发生切换
                        if is_printing:
                            print()  # 先换行
                            is_printing = False
                        print(f"🔀 [系统]: {current_agent_name} → {new_agent}")
                        current_agent_name = new_agent
    
                # 事件3: 工具调用
                elif event.type == "run_item_stream_event":
                    # 工具调用开始
                    if event.name == "tool_called":
                        if is_printing:
                            print()  # 先换行
                            is_printing = False
                        tool_name = event.item.raw_item.name
                        tool_args = event.item.raw_item.arguments # 获取工具参数 调试需要时可加入
                        # 区分转接工具和业务工具
                        if tool_name.startswith("transfer_"):
                            print(f"📞 [转接]: {tool_name}")
                        else:
                            print(f"🔧 [工具]: {tool_name}")
    
                    # 工具输出结果
                    elif event.name == "tool_output":
                        print(f"✅ [结果]: {event.item.output}")
                        is_printing = False
    
            # 结束本轮，确保换行
            if is_printing:
                print()
    
            # 更新状态
            messages = result.to_input_list()  # 获取完整对话历史
            cur_agent = result.last_agent  # 获取最后激活的Agent
    
    
    finally:
        await local_weather_servers[0].cleanup()
        print("✅ MCP Server connection closed.")
if __name__ == '__main__':
    asyncio.run(main())
