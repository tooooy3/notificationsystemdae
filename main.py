import os
import requests

def send_line_message():
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    LINE_USER_ID = os.getenv("LINE_USER_ID")

    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("エラー: 環境変数が設定されていません。")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    
    reminders = [
        "・【○月○日締切】Web開発課題レポート",
        "・【○月○日締切】システム設計書提出"
    ]
    
    task_list = "\n".join(reminders)
    message_text = f"📚【課題締め切り通知】\n\n期限が近づいている課題があります！\n\n{task_list}\n\n早めに終わらせましょう！"

    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("LINE通知の送信に成功しました！")
    else:
        print(f"エラーが発生しました: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    send_line_message()