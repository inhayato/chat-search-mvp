import json

file_path = "/Users/hayato/Downloads/claude_chat_data/conversations.json"

print("読み込み中...")
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n=== 会話数: {len(data)} 件 ===\n")

# メッセージ数でソート
conversations_with_messages = [
    conv for conv in data 
    if conv.get('chat_messages') and len(conv['chat_messages']) > 0
]
conversations_with_messages.sort(key=lambda x: len(x['chat_messages']), reverse=True)

print(f"メッセージがある会話: {len(conversations_with_messages)} 件\n")

# 上位3件を表示
print("=== メッセージ数が多い会話 Top 3 ===")
for i, conv in enumerate(conversations_with_messages[:3]):
    print(f"\n{i+1}. タイトル: {conv.get('name', '(無題)')[:50]}")
    print(f"   メッセージ数: {len(conv['chat_messages'])} 件")
    print(f"   作成日: {conv.get('created_at')[:10]}")

# 一番長い会話の詳細
if conversations_with_messages:
    longest = conversations_with_messages[0]
    
    print(f"\n\n=== 一番長い会話の詳細 ===")
    print(f"タイトル: {longest.get('name', '(無題)')}")
    print(f"メッセージ数: {len(longest['chat_messages'])} 件\n")
    
    # 最初の3メッセージを見る
    for i, msg in enumerate(longest['chat_messages'][:3]):
        print(f"\n--- メッセージ {i+1} ---")
        print(f"送信者: {msg.get('sender')}")
        print(f"text フィールド: {msg.get('text', '')[:100]}")
        print(f"content 配列の長さ: {len(msg.get('content', []))}")
        
        # content配列の中身を見る
        for j, content_item in enumerate(msg.get('content', [])[:2]):
            print(f"  content[{j}] type: {content_item.get('type')}")
            if content_item.get('type') == 'text':
                print(f"  content[{j}] text: {content_item.get('text', '')[:200]}")