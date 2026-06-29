import os
from datetime import datetime
import requests
import json
import re

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # 1. Web公開HTMLから現在あるシート名をすべて自動取得
    html_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
    tasks = []
    
    try:
        html_res = requests.get(html_url)
        html_res.encoding = 'utf-8'
        sheet_names = re.findall(r'class="sheet-name">([^<]+)', html_res.text)

        if not sheet_names:
            sheet_names = ["シート1", "シート2", "シート3", "シート4", "シート5"]
            
        sheet_names = list(dict.fromkeys(sheet_names))

        # 2. 各シートのデータを、エラーが起きにくい形式で確実に取得
        for sheet_name in sheet_names:
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                continue
                
            lines = response.text.splitlines()
            if len(lines) <= 1:
                continue
                
            for line in lines[1:]:
                # カンマやクォーテーションを綺麗に掃除して分割
                row = [val.strip('"').strip() for val in line.split(',')]
                if len(row) >= 2 and row[0] and row[1]:
                    # 文字列の中に余計なカンマがあっても日付を壊さないように保護
                    title = row[0]
                    due_text = row[-1] # 一番最後の要素を日付として取得
                    tasks.append({"title": title, "due_date": due_text, "sheet": sheet_name})
                    
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
            clean_date = re.sub(r'[^0-9/]', '', task["due_date"])
            due_date = datetime.strptime(clean_date, "%Y/%m/%d")
            days_left = (due_date - today).days + 1
            
            # 今日から5日後までの課題をすべて拾う
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

    # 期限が近い順に並び替え
    reminders.sort(key=lambda x: x["days_left"])

    # メッセージの組み立て（仕切り線が絶対に2行にならない設定）
    formatted_lines = []
    for item in reminders:
        if item["days_left"] <= 1:
            color_emoji = f"🔴【あと{item['days_left']}日】"
        elif item["days_left"] <= 3:
            color_emoji = f"🟡【あと{item['days_left']}日】"
        else:
            color_emoji = f"🟢【あと{item['days_left']}日】"
            
        block = f"{color_emoji}[{item['sheet']}]\n📝 {item['title']}\n📅 ({item['due_date']})"
        formatted_lines.append(block)

    divider = "━━━━━━━━━━━━━━━━"
    # 最初と最後、そして課題の間にだけきれいに1本ずつ敷く
    task_list_text = f"\n{divider}\n" + f"\n{divider}\n".join(formatted_lines) + f"\n{divider}"
    
    message_text = f"📚【課題締め切り通知】\n\n期限が近づいている課題があります！{task_list_text}\n\n早めに終わらせましょう！"

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message_text}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    send_line_message()
