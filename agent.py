import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
import traceback
from IPython.display import Image, display


load_dotenv()

# ▼ 状態管理
class AgentState(BaseModel):
    question: str = Field(default="こんにちは", description="question from user")
    answer: str | None = Field(default=None, description="answer by llm")
    state: str = Field(default="start", description="agent state")

GEMINI_MODEL = os.getenv("GEMINI_MODEL")
API_KEY = os.getenv("GOOGLE_API_KEY")

if not GEMINI_MODEL or not API_KEY:
    print("❌ GEMINI_MODEL or GOOGLE_API_KEY が設定されていません")
    exit()

# ▼ LLM設定 + タイムアウト
llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    temperature=0,
    timeout=20,  # ← 秒。返答がないなら止める
    transport="rest"
)

# ▼ ノード処理
def llm_node(state: AgentState):
    try:
        messages = [
            SystemMessage(content="あなたは優秀なAIアシスタントです。"),
            HumanMessage(content=state.question),
        ]
        response = llm.invoke(messages)  # ここで止まることがある
        state.answer = response.content  # 必ず.contentを使う
    except Exception:
        state.answer = "⚠ エラーが発生しました"
        print(traceback.format_exc())
    return state

def add_comment(state: AgentState):
    state.answer = state.answer + "これはadd_commentノードに入りました。"
    state.state = "finish"
    return state

def judge(state: AgentState):
    query = f"""
    以下の会話の回答が出ました。

    回答: {state.answer}

    この会話を続けるべきなら "continue"
    もう十分に回答済みで終了してよいなら "finish"
    のどちらかだけを返してください。
    """.strip()
    result = llm.invoke([HumanMessage(content=query)])
    decision = result.content.strip().lower()
    if "finish" in decision:
        state.state = "finish"
    else:
        state.state = "continue"
    return state

# ▼ Flowの構築
def agent_run():
    graph = StateGraph(AgentState)
    graph.add_node("agent", llm_node)
    graph.add_node("comment", add_comment)
    graph.add_node("judge", judge)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", "judge")
    graph.add_conditional_edges(
        "judge",
        lambda state: state.state,
        {
            "finish": END,
            "continue": "comment"
        }
    )
    app = graph.compile()
    
    display(Image(app.get_graph().draw_mermaid_png()))

    # 実行
    result = app.invoke(AgentState(question="AIとは何ですか？"))
    print("■ question:", result.get("question"))
    print("■ answer:", result.get("answer"))

if __name__ == "__main__":
    agent_run()