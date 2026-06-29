import os
from datetime import datetime
import requests
import json
import re

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # スプレッドシートの全体情報をJSON形式で取得
    url_meta = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json"
    tasks = []
    
    try:
        res = requests.get(url_meta)
        res.encoding = 'utf-8'
        
        match = re.search(r'google\.visualization\.Query\.setResponse\((.*)\);', res.text)
        if not match:
            return tasks
            
        raw_data = json.loads(match.group(1))
        
        # 公開HTMLページから、現在有効なすべてのシート名（タブ名）を全自動で引っこ抜く
        html_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
        html_res = requests.get(html_url)
        html_res.encoding = 'utf-8'
        sheet_names = re.findall(r'class="sheet-name">([^<]+)', html_res.text)

        # 自動取得が空振りした場合の最終セーフティ
        if not sheet_names:
            sheet_names = ["シート1", "シート2", "シート3", "シート4", "シート5"]
            
        sheet_names = list(dict.fromkeys(sheet_names))

        # 見つかったすべてのシートを1つずつ読み込む
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
            # 前回のバグ（resub）を修正
            clean_date = re.sub(r'[^0-9/]', '', task["due_date"])
            due_date = datetime.strptime(clean_date, "%Y/%m/%d")
            days_left = (due_date - today).days + 1
            
            # 今日から3日以内のものだけを通知対象にする
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

    # 1. 期限が近い順（残り日数が少ない順）に並び替える
    reminders.sort(key=lambda x: x["days_left"])

    # 2. LINE送信用にテキストを整形する
    formatted_lines = []
    for item in reminders:
        # 残り日数に応じて「焦る色」を自動で割り振り
        if item["days_left"] <= 1:
            color_emoji = f"🔴あと{item['days_left']}日"
        else:
            color_emoji = f"🟡あと{item['days_left']}日"
            
        formatted_lines.append(f"・【{color_emoji}】[{item['sheet']}] {item['title']} ({item['due_date']})")

    # ★【新機能】1行ずつ空けて見やすくするために、改行2つ（\n\n）で繋ぐ
    task_list = "\n\n".join(formatted_lines)
    message_text = f"📚【課題締め切り通知】\n\n期限が近づいている課題があります！\n\n{task_list}\n\n早めに終わらせましょう！"

    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message_text}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    send_line_message()
