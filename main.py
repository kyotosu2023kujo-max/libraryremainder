import os
from playwright.sync_api import sync_playwright
from datetime import datetime
import requests

USER_ID = os.environ.get("LIB_USER_ID")
PASSWORD = os.environ.get("LIB_PASSWORD")
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL") # LINEやDiscordのURL

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # ログインページへ移動してログイン処理
    page.goto("https://ksucat2.kyoto-su.ac.jp/...") # 実際のURL
    page.fill('input[name="username"]', USER_ID)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    
    # 貸出一覧ページを開く
    page.goto("https://ksucat2.kyoto-su.ac.jp/webopac/lenlst.do") # 貸出一覧URL
    
    # テーブルから行を取得（書誌事項、返却期限など）
    rows = page.query_selector_all("table tr")
    # ここで各本の「返却期限」と「書誌事項（タイトル）」を抽出して期限判定
    ...
