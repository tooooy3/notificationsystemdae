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
        res.encoding = 'utf-8'
        
        match = re.search(r'google\.visualization\.Query\.setResponse\((.*)\);', res.text)
        if not match:
            return tasks
            
        raw_data = json.loads(match.group(1))
        
        html_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
        html_res = requests.get(html_url)
        html_res.encoding = 'utf-8'
        sheet_names = re.findall(r'class="sheet-name">([^<]+)', html_res.text)

        if not sheet_names:
            sheet_names = ["シート1", "シート2", "シート3", "シート4", "シート5"]
            
        sheet_names = list(dict.fromkeys(sheet_names))

        for sheet_name in sheet_names:
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                continue
                
            lines = response.text.splitlines()
            if not lines:
                continue
                
            for line in lines[1:]:
                row = [val.strip('"') for val in line.split(',')]
                if len(row) >= 2 and row[0] and row[1]:
                    tasks.append({"title": row[0], "due_date": row[1], "sheet": sheet_name})
                    
    except Exception as e:
        print(f"データ取得エラー: {e}")
        
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
            clean_date = re.sub(r'[^0-9/]', '', task["due_date"])
            due_date = datetime.strptime(clean_date, "%Y/%m/%d")
            days_left = (due_date - today).days + 1
            
            # 今日から5日後までの課題をすべて対象にする
            if 0 <= days_left <= 5:
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

    # 仕切り線を綺麗に1本にするためにここを修正しました！
    formatted_lines = []
    for item in reminders:
        # 日数で3色（赤・黄・緑）に色分け
        if item["days_left"] <= 1:
            color_emoji = f"🔴【あと{item['days_left']}日】"
        elif item["days_left"] <= 3:
            color_emoji = f"🟡【あと{item['days_left']}日】"
        else:
            color_emoji = f"🟢【あと{item['days_left']}日】"
            
        # 課題ブロックを作成
        block = f"{color_emoji}[{item['sheet']}]\n📝 {item['title']}\n📅 ({item['due_date']})"
        formatted_lines.append(block)

    # ★ 課題と課題の間「だけ」に一本の仕切り線を挟むように調整
    # これでダブりません！
    divider = "━━━━━━━━━━━━━━━━"
    # 各課題ブロックを結合し、前後に仕切り線を挟む
    task_list_text = f"\n{divider}\n" + f"\n{divider}\n".join(formatted_lines) + f"\n{divider}"
    
    message_text = f"📚【課題締め切り通知】\n\n期限が近づいている課題があります！\n{task_list_text}\n早めに終わらせましょう！"

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message_text}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    send_line_message()
