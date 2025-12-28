import json

file_path = "/Users/hayato/Downloads/claude_chat_data/conversations.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# スキップされた会話を調査（インデックス1, 2, 3, 4, 5, 6, 11, 28）
skip_indices = [1, 2, 3, 4, 5, 6, 11, 28]

for idx in skip_indices:
    if idx < len(data):
        conv = data[idx]
        title = conv.get('name', '(無題)')
        messages = conv.get('chat_messages', [])
        
        print(f"\n=== 会話{idx}: {title} ===")
        print(f"メッセージ数: {len(messages)}")
        
        if messages:
            first_msg = messages[0]
            content = first_msg.get('content', [])
            print(f"最初のメッセージのcontent配列: {len(content)}個")
            
            for i, item in enumerate(content[:3]):
                print(f"  content[{i}]: type={item.get('type')}, text={item.get('text', '')[:50]}")