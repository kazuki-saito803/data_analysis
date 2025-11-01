import streamlit as st
import msal
import requests
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("APPLICATION_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = "https://login.microsoftonline.com/consumers"
REDIRECT_URI = "http://localhost:8501/"
SCOPES = ["Files.ReadWrite"]

# MSAL クライアント設定
app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
)

# ✅ セッション変数の初期化
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "selected_files" not in st.session_state:
    st.session_state.selected_files = []
if "file_list" not in st.session_state:
    st.session_state.file_list = []  # ← APIで取得したファイルを保存しておく

col1, col2 = st.columns(2)

# -------------------------
# ✅ ① 左カラム（認証 + ファイル一覧取得のみ）
# -------------------------
with col1:
    st.header("📁 OneDrive 認証 & ファイル一覧")

    query_params = st.query_params

    # 認証されていない & コードもない → 認証URLへ自動リダイレクト
    if st.session_state.access_token is None and "code" not in query_params:
        auth_url = app.get_authorization_request_url(
            scopes=SCOPES, redirect_uri=REDIRECT_URI
        )
        st.write("🔄 Microsoft認証にリダイレクトしています…")
        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">',
                    unsafe_allow_html=True)

    # リダイレクト後 → トークンに変換
    elif st.session_state.access_token is None and "code" in query_params:
        result = app.acquire_token_by_authorization_code(
            code=query_params["code"],
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        if "access_token" in result:
            st.session_state.access_token = result["access_token"]
            st.success("✅ ログイン成功！")

    # ✅ トークンがあるときだけファイル一覧を取得（初回のみ）
    if st.session_state.access_token and not st.session_state.file_list:
        folder_path = "Test"
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}:/children"
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            st.session_state.file_list = response.json().get("value", [])
        else:
            st.error("❌ OneDriveフォルダの取得に失敗")
            st.stop()

    # ✅ ここでは「表示」と「チェックの保持だけ」
    for file in st.session_state.file_list:
        name = file["name"]
        checked = st.checkbox(name, key=f"chk_{name}")
        if checked:
            if name not in st.session_state.selected_files:
                st.session_state.selected_files.append(name)
        else:
            if name in st.session_state.selected_files:
                st.session_state.selected_files.remove(name)

# -------------------------
# ✅ ② 右カラム（送信ボタン → ここでだけ処理を実行）
# -------------------------
with col2:
    st.header("✅ 選択されたファイル")

    st.write(st.session_state.selected_files)

    if st.button("送信（処理開始）"):
        if not st.session_state.selected_files:
            st.warning("⚠ ファイルが選択されていません")
        else:
            st.success("📤 処理実行します")
            st.write("対象ファイル：", st.session_state.selected_files)
            # ⚠ この中でのみAPI処理、ファイルダウンロードなど行う