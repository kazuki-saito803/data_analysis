import streamlit as st
import msal
import os
from dotenv import load_dotenv
from tools import (
    get_file_list,
    fetch_onedrive_files,
    convert_to_dataframes,
    visualization_subplots
)
from agent import AgentState, app as langgraph_app

# ✅ .env 読み込み
load_dotenv()

CLIENT_ID = os.getenv("APPLICATION_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = "https://login.microsoftonline.com/consumers"
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = ["Files.ReadWrite"]

st.set_page_config(page_title="OneDrive × AI Dashboard", layout="wide")
st.title("📁 OneDrive × LangGraph × Streamlit")

# ✅ MSAL クライアント
msal_app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET
)

# -------------------- 認証 --------------------
if "access_token" not in st.session_state:
    code = st.query_params.get("code")
    if not code:
        login_url = msal_app.get_authorization_request_url(
            scopes=SCOPES, redirect_uri=REDIRECT_URI
        )
        st.markdown(f"[👉 Microsoft にログインする]({login_url})")
        st.stop()
    token_result = msal_app.acquire_token_by_authorization_code(
        code=code, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    if "access_token" not in token_result:
        st.error("❌ トークン取得に失敗しました")
        st.stop()
    st.session_state.access_token = token_result["access_token"]
    st.session_state.is_first_run = True

# -------------------- 初回のみ：State初期化 --------------------
if st.session_state.get("is_first_run", False):
    quantity_files = get_file_list(st.session_state.access_token)
    st.session_state.agent_state = AgentState(
        state="",
        quantity_files=quantity_files,
        quantity_file_contents={},
        quality_files=[],
        quality_file_contents={},
        answer="",
        predict_answer="",
        question="",
        selected_files=[],
        access_token=st.session_state.access_token,
    )
    st.session_state.messages = []
    st.session_state.dfs = None
    st.session_state.fig = None
    st.session_state.is_first_run = False

col1, col2 = st.columns(2)

# -------------------- 右：チャット（LangGraph連携） --------------------
with col2:
    st.subheader("💬 Chat Assistant")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    user_input = st.chat_input("質問を入力してください...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        # ✅ LangGraph実行
        state_dict = st.session_state.agent_state.dict()
        state_dict["question"] = user_input

        result = langgraph_app.invoke(state_dict)
        st.session_state.agent_state = AgentState(**result)

        reply = result.get("predict_answer") or result.get("answer") or "⚠ 応答なし"
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # ✅ ここで 📊 データ取得 ＆ グラフ作成
        if result.get("selected_files"):
            raw_csvs = fetch_onedrive_files(
                file_names=result["selected_files"],
                access_token=result["access_token"]
            )
            st.session_state.dfs = convert_to_dataframes(raw_csvs)
            st.session_state.fig = visualization_subplots(st.session_state.dfs)

        with st.chat_message("assistant"):
            st.write(reply)

# -------------------- 左：データ可視化 --------------------
with col1:
    st.subheader("📊 データの可視化")

    if st.session_state.fig:
        st.pyplot(st.session_state.fig)

    if st.session_state.dfs:
        st.subheader("📄 DataFrame 一覧")
        for name, df in st.session_state.dfs.items():
            st.write(f"### {name}")
            st.dataframe(df)