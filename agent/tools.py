# tools.py
from langchain_core.tools import tool
import requests
from dotenv import load_dotenv
import pandas as pd
from io import StringIO
import matplotlib.pyplot as plt

load_dotenv()

# ✅ OneDrive内のファイル名一覧を取得
def get_file_list(access_token: str, folder_path="Test"):
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}:/children"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"❌ OneDrive API エラー: {response.status_code} - {response.text}")

    files = response.json().get("value", [])
    return [item["name"] for item in files]

# ✅ 指定ファイルを OneDrive から取得
def fetch_onedrive_files(file_names: list, access_token: str, folder_path="Test") -> dict:
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}:/children"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise Exception(f"❌ OneDrive API エラー: {res.status_code} - {res.text}")

    result = {}
    files = res.json().get("value", [])

    for name in file_names:
        match = next((f for f in files if f["name"] == name), None)
        if not match:
            result[name] = "⚠ 見つかりません"
            continue

        download_url = match["@microsoft.graph.downloadUrl"]
        content = requests.get(download_url).content.decode("utf-8", errors="ignore")
        result[name] = content

    return result

# ✅ CSV文字列 → pandas DataFrameへ変換
def convert_to_dataframes(file_contents: dict) -> dict:
    dataframes = {}

    for filename, content in file_contents.items():
        if isinstance(content, str) and content.startswith("⚠"):
            dataframes[filename] = content
            continue

        try:
            dataframes[filename] = pd.read_csv(StringIO(content))
        except Exception as e:
            dataframes[filename] = f"❌ DataFrame変換失敗: {e}"

    return dataframes

# ✅ サブプロットで可視化s
def visualization_subplots(dataframes: dict):
    """
    各DataFrameごとに「棒グラフ＋円グラフ＋ヒストグラム」を1行にまとめて表示する
    layout = n_files × 3 のサブプロット
    """
    plt.rcParams['font.family'] = 'Hiragino Sans'

    files = list(dataframes.keys())
    n = len(files)

    if n == 0:
        return None

    fig, axs = plt.subplots(n, 3, figsize=(15, 5 * n))
    if n == 1:
        axs = [axs]

    for i, file in enumerate(files):
        df = dataframes[file]

        if isinstance(df, str):
            for ax in axs[i]:
                ax.set_title(f"{file} (Error)", fontsize=12)
                ax.text(0.5, 0.5, df, ha='center', va='center')
            continue

        # ✅ (1) セクター別含み損益
        sector_profit = df.groupby("sector")["unrealized_profit"].sum()
        sector_profit.plot(kind="bar", ax=axs[i][0])
        axs[i][0].set_title(f"{file}：セクター別含み損益")
        axs[i][0].set_xlabel("Sector")
        axs[i][0].set_ylabel("Unrealized Profit")
        axs[i][0].tick_params(axis='x', rotation=45)

        # ✅ (2) 資産クラス別 保有評価額の円グラフ
        try:
            df["eval_value"] = df["quantity"] * df["price_per_unit"]
            asset_value = df.groupby("asset_class")["eval_value"].sum()
            asset_value.plot(kind="pie", ax=axs[i][1], autopct="%.1f%%")
            axs[i][1].set_title(f"{file}：資産クラス比率")
            axs[i][1].set_ylabel("")
        except Exception:
            axs[i][1].text(0.5, 0.5, "円グラフ描画不可", ha="center")

        # ✅ (3) 取引数量ヒストグラム
        try:
            df["quantity"].plot(kind="hist", bins=10, ax=axs[i][2])
            axs[i][2].set_title(f"{file}：数量分布（ヒストグラム）")
            axs[i][2].set_xlabel("Quantity")
        except Exception:
            axs[i][2].text(0.5, 0.5, "ヒストグラム描画不可", ha="center")

    plt.tight_layout()
    return fig

# ✅ 単体実行用
if __name__ == "__main__":
    print("⚠ このファイルは app.py から呼び出される想定です")