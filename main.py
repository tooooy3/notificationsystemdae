import os
from datetime import datetime
import requests
import json
import re

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # Googleの公式APIから、スプレッドシート全体の情報をJSONで取得
    url_meta = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json"
    tasks = []
    
    try:
        res = requests.get(url_meta)
        res.encoding = 'utf-8'
        
        # Google特有の不要な文字列を削り、純粋なJSONにする
        match = re.search(r'google\.visualization\.Query\.setResponse\((.*)\);', res.text)
        if not match:
            return [{"title": "設定エラー", "due_date": "2026/01/01", "sheet": "システム"}]
            
        raw_data = json.loads(match.group(1))
        
        # 【超重要】JSONの「reqId」から、現在存在するすべての実際のシート名（タブ名）を全自動で引っこ抜く
        sheet_names = []
        if 'sig' in raw_data:
            # htmlviewのページから、現在有効な全シートのタブ名を正規表現で完全に抽出
            html_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
            html_res = requests.get(html_url)
            html_res.encoding = 'utf-8'
            sheet_names = re.findall(r'class="sheet-name">([^<]+)', html_res.text)

        # 万が一自動取得が完全にブロックされた場合の最終セーフティ
        if not sheet_names:
            sheet_names = ["シート1", "シート2", "シート3", "シート4", "シート5"]
            
        sheet_names = list(dict.fromkeys(sheet_names)) # 重複排除

        # 見つかったすべてのシート（タブ）を確実に切り替えてCSVで読み込む
        for sheet_name in sheet_names:
            # sheet=引数にシート名を入れることで、確実にタブを切り替えてデータを取得します
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
                    # 最初の列がタイトル、2列目が日付、どのシートから取ったかも保存
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
            # 日付フォーマット（YYYY/MM/DD）を解析
            due_date = datetime.strptime(task["due_date"].resub(r'[^0-9/]', ''), "%Y/%m/%d") if hasattr(task["due_date"], 'resub') else datetime.strptime(task["due_date"], "%Y/%m/%d")
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
            # 日付の形式が違う行などは自動でスキップ
            continue

    if not reminders:
        return

    # 1. 期限が近い順（残り日数が少ない順）に並び替える
    reminders.sort(key=lambda x: x["days_left"])

    # 2. LINE送信用にテキストを整形する
    formatted_lines = []
    for item in reminders:
        # 残り日数に応じて「焦る色」を自動で割り振り（0〜1日は🔴、2〜3日は🟡）
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
