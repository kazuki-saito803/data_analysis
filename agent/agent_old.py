# agent.py
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage

# from tools import connect_onedrive, fetch_files_from_onedrive

load_dotenv()

# === 状態管理 ===
class AgentState(BaseModel):
    question: str = Field(default="こんにちは")
    quantity_file_list: list | None = None
    quality_file_list: list | None = None
    selected_files: list | None = None
    file_contents: dict | None = None
    answer: str | None = None
    access_token: str

# === LLM設定 ===
llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL"),
    temperature=0,
    transport="rest"
)

# ① OneDriveのファイル一覧取得
def list_files_node(state: AgentState):
    # state.file_list = connect_onedrive.run("Test")
    return state

# ② LLMで「使うファイルはどれ？」を判断
def analyze_node(state: AgentState):
    prompt = f"""
    ユーザー: {state.question}
    フォルダ内のファイル一覧: {state.file_list}

    ユーザーがファイル内容を見たがっている場合、
    必要なファイル名だけを JSON で返してください:

    例:
    {{"files": ["finance.csv"]}}

    説明文は禁止。JSON形式のみ出力してください。
    """
    res = llm.invoke([HumanMessage(content=prompt)]).content
    print("LLM応答:", res)

    try:
        parsed = json.loads(res)
        state.selected_files = parsed.get("files", [])
    except:
        state.selected_files = []
    return state

# ③ ファイルを実際に取得
def fetch_files_node(state: AgentState):
    if state.selected_files:
        # state.file_contents = fetch_files_from_onedrive(state.selected_files, "Test")
        state.answer = f"✅ 取得したファイル: {state.selected_files}"
    else:
        state.answer = "📂 必要なファイルはないと判断しました"
    return state

# ④ 応答
def respond_node(state: AgentState):
    return state

# === グラフ構築 ===
def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("list_files", list_files_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("fetch_files", fetch_files_node)
    graph.add_node("respond", respond_node)

    graph.add_edge(START, "list_files")
    graph.add_edge("list_files", "analyze")
    graph.add_edge("analyze", "fetch_files")
    graph.add_edge("fetch_files", "respond")
    graph.add_edge("respond", END)

    return graph.compile()

if __name__ == "__main__":
    # app = build_graph()
    # result = app.invoke(AgentState(question="Testフォルダのfinance.csvを見せて"))

    # print("📌 回答:", result.get("answer"))
    # print("🎯 選択されたファイル:", result.get("selected_files"))
    # print("📂 取得した内容:", result.get("file_contents"))
    files = ["finance.csv", "tecnology.csv"]
    system_prompt = f"""あなたは、ユーザープロンプトに応じて適切なファイルのみを選対して返すAIアシスタントです。選択できるファイルは次のものです。{files}
    また、返答する内容はファイル名を格納したリスト形式のオブジェクトのみとしてください。
    例：ユーザーからの質問
    「テクノロジーに関するファイルを取得してください。」
    あなたの回答
    ['tecnology.csv']
    """
    user_prompt = "金融のファイルを取得してください。"
    messages = [SystemMessage(content=system_prompt),
              HumanMessage(content=user_prompt)]
    result = llm.invoke(messages)
    print(result)