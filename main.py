import os
from datetime import datetime
import requests

def get_tasks_from_sheets():
    # あなたのスプレッドシートID
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # 読み込みたいシート（タブ）の名前をここに並べます
    # ※スプレッドシートの下のタブ名と完全に一致させてください
    SHEET_NAMES = ["シート1", "シート2", "シート3", "シート4", "シート5"]
    
    tasks = []
    
    for sheet_name in SHEET_NAMES:
        # シート名を指定してCSV形式でダウンロードするURL
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        
        try:
            response = requests.get(url)
            response.encoding = 'utf-8'
            lines = response.text.splitlines()
            
            if not lines:
                continue
                
            # 1行目は見出し（課題名, 締切日）なので飛ばす
            for line in lines[1:]:
                row = [val.strip('"') for val in line.split(',')]
                if len(row) >= 2 and row[0] and row[1]:
                    # どのシートの課題かわかるように、シート名も一緒に保存する
                    tasks.append({"title": row[0], "due_date": row[1], "sheet": sheet_name})
        except Exception as e:
            print(f"シート「{sheet_name}」の読み込みエラー: {e}")
            
    return tasks

def send_line_message():
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    LINE_USER_ID = os.getenv("LINE_USER_ID")

    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("エラー: 環境変数が設定されていません。")
        return

    # すべてのシートから課題一覧を取得
    all_tasks = get_tasks_from_sheets()
    
    # 今日から「3日以内」の課題を抽出する
    today = datetime.now()
    reminders = []
    
    for task in all_tasks:
        try:
            due_date = datetime.strptime(task["due_date"], "%Y/%m/%d")
            days_left = (due_date - today).days + 1
            
            if 0 <= days_left <= 3:
                # LINEのメッセージに「[シート名]」を表示させて、どこに書いた課題かわかりやすくします
                reminders.append(f"・【あと{days_left}日】[{task['sheet']}] {task['title']} ({task['due_date']})")
        except Exception:
            continue

    if not reminders:
        print("期限が近い課題はありませんでした。")
        return

    task_list = "\n".join(reminders)
    message_text = f"📚【課題締め切り通知】\n\n期限が近づいている課題があります！\n\n{task_list}\n\n早めに終わらせましょう！"

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