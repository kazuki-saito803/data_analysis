import streamlit as st
import msal
import requests
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("APPLICATION_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = "https://login.microsoftonline.com/consumers"
REDIRECT_URI = "http://localhost:8501/"
SCOPES = ["Files.ReadWrite"]

# ▼ セッション変数初期化
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "selected_files" not in st.session_state:
    st.session_state.selected_files = []
if "file_list" not in st.session_state:
    st.session_state.file_list = None

# ▼ MSALアプリ設定
app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET
)

col1, col2 = st.columns(2)

# ======================
# 📂 左カラム：認証 & ファイル選択
# ======================
with col1:
    st.header("📂 OneDrive 認証 & ファイル選択")
    query_params = st.query_params

    if st.session_state.access_token is None and "code" not in query_params:
        auth_url = app.get_authorization_request_url(
            scopes=SCOPES, redirect_uri=REDIRECT_URI
        )
        st.write("🔄 Microsoft認証ページへ移動中...")
        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)

    elif st.session_state.access_token is None and "code" in query_params:
        result = app.acquire_token_by_authorization_code(
            code=query_params["code"],
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        if "access_token" in result:
            st.session_state.access_token = result["access_token"]
            st.success("✅ ログイン成功")
        else:
            st.error("❌ トークン取得に失敗しました")
            st.stop()

    if st.session_state.access_token:
        url = "https://graph.microsoft.com/v1.0/me/drive/root:/Test:/children"
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            files = response.json().get("value", [])
            st.session_state.file_list = files

            st.subheader("✅ ファイル選択 (Testフォルダ)")
            for file in files:
                name = file["name"]
                if st.checkbox(name, key=name):
                    if name not in st.session_state.selected_files:
                        st.session_state.selected_files.append(name)
                else:
                    if name in st.session_state.selected_files:
                        st.session_state.selected_files.remove(name)
        else:
            st.error("❌ フォルダ情報取得に失敗しました")
            st.write(response.text)

# ======================
# 📊 右カラム：ファイル内容 → 円グラフ描画
# ======================
with col2:
    st.header("📊 投資データの可視化")
    st.write("選択中のファイル:", st.session_state.selected_files)

    if st.button("📤 データ分析開始"):  # ← ここで初めて処理開始
        if not st.session_state.selected_files:
            st.warning("⚠ ファイルが選択されていません")
        else:
            for file in st.session_state.file_list:
                if file["name"] in st.session_state.selected_files:
                    if "@microsoft.graph.downloadUrl" not in file:
                        st.warning(f"⚠ {file['name']} のURLが取得できません")
                        continue

                    csv_url = file["@microsoft.graph.downloadUrl"]
                    csv_data = requests.get(csv_url).content
                    df = pd.read_csv(StringIO(csv_data.decode("utf-8")))

                    st.subheader(f"📄 {file['name']} の内容（先頭5行）")
                    st.dataframe(df.head())

                    # ✅ Sector & total_cost で円グラフ（投資比率）
                    if "sector" in df.columns and "total_cost" in df.columns:
                        grouped = df.groupby("sector")["total_cost"].sum()

                        fig, ax = plt.subplots()
                        ax.pie(grouped, labels=grouped.index, autopct='%1.1f%%', startangle=90)
                        ax.set_title(f"{file['name']} - 投資比率（Sector別）")
                        ax.axis("equal")
                        st.pyplot(fig)

                    else:
                        st.warning(f"⚠ {file['name']} に 'sector' または 'total_cost' 列がありません")