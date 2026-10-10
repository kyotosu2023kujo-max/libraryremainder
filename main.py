import os
import re
from datetime import datetime, date
import requests
from playwright.sync_api import sync_playwright

LIB_USER_ID = os.environ.get("LIB_USER_ID")
LIB_PASSWORD = os.environ.get("LIB_PASSWORD")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line_notification(text: str):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("LINEのトークンまたはユーザーIDが設定されていません。")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

def check_books_and_notify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 1. ログイン画面へアクセス
        login_url = "https://ksucat2.kyoto-su.ac.jp/webopac/login.do?url=ufisnd.do%3Fredirect_page_id%3D15%26svcaction%3D_437%252CAskMenu_437"
        page.goto(login_url, wait_until="networkidle")

        # フォームの待機
        page.wait_for_selector('input[name="userid"]', timeout=15000)

        # 2. ログイン情報入力
        page.fill('input[name="userid"]', LIB_USER_ID)
        page.fill('input[name="password"]', LIB_PASSWORD)

        # 3. ログイン実行
        login_button = page.locator('input[alt="ログイン"]')
        if login_button.count() > 0:
            login_button.first.click()
        else:
            page.press('input[name="password"]', 'Enter')

        page.wait_for_load_state("networkidle")

        # 4. 貸出一覧テーブルの取得
        rows = page.query_selector_all("table tr")
        all_books = []
        today = date.today()

        for row in rows:
            text = row.inner_text()
            # 日付（YYYY/MM/DD または YYYY-MM-DD）のパターンを抽出
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', text)
            if not date_match:
                continue

            due_date_str = date_match.group(1).replace("-", "/")
            due_date = datetime.strptime(due_date_str, "%Y/%m/%d").date()
            days_left = (due_date - today).days

            cols = row.query_selector_all("td")
            title = "書籍"
            for col in cols:
                col_text = col.inner_text().strip()
                if "/" in col_text and ("著" in col_text or "訳" in col_text or "編" in col_text):
                    title = col_text.split("\n")[0]
                    break
                elif len(col_text) > 5 and not re.search(r'\d{4}/\d{2}/\d{2}', col_text):
                    title = col_text.split("\n")[0]

            # 残り日数に応じたバッジ表示
            if days_left < 0:
                badge = f"⚠️【期限超過 {abs(days_left)}日】"
            elif days_left == 0:
                badge = "🚨【本日返却日】"
            elif days_left <= 3:
                badge = f"⏳【あと{days_left}日】"
            else:
                badge = f"📖【あと{days_left}日】"

            book_info = f"{badge} 返却期限: {due_date_str}\n{title}"
            all_books.append(book_info)

        browser.close()

        # 5. 全本の表示およびLINE送信
        if all_books:
            message = f"📚 借りている本の一覧（全{len(all_books)}冊）\n\n" + "\n\n".join(all_books)
            print("=== 取得した本の一覧 ===")
            print(message)
            print("========================")
            send_line_notification(message)
            print("LINE通知を送信しました。")
        else:
            print("現在借りている本はありません。")

if __name__ == "__main__":
    check_books_and_notify()
