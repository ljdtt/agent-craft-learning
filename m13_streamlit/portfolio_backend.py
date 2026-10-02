"""Cloud portfolio: isolated chat state, limited requests and simulated tools."""

import asyncio
import sqlite3
import tempfile
import uuid
import weakref
from pathlib import Path

from agents import Agent, ModelSettings, RunConfig, Runner, SQLiteSession, function_tool
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI, AuthenticationError, RateLimitError
from openai.types.responses import ResponseTextDeltaEvent

MAX_TURNS = 5
MAX_INPUT_LENGTH = 300


def _release_resources(session, directory):
    # The finalizer owns resources, but must not retain the PortfolioState itself.
    session.close()
    if directory is not None:
        directory.cleanup()


class PortfolioState:
    """One visitor's history and quota; clearing history never refunds attempts."""

    def __init__(self):
        self.used_turns = 0
        self.current_agent = "TriageAgent"
        self.messages = []
        self.session_id = uuid.uuid4().hex
        self.memory_only = False
        self._directory = None
        self.session = self._new_session()
        self._finalizer = weakref.finalize(self, _release_resources, self.session, self._directory)

    def _new_session(self):
        try:
            if self._directory is None:
                self._directory = tempfile.TemporaryDirectory(prefix="agent-portfolio-")
            path = Path(self._directory.name) / "conversation.db"
            session = SQLiteSession(self.session_id, db_path=path)
            self.memory_only = False
            return session
        except (OSError, sqlite3.Error):
            self.memory_only = True
            return SQLiteSession(self.session_id, db_path=":memory:")

    @property
    def remaining_turns(self):
        return max(0, MAX_TURNS - self.used_turns)

    def start_turn(self, prompt):
        # Check the raw length too: padding must not bypass the input limit.
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("请输入一个问题。")
        if len(prompt) > MAX_INPUT_LENGTH:
            raise ValueError(f"每次最多输入 {MAX_INPUT_LENGTH} 个字符。")
        if self.remaining_turns == 0:
            raise ValueError("本会话的 5 轮体验已用完。")
        self.used_turns += 1
        return prompt.strip()

    async def clear(self):
        try:
            await self.session.clear_session()
        finally:
            self._finalizer.detach()
            self.session.close()
            self.session_id = uuid.uuid4().hex
            self.messages = []
            self.current_agent = "TriageAgent"
            self.session = self._new_session()
            self._finalizer = weakref.finalize(self, _release_resources, self.session, self._directory)

    def close(self):
        self._finalizer()

    def use_memory(self):
        self._finalizer.detach()
        self.session.close()
        self.session = SQLiteSession(self.session_id, db_path=":memory:")
        self.memory_only = True
        self._finalizer = weakref.finalize(self, _release_resources, self.session, self._directory)


@function_tool
def execute_refund() -> str:
    """模拟退款申请，仅返回教学结果，不操作真实订单或资金。"""
    return "【模拟操作】CA1234 退款申请演示成功；未提交真实申请，未扣款或退款。"


@function_tool
def check_seat() -> str:
    """模拟查询明日航班的座位余量，不预订或改签真实航班。"""
    return "【模拟查询】CA1234 明日航班尚有余票；教学固定数据，未预订座位或执行改签。"


@function_tool
def get_weather(city: str) -> str:
    """获取城市的模拟天气，用于演示工具调用，不能作为实时天气依据。"""
    return f"【模拟天气】{city}：晴，25℃，风力3级。教学固定数据，并非实时天气。"


def build_agents(client):
    model = OpenAIChatCompletionsModel(model="deepseek-chat", openai_client=client)
    settings = ModelSettings(max_tokens=600, parallel_tool_calls=False)
    common = (
        "始终用中文回答。这里是基于教学项目制作的航空客服演示。"
        "演示用户是小何（白金会员），居住杭州，演示航班CA1234。"
        "小何是客户的名字，不是你的名字。"
        "所有工具都是模拟操作；必须说明模拟性质，不能声称办理了真实订单、退款、预订或改签。"
        "只根据实际工具结果回答天气和业务结果，不能编造已执行的操作。"
    )
    triage = Agent(
        name="TriageAgent", model=model, model_settings=settings,
        instructions=common + "你是前台，也是综合服务专员。退票转给RefundAgent，"
        "改签转给ChangeAgent；天气问题必须使用get_weather；其他问题直接回答。"
        "专员转回后直接接管，不要再找其他综合服务专员。",
        tools=[get_weather],
    )
    refund = Agent(
        name="RefundAgent", model=model, model_settings=settings,
        instructions=common + "你是退票专员。用户已经表达退票意图或被转接来退票时，"
        "立即使用execute_refund演示一次，不要再次要求确认，"
        "按模拟结果回答。改签转给ChangeAgent；天气及其他问题转回TriageAgent。",
        tools=[execute_refund],
    )
    change = Agent(
        name="ChangeAgent", model=model, model_settings=settings,
        instructions=common + "你是改签专员。用户已经表达改签意图或被转接来改签时，"
        "立即使用check_seat模拟查询余票，不要再次要求确认，"
        "只提供模拟余票信息，不声称已预订或改签。退票转给RefundAgent；"
        "天气及其他问题转回TriageAgent。",
        tools=[check_seat],
    )
    triage.handoffs = [refund, change]
    refund.handoffs = [change, triage]
    change.handoffs = [refund, triage]
    return {agent.name: agent for agent in (triage, refund, change)}


async def run_turn(state, prompt, api_key, on_text=None, on_log=None, on_agent=None):
    """Reserve quota before any HTTP request; restore memory on failed runs."""
    prompt = state.start_turn(prompt)
    state.messages.append({"role": "user", "content": prompt, "logs": []})
    previous_items = []
    previous_agent = state.current_agent
    logs = []
    stream = None
    reply = ""

    def log(value):
        logs.append(value)
        if on_log:
            on_log(value)

    try:
        previous_items = await state.session.get_items()
        async with AsyncOpenAI(
            api_key=api_key, base_url="https://api.deepseek.com",
            timeout=30, max_retries=0,
        ) as client:
            agents = build_agents(client)
            stream = Runner.run_streamed(
                agents[state.current_agent], input=prompt, session=state.session,
                max_turns=6, run_config=RunConfig(tracing_disabled=True),
            )
            try:
                async with asyncio.timeout(90):
                    async for event in stream.stream_events():
                        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                            reply += event.data.delta or ""
                            if on_text:
                                on_text(reply)
                        elif event.type == "agent_updated_stream_event":
                            name = event.new_agent.name
                            if name != state.current_agent:
                                log(f"转接：{state.current_agent} → {name}")
                                state.current_agent = name
                                if on_agent:
                                    on_agent(name)
                        elif event.type == "run_item_stream_event":
                            if event.name == "tool_called":
                                log(f"调用工具：{event.item.raw_item.name}")
                            elif event.name == "tool_output":
                                log(f"工具结果：{event.item.output}")
            finally:
                if not stream.is_complete:
                    stream.cancel()
                    async for _ in stream.stream_events():
                        pass
            reply = str(stream.final_output or reply)
        outcome = {"role": "assistant", "content": reply, "logs": logs, "success": True}
    except Exception as error:
        state.current_agent = previous_agent
        # A partial tool call must not leave an unmatched tool in future history.
        try:
            await state.session.clear_session()
            await state.session.add_items(previous_items)
        except (OSError, sqlite3.Error):
            state.use_memory()
            await state.session.add_items(previous_items)
        if isinstance(error, AuthenticationError):
            message = "模型服务认证失败，请联系作品维护者检查配置。"
        elif isinstance(error, RateLimitError):
            message = "模型服务额度不足或请求过多，请稍后再试。"
        else:
            message = "本轮体验未完成，模型服务或演示工具暂时不可用，请稍后再试。"
        outcome = {"role": "assistant", "content": message, "logs": logs, "success": False}
        if on_agent:
            on_agent(state.current_agent)
    state.messages.append(outcome)
    return outcome
