import os
from datetime import datetime
import requests
import json
import re

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # htmlviewから今あるシート名を確実に引っこ抜く
    html_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
    tasks = []
    
    try:
        html_res = requests.get(html_url)
        html_res.encoding = 'utf-8'
        sheet_names = re.findall(r'class="sheet-name">([^<]+)', html_res.text)
            
        if not sheet_names:
            # 代替案：公開データからシート名を探す
            url_meta = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json"
            res = requests.get(url_meta)
            match = re.search(r'google\.visualization\.Query\.setResponse\((.*)\);', res.text)
            if match:
                data = json.loads(match.group(1))
                if 'table' in data and 'cols' in data['table']:
                    sheet_names = ["シート1", "シート2", "シート3", "シート4", "シート5"] # 予測セーフティ
        
        if not sheet_names:
            sheet_names = ["シート1"]
            
        sheet_names = list(dict.fromkeys(sheet_names))
        print(f"検知されたシート一覧: {sheet_names}")

        for sheet_name in sheet_names:
            # tqエンドポイントではなく、一番確実なexport用のURL（キャッシュされない形式）を使用
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&sheet={sheet_name}"
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
                reminders.append({
                    "days_left": days_left,
                    "sheet": task["sheet"],
                    "title": task["title"],
                    "due_date": task["due_date"]
                })
        except Exception:
            continue

    if not reminders:
        return

    reminders.sort(key=lambda x: x["days_left"])

    formatted_lines = []
    for item in reminders:
        if item["days_left"] <= 1:
            color_emoji = f"🔴あと{item['days_left']}日"
        else:
            color_emoji = f"🟡あと{item['days_left']}日"
        formatted_lines.append(f"・【{color_emoji}】[{item['sheet']}] {item['title']} ({item['due_date']})")

    task_list = "\n".join(formatted_lines)
    message_text = f"📚【課題締め切り通知】\n\n期限が近づいている課題があります！\n\n{task_list}\n\n早めに終わらせましょう！"

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message_text}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    send_line_message()
