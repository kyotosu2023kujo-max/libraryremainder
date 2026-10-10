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

        page.wait_for_selector('input[name="userid"]', timeout=15000)

        # 2. ログイン
        page.fill('input[name="userid"]', LIB_USER_ID)
        page.fill('input[name="password"]', LIB_PASSWORD)

        login_button = page.locator('input[alt="ログイン"]')
        if login_button.count() > 0:
            login_button.first.click()
        else:
            page.press('input[name="password"]', 'Enter')

        page.wait_for_load_state("networkidle")

        # 3. 貸出一覧の各行を解析
        rows = page.query_selector_all("table tr")
        all_books = []
        today = date.today()

        for row in rows:
            cols = row.query_selector_all("td")
            if not cols:
                continue

            # 各セルのテキストを取得
            col_texts = [col.inner_text().strip() for col in cols]
            row_full_text = " ".join(col_texts)

            # 行の中に日付が含まれているかチェック (YYYY/MM/DD)
            dates = re.findall(r'\b\d{4}/\d{2}/\d{2}\b', row_full_text)
            if not dates:
                continue

            # 1つ目の日付が「返却期限日」（2つ目は貸出日）
            due_date_str = dates[0]
            due_date = datetime.strptime(due_date_str, "%Y/%m/%d").date()
            days_left = (due_date - today).days

            # 「書誌事項」セル（スラッシュや改行を含むタイトル文字列）を探す
            title = "書籍"
            for t in col_texts:
                if "/" in t and ("著" in t or "訳" in t or "編" in t or "シリーズ" in t or "\n" in t):
                    title = t.split("\n")[0].strip()
                    break

            # 状態に応じたマーク
            if days_left < 0:
                badge = f"⚠️【期限超過 {abs(days_left)}日】"
            elif days_left == 0:
                badge = "🚨【本日返却日】"
            elif days_left <= 3:
                badge = f"⏳【あと{days_left}日】"
            else:
                badge = f"📖【あと{days_left}日】"

            book_info = f"{badge} 返却期日: {due_date_str}\n{title}"
            all_books.append(book_info)

        browser.close()

        # 4. ログ出力 & LINE送信
        if all_books:
            message = f"📚 借りている本の一覧（全{len(all_books)}冊）\n\n" + "\n\n".join(all_books)
            print("=== 取得結果 ===")
            print(message)
            print("================")
            send_line_notification(message)
            print("LINE通知を送信しました。")
        else:
            print("現在借りている本はありません。")

if __name__ == "__main__":
    check_books_and_notify()
