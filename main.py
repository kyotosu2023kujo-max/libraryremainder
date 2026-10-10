import os
import re
from datetime import datetime, date
from playwright.sync_api import sync_playwright

LIB_USER_ID = os.environ.get("LIB_USER_ID")
LIB_PASSWORD = os.environ.get("LIB_PASSWORD")

def check_books_and_notify():
    with sync_playwright() as p:
        # ヘッドレスブラウザ起動
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. ログイン画面へアクセス
        # ※ 実際のログインURLに置き換えてください
        login_url = "https://ksucat2.kyoto-su.ac.jp/webopac/login.do"
        page.goto(login_url)

        # フォームのセレクタに合わせて入力・送信
        page.fill('input[name="userid"]', LIB_USER_ID)
        page.fill('input[name="password"]', LIB_PASSWORD)
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle")

        # 2. 貸出一覧ページに移動
        # ログイン直後に遷移しない場合は直接指定
        # page.goto("https://ksucat2.kyoto-su.ac.jp/webopac/lenlst.do")

        # 3. テーブルから本と返却期限を取得
        # 行（tr）を走査
        rows = page.query_selector_all("table tr")
        
        warning_books = []
        today = date.today()

        for row in rows:
            text = row.inner_text()
            # 日付（YYYY/MM/DD または YYYY-MM-DD）のパターンを探す
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', text)
            if not date_match:
                continue

            due_date_str = date_match.group(1).replace("-", "/")
            due_date = datetime.strptime(due_date_str, "%Y/%m/%d").date()
            days_left = (due_date - today).days

            # 3日以内または期限切れの本を抽出
            if days_left <= 3:
                # 簡易的に行の1行目や書誌事項からタイトルを切り出す
                cols = row.query_selector_all("td")
                title = cols[3].inner_text().strip().split("\n")[0] if len(cols) > 3 else "書籍"
                
                status_str = f"【あと{days_left}日】" if days_left >= 0 else f"【超過 {abs(days_left)}日】"
                warning_books.append(f"{status_str} {due_date_str}返却\n・{title}")

        browser.close()

        # 4. 対象があればLINE通知
        if warning_books:
            message = "📚 図書館 本の返却リマインド\n\n" + "\n\n".join(warning_books)
            send_line_notification(message)
            print("通知を送信しました。")
        else:
            print("直近で返却期限の本はありません。")

if __name__ == "__main__":
    check_books_and_notify()
