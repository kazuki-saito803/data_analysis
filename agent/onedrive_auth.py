# onedrive_auth.py
import msal, os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("APPLICATION_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = "https://login.microsoftonline.com/consumers"
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = ["Files.ReadWrite"]

app = msal.ConfidentialClientApplication(
    CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
)

def get_access_token_via_cli():
    """CLIで実行する際の auth_code 入力方式"""
    auth_url = app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)
    print("以下のURLにブラウザでアクセスし、認証後の code を入力してください：")
    print(auth_url)
    code = input("code: ")
    token = app.acquire_token_by_authorization_code(code, SCOPES, REDIRECT_URI)
    return token.get("access_token", None)