import os
from datetime import datetime
import requests
import json
import re

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    url_meta = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json"
    tasks = []
    
    try:
        res = requests.get(url_meta)
        match = re.search(r'google\.visualization\.Query\.setResponse\((.*)\);', res.text)
        if not match:
            return tasks
        
        data = json.loads(match.group(1))
        sheet_names = []
        if 'table' in data and 'cols' in data['table']:
            html_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
            html_res = requests.get(html_url)
            sheet_names = re.findall(r'class="sheet-name">([^<]+)', html_res.text)
            
        if not sheet_names:
            sheet_names = ["シート1"]
            
        sheet_names = list(dict.fromkeys(sheet_names))

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
            
            # 今日から3日以内の課題をピックアップ
            if 0 <= days_left <= 3:
                # 期限が近い順に並び替えるために days_left も一緒に保存
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

    # ★残り日数が少ない順（期限が近い順）に並び替える
    reminders.sort(key=lambda x: x["days_left"])

    # LINE用のテキストを作成
    formatted_lines = []
    for item in reminders:
        # ★日数に応じて「焦る色」の絵文字に変える
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
