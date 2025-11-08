import os
import ast
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage
from tools import fetch_onedrive_files

# =============================
# 環境変数読み込み
# =============================
load_dotenv()

# =============================
# AgentState の定義
# =============================
class AgentState(BaseModel):
    state: str = ""                                  # 現在の状態
    question: str = ""                               # ユーザーの質問

    quantity_files: list = Field(default_factory=list, description="量的データファイル一覧")
    quantity_file_contents: dict = Field(default_factory=dict)

    quality_files: list = Field(default_factory=list, description="質的データファイル一覧")
    quality_file_contents: dict = Field(default_factory=dict)

    selected_files: list = Field(default_factory=list)  # ユーザーが選んだファイル

    answer: str = ""           # LLMの返答（ファイル選択）
    predict_answer: str = ""   # LLMの最終分析結果

    access_token: str          # OneDrive API用トークン

# =============================
# LLM（Google Gemini）
# =============================
llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL"),
    temperature=0.5,
    transport="rest"
)

# =============================
# ① ファイル選択ノード
# =============================
def select_file_node(state: AgentState) -> AgentState:
    system_prompt = f"""
    あなたはデータ選定アシスタントです。
    以下のファイル一覧から、ユーザーの依頼内容に関係のあるものだけを選んでください。
    
    ✅ 出力ルール：
    ・Python の list 形式のみで回答してください（例：['finance.csv', 'healthcare.csv']）
    ・文章やJSON形式は禁止です

    選択可能ファイル：{state.quantity_files}
    """
    messages = [SystemMessage(content=system_prompt),
                HumanMessage(content=state.question)]
    state.answer = llm.invoke(messages).content
    state.state = "file_selected"
    return state

# ✅ ファイル選択結果の形式が正しいかチェック
def is_list_or_not(state):
    try:
        parsed = ast.literal_eval(state.answer)
        return "list" if isinstance(parsed, list) else "other"
    except Exception:
        return "other"

# =============================
# ② 選択されたファイルの中身を取得
# =============================
def quantity_files_node(state: AgentState) -> AgentState:
    try:
        selected = ast.literal_eval(state.answer)
        if not selected:
            state.predict_answer = "⚠ ファイルが選択されませんでした。"
            state.state = "no_files_selected"
            return state
        state.selected_files = selected
    except Exception:
        state.predict_answer = "⚠ ['finance.csv'] のようにリスト形式で指定してください。"
        state.state = "error_parsing_list"
        return state

    state.quantity_file_contents = fetch_onedrive_files(
        file_names=state.selected_files,
        access_token=state.access_token
    )
    state.state = "fetched_quantity_files"
    return state

# =============================
# ③ 質的データ（任意・未使用ならスキップ可）
# =============================
def quality_files_node(state: AgentState) -> AgentState:
    if not state.quality_files:
        state.state = "skip_quality"
        return state

    state.quality_file_contents = fetch_onedrive_files(
        file_names=state.quality_files,
        access_token=state.access_token,
        folder_path="Test2"
    )
    state.state = "fetched_quality_files"
    return state

# =============================
# ④ 最終分析ノード
# =============================
def predict_node(state: AgentState) -> AgentState:
    system_prompt = f"""
    あなたはデータサイエンティストです。
    以下のデータに基づいて、定量的・定性的な分析を行い、洞察とアクションを出してください。

    --- 量的データ ---
    {state.quantity_file_contents}

    --- 質的データ（任意）---
    {state.quality_file_contents}

    ✅ 出力フォーマット：
    ### ✅ インサイト（事実・傾向）
    -
    ### 💡 仮説・示唆
    -
    ### ⚠ リスク・懸念点
    -
    ### 🚀 次のアクション提案
    -
    """
    messages = [SystemMessage(content=system_prompt),
                HumanMessage(content=state.question)]
    state.predict_answer = llm.invoke(messages).content
    state.state = "predict_done"
    return state

# =============================
# ⑤ エラーノード（無限ループ防止）
# =============================
def error_node(state: AgentState) -> AgentState:
    state.state = "error"
    state.predict_answer = "⚠ 正しい形式でファイル名を出力してください（例：['finance.csv']）"
    return state

# =============================
# LangGraph 構築
# =============================
graph = StateGraph(AgentState)

graph.add_node("select_file_node", select_file_node)
graph.add_node("quantity_files_node", quantity_files_node)
graph.add_node("quality_files_node", quality_files_node)
graph.add_node("predict_node", predict_node)
graph.add_node("error_node", error_node)

graph.add_edge(START, "select_file_node")

graph.add_conditional_edges(
    "select_file_node",
    is_list_or_not,
    {
        "list": "quantity_files_node",
        "other": "error_node"
    }
)

graph.add_edge("quantity_files_node", "quality_files_node")
graph.add_edge("quality_files_node", "predict_node")
graph.add_edge("predict_node", END)
graph.add_edge("error_node", END)

app = graph.compile()