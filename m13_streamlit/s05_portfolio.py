"""Run: python -m streamlit run m13_streamlit/s05_portfolio.py"""

import asyncio
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from m13_streamlit.portfolio_backend import (  # noqa: E402
    MAX_INPUT_LENGTH, MAX_TURNS, PortfolioState, run_turn,
)

st.set_page_config(page_title="小何的 Agent 学习作品", page_icon="✈️", layout="wide")

load_dotenv(PROJECT_ROOT / ".env")
try:
    api_key = st.secrets.get("OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    github_url = st.secrets.get("PORTFOLIO_GITHUB_URL", "") or os.getenv("PORTFOLIO_GITHUB_URL", "")
except FileNotFoundError:
    api_key = os.getenv("OPENAI_API_KEY", "")
    github_url = os.getenv("PORTFOLIO_GITHUB_URL", "")

st.caption("PERSONAL LEARNING PORTFOLIO · AI AGENT")
st.title("✈️ 智能航空客服")
st.write("体验前台、退票专员和改签专员如何协作，看见 AI 转接和调用工具的过程。")
st.info("这是教学演示：退票、改签和天气均为模拟数据，不操作真实订单，也不提供实时天气。")

with st.expander("关于这份作品", expanded=False):
    st.markdown(
        "这是小何跟随 [Annyfee/agent-craft](https://github.com/Annyfee/agent-craft) "
        "课程完成的学习实践。基础课程与代码由 **Annyfee** 原创，按 **MIT License** 授权。\n\n"
        "个人实践包括 Windows/Conda 环境适配、依赖整理、运行问题修复，"
        "以及这个支持限额体验的云端展示版。云端天气使用 Python 工具，"
        "源码中的模块 10～12 展示本地 MCP 服务与客户端。"
    )

if not api_key:
    st.warning("在线对话尚未配置模型密钥，请作品维护者在 Streamlit Secrets 中设置 OPENAI_API_KEY。")
    st.markdown("配置和部署方法见仓库中的 `docs/cloud-deployment.md`。")
    st.caption("基于 Annyfee/agent-craft 学习实践 · MIT License")
    st.stop()

if "portfolio" not in st.session_state:
    st.session_state.portfolio = PortfolioState()
state = st.session_state.portfolio

AGENT_LABELS = {
    "TriageAgent": "前台 · TriageAgent",
    "RefundAgent": "退票专员 · RefundAgent",
    "ChangeAgent": "改签专员 · ChangeAgent",
}

with st.sidebar:
    st.header("客服驾驶舱")
    agent_status = st.empty()
    agent_status.info(AGENT_LABELS[state.current_agent])
    st.metric("剩余体验轮数", f"{state.remaining_turns} / {MAX_TURNS}")
    st.progress(state.used_turns / MAX_TURNS)
    st.caption("每个浏览器会话最多 5 轮。一次提问可能包含多次模型调用，失败的请求也计入次数。")
    st.divider()
    st.subheader("演示用户")
    st.json({"姓名": "小何", "会员": "白金会员", "城市": "杭州", "航班": "CA1234"})
    st.metric("对话消息数", len(state.messages))
    if state.memory_only:
        st.caption("本次对话使用内存记录。")
    if st.button("清空对话", use_container_width=True):
        try:
            asyncio.run(state.clear())
        except Exception:
            st.warning("历史记录清理遇到问题，新的对话已重新初始化。")
        st.rerun()
    st.caption("清空对话不恢复次数；会话记录不保证在刷新或服务重启后保留。")
    st.divider()
    if github_url.startswith("https://github.com/ljdtt/"):
        st.link_button("查看 GitHub 源码", github_url, use_container_width=True)
    else:
        st.caption("GitHub 源码仓库正在准备发布。")
    st.link_button("原作者课程", "https://github.com/Annyfee/agent-craft", use_container_width=True)

st.caption("可以试试：“我想退票” → “我改主意了，想改签” → “杭州天气怎么样？”")
st.caption("请勿输入真实身份证、手机号或订单信息。")

for message in state.messages:
    with st.chat_message(message["role"]):
        if message.get("success") is False:
            st.warning(message["content"])
        else:
            st.markdown(message["content"])
        if message.get("logs"):
            with st.expander("查看转接与工具记录"):
                for log in message["logs"]:
                    st.text(log)

if state.remaining_turns == 0:
    st.warning("本会话的 5 轮体验已用完，仍可查看对话和工具记录。")

prompt = st.chat_input(
    "请输入问题（最多 300 字）", max_chars=MAX_INPUT_LENGTH,
    disabled=state.remaining_turns == 0,
)
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        reply_placeholder = st.empty()
        with st.status("客服正在处理…", expanded=True) as status:
            try:
                outcome = asyncio.run(run_turn(
                    state, prompt, api_key,
                    on_text=reply_placeholder.markdown,
                    on_log=status.write,
                    on_agent=lambda name: agent_status.info(AGENT_LABELS[name]),
                ))
                reply_placeholder.markdown(outcome["content"])
                status.update(label="处理完成" if outcome["success"] else "本轮未完成",
                              state="complete" if outcome["success"] else "error", expanded=False)
            except ValueError as error:
                st.warning(str(error))
        st.rerun()

st.divider()
st.caption("基于 Annyfee/agent-craft 学习实践 · MIT License · 制作与适配：小何（ljdtt）")
