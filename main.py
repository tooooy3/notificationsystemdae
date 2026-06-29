import os
from datetime import datetime, timedelta
import requests

def get_tasks_from_sheets():
    # ★ここにあなたのスプレッドシートIDを貼り付けてください
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # 共有リンクを知っている全員が閲覧可能であれば、CSV形式で一発でダウンロードできます
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv"
    
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        lines = response.text.splitlines()
        
        tasks = []
        # 1行目は見出し（課題名, 締切日）なので飛ばす
        for line in lines[1:]:
            # CSVのクォーテーションを外して分割
            row = [val.strip('"') for val in line.split(',')]
            if len(row) >= 2:
                tasks.append({"title": row[0], "due_date": row[1]})
        return tasks
    except Exception as e:
        print(f"スプレッドシートの読み込みエラー: {e}")
        return []

def send_line_message():
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    LINE_USER_ID = os.getenv("LINE_USER_ID")

    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("エラー: 環境変数が設定されていません。")
        return

    # スプレッドシートから課題一覧を取得
    all_tasks = get_tasks_from_sheets()
    
    # 【判定ロジック】今日から「3日以内」の課題を抽出する
    today = datetime.now()
    reminders = []
    
    for task in all_tasks:
        try:
            # スプレッドシートの日付（YYYY/MM/DD）を日付データに変換
            due_date = datetime.strptime(task["due_date"], "%Y/%m/%d")
            # 締切までの残り日数を計算
            days_left = (due_date - today).days + 1
            
            # 期限が過ぎておらず、かつ3日以内の場合のみリストに入れる
            if 0 <= days_left <= 3:
                reminders.append(f"・【あと{days_left}日】{task['title']} ({task['due_date']})")
        except Exception:
            # 日付の形式が違う行などはスキップ
            continue

    # 通知する課題がなければプログラムを終了
    if not reminders:
        print("期限が近い課題はありませんでした。")
        return

    # LINEに送る文章の作成
    task_list = "\n".join(reminders)
    message_text = f"📚【課題締め切り通知】\n\n期限が近づいている課題があります！\n\n{task_list}\n\n早めに終わらせましょう！"

    # LINE APIへ送信
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message_text}]
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("LINE通知の送信に成功しました！")
    else:
        print(f"エラーが発生しました: {response.status_code}\n{response.text}")

if __name__ == "__main__":
    send_line_message()