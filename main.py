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
    """LINE Messaging APIを使ってメッセージをプッシュ送信する"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("エラー: LINE_CHANNEL_ACCESS_TOKEN または LINE_USER_ID が未設定です。")
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
    if response.status_code != 200:
        print(f"LINE送信失敗: {response.status_code} {response.text}")
        response.raise_for_status()
    else:
        print("LINE通知の送信に成功しました。")

def check_books_and_notify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 1. ログイン画面を開く
        login_url = "https://ksucat2.kyoto-su.ac.jp/webopac/login.do?url=ufisnd.do%3Fredirect_page_id%3D15%26svcaction%3D_437%252CAskMenu_437"
        page.goto(login_url, wait_until="networkidle")
        page.wait_for_selector('input[name="userid"]', timeout=15000)

        # 2. ログイン情報を入力して送信
        page.fill('input[name="userid"]', LIB_USER_ID)
        page.fill('input[name="password"]', LIB_PASSWORD)

        login_button = page.locator('input[alt="ログイン"]')
        if login_button.count() > 0:
            login_button.first.click()
        else:
            page.press('input[name="password"]', 'Enter')

        page.wait_for_load_state("networkidle")

        # 3. 貸出一覧ページへ直接移動
        page.goto("https://ksucat2.kyoto-su.ac.jp/webopac/lenlst.do", wait_until="networkidle")

        # 4. テーブル内の全行をチェック
        rows = page.query_selector_all("table tr")
        book_list = []
        today = date.today()

        for row in rows:
            cols = row.query_selector_all("td")
            if not cols:
                continue

            col_texts = [col.inner_text().strip() for col in cols]
            row_full_text = " ".join(col_texts)

            # 行に含まれる日付 (YYYY/MM/DD) を抽出
            dates = re.findall(r'\b\d{4}/\d{2}/\d{2}\b', row_full_text)
            if not dates:
                continue

            # 1つ目の日付が「返却期限日」
            due_date_str = dates[0]
            due_date = datetime.strptime(due_date_str, "%Y/%m/%d").date()
            days_left = (due_date - today).days

            # 書誌事項（タイトル）を抽出
            title = "書籍"
            for t in col_texts:
                if "/" in t and ("著" in t or "訳" in t or "編" in t or "シリーズ" in t or "\n" in t):
                    # 「相対性理論入門講義 / 風間洋一 著...」からタイトル部分だけ取得
                    title = t.split("/")[0].strip()
                    break

            # 残り日数ごとのステータスアイコン
            if days_left < 0:
                badge = f"⚠️【期限超過 {abs(days_left)}日】"
            elif days_left == 0:
                badge = "🚨【本日返却日！】"
            elif days_left <= 3:
                badge = f"⏳【あと{days_left}日】"
            else:
                badge = f"📖【あと{days_left}日】"

            book_list.append({
                "badge": badge,
                "due_date": due_date_str,
                "title": title,
                "days_left": days_left
            })

        browser.close()

        # 5. LINE通知メッセージの組み立てと送信
        if book_list:
            # 返却日が近い順にソート
            book_list.sort(key=lambda x: x["days_left"])

            message_lines = [
                f"📚 図書館 貸出状況（全{len(book_list)}冊）",
                f"確認日: {today.strftime('%Y/%m/%d')}",
                "────────────────"
            ]

            for idx, b in enumerate(book_list, 1):
                item_str = (
                    f"{idx}. {b['badge']}\n"
                    f"・期限: {b['due_date']}\n"
                    f"・書名: {b['title']}"
                )
                message_lines.append(item_str)

            message_lines.append("────────────────")
            message = "\n".join(message_lines)

            print("=== 取得結果 ===")
            print(message)
            print("================")

            send_line_notification(message)
        else:
            msg = "📚 現在借りている本はありません。"
            print(msg)
            send_line_notification(msg)

if __name__ == "__main__":
    check_books_and_notify()
