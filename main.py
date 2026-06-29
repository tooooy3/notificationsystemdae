import os
from datetime import datetime
import requests

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    SHEET_NAMES = ["シート1", "シート2", "シート3", "シート4", "シート5"]
    tasks = []
    
    for sheet_name in SHEET_NAMES:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        try:
            response = requests.get(url)
            response.encoding = 'utf-8'
            lines = response.text.splitlines()
            if not lines:
                continue
            for line in lines[1:]:
                row = [val.strip('"') for val in line.split(',')]
                if len(row) >= 2 and row[0] and row[1]:
                    tasks.append({"title": row[0], "due_date": row[1], "sheet": sheet_name})
        except Exception as e:
            print(f"エラー: {e}")
    return tasks

def send_line_message():
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    LINE_USER_ID = os.getenv("LINE_USER_ID")
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        return

    all_tasks = get_tasks_from_sheets()
    today = datetime.now()
    reminders = []
    
    for task in all_tasks:
        try:
            due_date = datetime.strptime(task["due_date"], "%Y/%m/%d")
            days_left = (due_date - today).days + 1
            if 0 <= days_left <= 3:
                reminders.append(f"・【あと{days_left}日】[{task['sheet']}] {task['title']} ({task['due_date']})")
        except Exception:
            continue

    if not reminders:
        return

    task_list = "\n".join(reminders)
    message_text = f"📚【課題締め切り通知】\n\n期限が近づいている課題があります！\n\n{task_list}\n\n早めに終わらせましょう！"

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message_text}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    send_line_message()
