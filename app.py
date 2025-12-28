import streamlit as st
import chromadb
from openai import OpenAI
import json

# OpenAI初期化
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ChromaDB初期化（embedding_function明示的にNone）
@st.cache_resource
def init_chromadb():
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    # 既存のコレクションを削除（デバッグ用）
    try:
        chroma_client.delete_collection("conversations")
    except:
        pass
    
    # 新しいコレクション作成（embedding_function=None）
    collection = chroma_client.create_collection(
        name="conversations",
        metadata={"hnsw:space": "cosine"}
    )
    return collection

collection = init_chromadb()

# タイトル
st.title("🔍 会話履歴検索ツール - Memory Layer MVP")

# サイドバー - データ管理
st.sidebar.header("📁 データ管理")

# データベース統計
try:
    total_docs = collection.count()
    st.sidebar.metric("保存済み会話数", total_docs)
except:
    st.sidebar.metric("保存済み会話数", 0)

# JSONファイルアップロード
st.sidebar.subheader("📤 会話履歴インポート")
uploaded_file = st.sidebar.file_uploader("conversations.json", type=['json'])

if uploaded_file:
    try:
        # JSONを読み込み
        conversations = json.load(uploaded_file)
        
        st.sidebar.success(f"✅ {len(conversations)} 件の会話を検出")
        
        # 統計情報
        total_messages = sum(len(conv.get('chat_messages', [])) for conv in conversations)
        st.sidebar.info(f"📊 総メッセージ数: {total_messages} 件")
        
        # インポートボタン
        if st.sidebar.button("🚀 データベースにインポート", type="primary"):
            
            progress_bar = st.sidebar.progress(0)
            status_text = st.sidebar.empty()
            
            success_count = 0
            error_count = 0
            skipped_count = 0
            error_logs = []
            
            for idx, conv in enumerate(conversations):
                try:
                    # 基本情報
                    chat_id = conv.get('uuid', f"unknown_{idx}")
                    title = conv.get('name', '(無題)')
                    created_at = conv.get('created_at', '')
                    chat_messages = conv.get('chat_messages', [])
                    
                    # メッセージがない会話はスキップ
                    if not chat_messages:
                        skipped_count += 1
                        error_logs.append(f"スキップ{idx}: タイトル='{title}', ID={chat_id[:20]} - メッセージ0件")
                        continue
                    
                    # メッセージからテキストを抽出
                    full_text_parts = []
                    
                    for msg in chat_messages:
                        sender = msg.get('sender', 'unknown')
                        
                        # content配列からtype="text"のみを抽出
                        content_array = msg.get('content', [])
                        text_parts = []
                        
                        for content_item in content_array:
                            if content_item.get('type') == 'text':
                                text = content_item.get('text', '').strip()
                                if text:
                                    text_parts.append(text)
                        
                        # contentから抽出したテキストを結合
                        if text_parts:
                            combined_text = ' '.join(text_parts)
                            full_text_parts.append(f"[{sender}]: {combined_text}")
                    
                    full_text = '\n'.join(full_text_parts)
                    
                    # テキストを切り詰める（OpenAI Embeddingsの制限対策）
                    MAX_CHARS = 5000
                    if len(full_text) > MAX_CHARS:
                        full_text = full_text[:MAX_CHARS] + "\n...(以下省略)"

                    # 空のテキストの場合はスキップ
                    if not full_text.strip():
                        skipped_count += 1
                        msg_count = len(chat_messages)

                        #デバッグ：最初のメッセージのcontent構造を確認
                        debug_info = ""
                        if chat_messages and len(chat_messages) > 0:
                            first_msg = chat_messages[0]
                            content = first_msg.get('content',[])
                            debug_info = f", content配列長={len(content)}"
                            if content:
                                types = [c.get('type') for c in content]
                                debug_info += f", type={type}"
                        error_logs.append(f"スキップ{idx}: タイトル='{title}', {msg_count}msg, ID={chat_id[:20]}... - テキスト抽出0文字(contentが空?)")
                        continue
                    
                    # OpenAIでEmbedding作成
                    response = client.embeddings.create(
                        model="text-embedding-3-small",
                        input=full_text
                    )
                    embedding = response.data[0].embedding
                    
                    # ChromaDBに追加（embeddingを明示的に渡す）
                    collection.add(
                        documents=[full_text],
                        embeddings=[embedding],
                        ids=[chat_id],
                        metadatas=[{
                            'chat_id': chat_id,
                            'title': title,
                            'created_at': created_at,
                            'message_count': len(chat_messages)
                        }]
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    title_preview = conv.get('name', '(無題)')[:30]
                    messages = conv.get('chat_messages', [])
                    error_msg = f"会話{idx}: {title_preview} ({len(messages)}msg) - {str(e)[:150]}"
                    error_logs.append(error_msg)  # ← ログを保存
                
                # プログレスバー更新
                progress_bar.progress((idx + 1) / len(conversations))
                status_text.text(f"処理中: {idx + 1}/{len(conversations)}")
            
            progress_bar.empty()
            status_text.empty()
            
            # 結果表示
            st.sidebar.success(f"✅ インポート完了: {success_count} 件")
            if skipped_count > 0:
                st.sidebar.info(f"ℹ️ スキップ: {skipped_count} 件（空の会話）")
            if error_count > 0:
                st.sidebar.warning(f"⚠️ エラー: {error_count} 件")
            
            # エラーログとスキップログを表示
            if len(error_logs) > 0:
                with st.sidebar.expander("🔍 エラー詳細を表示"):
                    for log in error_logs:
                        st.text(log)
            
            #st.rerun()
            
    except Exception as e:
        st.sidebar.error(f"ファイル読み込みエラー: {str(e)}")

# データベースリセット
if st.sidebar.button("🗑️ データベースリセット"):
    try:
        collection.delete(where={})
        st.sidebar.success("✅ データベースをリセットしました")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"エラー: {str(e)}")

# メイン画面 - 検索
st.header("🔍 検索")

query = st.text_input("検索キーワードを入力", placeholder="例: マイクロ波、実験、Python")

if query:
    try:
        # OpenAI Embeddingsでクエリをベクトル化
        response = client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding
        
        # ChromaDBで検索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5
        )
        
        st.subheader(f"検索結果: {len(results['documents'][0])} 件")
        
        # 結果がない場合
        if len(results['documents'][0]) == 0:
            st.info("🔍 検索結果が見つかりませんでした")
        else:
            # 結果表示
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                # タイトルと日付
                title = metadata.get('title', '(無題)')
                created_at = metadata.get('created_at', 'N/A')
                if created_at != 'N/A' and len(created_at) >= 10:
                    date_str = created_at[:10]
                else:
                    date_str = 'N/A'
                
                # 類似度スコア
                similarity = 1 - distance
                
                with st.expander(f"📄 {i+1}. {title} - {date_str} (類似度: {similarity:.3f})", expanded=(i==0)):
                    st.markdown(f"**メッセージ数:** {metadata.get('message_count', 'N/A')} 件")
                    st.markdown(f"**チャットID:** `{metadata.get('chat_id', 'N/A')}`")
                    st.divider()
                    
                    # 内容プレビュー
                    st.markdown("**内容プレビュー:**")
                    if len(doc) > 500:
                        st.text(doc[:500] + "...")
                        # 全文表示ボタン
                        if st.button(f"全文を表示", key=f"show_full_{i}"):
                            st.text(doc)
                    else:
                        st.text(doc)
        
        # デバッグ情報
        with st.expander("🔍 デバッグ情報（開発用）"):
            st.write("results の構造:")
            st.json(results)
            st.write(f"documents の長さ: `{len(results['documents'][0])}`")
            st.write(f"metadatas の長さ: `{len(results['metadatas'][0])}`")
            
    except Exception as e:
        st.error(f"検索エラー: {str(e)}")