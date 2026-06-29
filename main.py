import os
from datetime import datetime
import requests
import json
import re

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # 【新機能】スプレッドシートのメタデータから、今あるすべてのシート名を全自動で取得するURL
    url_meta = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json"
    tasks = []
    
    try:
        res = requests.get(url_meta)
        # Google特有のゴミ文字を削って純粋なデータにする
        match = re.search(r'google\.visualization\.Query\.setResponse\((.*)\);', res.text)
        if not match:
            return tasks
        
        data = json.loads(match.group(1))
        
        # スプレッドシートが持っている「すべてのシート名」を自動でリストにする
        # ※これで「シート1」やそれ以外のどんな名前のタブも自動検知します
        sheet_names = []
        if 'table' in data and 'cols' in data['table']:
            # データの構造からシート名を割り出す裏ワザ的な処理
            html_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
            html_res = requests.get(html_url)
            sheet_names = re.findall(r'class="sheet-name">([^<]+)', html_res.text)
            
        if not sheet_names:
            sheet_names = ["シート1"] # 万が一のセーフティ
            
        sheet_names = list(dict.fromkeys(sheet_names)) # 重複を消す
        print(f"検知されたシート一覧: {sheet_names}")

        # 自動で見つけたシートを1つずつ読み込む
        for sheet_name in sheet_names:
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
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
