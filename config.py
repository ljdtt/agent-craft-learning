# 导入必要模块
import os
from pathlib import Path
from dotenv import load_dotenv

# 从项目根目录加载 .env，不依赖当前工作目录或本机绝对路径
ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

# ------------------- 2. 解决UUID v7警告（保留原项目逻辑） -------------------
try:
    from langsmith import uuid7
    import uuid
    uuid.uuid4 = uuid7
except ImportError:
    pass

# ------------------- 3. 屏蔽框架兼容性告警（保留原项目逻辑） -------------------
def silence_framework_warnings():
    import warnings
    import logging
    # 屏蔽TensorFlow/NumPy警告
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    warnings.filterwarnings('ignore')
    logging.getLogger('tensorflow').setLevel(logging.ERROR)
silence_framework_warnings()

# ------------------- 4. 读取API密钥并强制校验 -------------------
# 从.env读取变量，若为空则返回空字符串
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
AMAP_MAPS_API_KEY = os.getenv("AMAP_MAPS_API_KEY", "")
CHATGPT_API_KEY = os.getenv("CHATGPT_API_KEY", "")

# 只有启用 LangSmith 追踪时才强制要求对应密钥
LANGCHAIN_TRACING_ENABLED = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
if LANGCHAIN_TRACING_ENABLED and not LANGCHAIN_API_KEY:
    raise ValueError(
        "❌ 错误：LANGCHAIN_API_KEY 未从 .env 文件读取成功！\n"
        "请检查：\n"
        f"1. .env文件是否在项目根目录：{ENV_PATH}\n"
        "2. .env文件中是否正确填写了 LANGCHAIN_API_KEY=lsv2开头的密钥\n"
        "3. 密钥内部不能有空格、引号等特殊字符\n"
        "4. 变量名必须是 LANGCHAIN_API_KEY，中间是下划线，不是空格"
    )

# 【关键校验】OPENAI_API_KEY为空时也报错，避免后续模块运行失败
if not OPENAI_API_KEY:
    raise ValueError("❌ 错误：请在.env文件中设置 OPENAI_API_KEY！")

# ------------------- 5. 配置LangSmith追踪的环境变量 -------------------
# 自动设置追踪所需的环境变量，无需在业务脚本中重复配置
os.environ["LANGCHAIN_TRACING_V2"] = str(LANGCHAIN_TRACING_ENABLED).lower()
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "agent_craft_demo")
if LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY

