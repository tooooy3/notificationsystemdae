import os
from datetime import datetime
import requests
import json
import re

def get_tasks_from_sheets():
    SPREADSHEET_ID = "1KBCOdxYN1reu_2-MrkRkHgVI5lERqTgh2nHTtnH2vjs"
    
    # スプレッドシートの構成情報を取得するためのURL（最初のシートから、全シートの情報をあぶり出します）
    init_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json"
    
    tasks = []
    try:
        res = requests.get(init_url)
        # Google APIが返す不要なプレフィックス「/*O_o*/\ngoogle.visualization.Query.setResponse(...);」を削ってピュアなJSONにする
        json_text = re.sub(r'^.*setResponse\(', '', res.text)
        json_text = re.sub(r'\);?\s*$', '', json_text)
        data = json.loads(json_text)
        
        # スプレッドシートに含まれるすべてのシート名（タブ名）を自動で抽出！
        # Google側のデータ構造からシート名リストを取得します
        sheet_names = []
        if "table" in data and "parsedNumHeaders" in data:
            # 一般的なエクスポート用リンクからすべてのシート名を取得するための裏ワザとして、
            # 別形式の特殊なエンドポイントからシート一覧を取得します
            meta_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/htmlview"
            meta_res = requests.get(meta_url)
            # HTML内からシートのタイトルを探し出す
            sheet_names = re.findall(r'class="sheet-name">([^<]+)', meta_res.text)
        
        # もしHTMLからうまく取れなかった場合のセーフティ（最低限「シート1」は見る）
        if not sheet_names:
            sheet_names = ["シート1","シート2","シート3","シート4","シート5"]
            
        # 重複を除去して綺麗にする
        sheet_names = list(dict.fromkeys(sheet_names))
        print(f"自動検出されたシート: {sheet_names}")
        
        # 見つかったすべてのシートをループで読み込む
        for sheet_name in sheet_names:
            url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            lines = response.text.splitlines()
            
            if not lines:
                continue
                
            # 1行目は見出し（課題名, 締切日）なので飛ばす
            for line in lines[1:]:
                row = [val.strip('"') for val in line.split(',')]
                if len(row) >= 2 and row[0] and row[1]:
                    tasks.append({"title": row[0], "due_date": row[1], "sheet": sheet_name})
                    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
            
    return tasks

def send_line_message():
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    LINE_USER_ID = os.getenv("LINE_USER_ID")

    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("エラー: 環境変数が設定されていません。")
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