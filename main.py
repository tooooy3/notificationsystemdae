import os
from datetime import datetime
import requests
import json
import re

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # 【最重要】HTMLを使わず、スプレッドシートのメタデータから全自動でシート名を引っこ抜くAPI
    url_meta = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json"
    tasks = []
    
    try:
        res = requests.get(url_meta)
        res.encoding = 'utf-8'
        # Google特有のゴミ文字を削って純粋なJSONデータにする
        match = re.search(r'google\.visualization\.Query\.setResponse\((.*)\);', res.text)
        if not match:
            # 万が一のセーフティ：固定名で読み込む
            sheet_names = ["シート1", "シート2", "シート3", "シート4", "シート5"]
        else:
            data = json.loads(match.group(1))
            
            # JSONデータの中から、いま存在するすべてのシート名を全自動で抽出
            # これであなたがタブをどんな名前にしても、いくつ増やしても自動検知します！
            sheet_names = []
            if 'table' in data and 'cols' in data['table']:
                #colsの中にあるid属性がシート名になっている仕組みを利用
                raw_ids = [col['id'] for col in data['table']['cols'] if 'id' in col]
                for rid in raw_ids:
                    # idが'A'や'B'のものはダミーなので除外
                    if len(rid) > 1: 
                        sheet_names.append(rid)

            # セーフティ：もし全自動取得が空振りしたら、固定名に戻す
            if not sheet_names:
                sheet_names = ["シート1", "シート2", "シート3", "シート4", "シート5"]
        
        # 重複を消して整理
        sheet_names = list(dict.fromkeys(sheet_names))
        print(f"検知されたシート一覧: {sheet_names}")

        # 自動で見つけたすべてのシートを1つずつ読み込む
        for sheet_name in sheet_names:
            # キャッシュを無視して最新のCSVを強制ダウンロードする確実なURL
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&sheet={sheet_name}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            # シートが存在しない、またはエラーの場合は飛ばす
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
        print(f"読み込みスキップエラー: {e}")
            
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

    # ★【新機能】期限が近い順（残り日数が少ない順）に並び替える
    reminders.sort(key=lambda x: x["days_left"])

    # LINE用のテキストを作成
    formatted_lines = []
    for item in reminders:
        # ★【新機能】残り日数に応じて「焦る色」の絵文字に変える
        # 0日〜1日：🔴（大至急！）
        if item["days_left"] <= 1:
            color_emoji = f"🔴あと{item['days_left']}日"
        # 2日〜3日：🟡（そろそろ！）
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
