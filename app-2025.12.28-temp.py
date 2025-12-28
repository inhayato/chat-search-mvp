import streamlit as st
import chromadb
from openai import OpenAI
import json
from datetime import datetime

st.title("🔍会話履歴検索 MVP")

#OpenAI初期化
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

#ChromaDB初期化
@st.cache_resource
def init_chromadb():
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection("conversations")
    return collection

collection = init_chromadb()

#サイドバーでデータ管理
with st.sidebar:
    st.header("📁データ管理")

    #JSONファイルアップロード
    uploaded_file = st.file_uploader("会話履歴JSONファイル",type=['json'])

    if uploaded_file:
        try:
            conversations = json.load(uploaded_file)

            st.success(f"✅ {len(conversations)} 件の会話を検出")

            #統計情報
            total_messages = sum(len(conv.get('chat_messages', [])) for conv in conversations)
            st.info(f"📊総メッセージ数： {total_messages} 件")

            if st.button("データベースにインポート"):
                progress_bar = st.progress(0)
                status_text = st.empty()

                success_count = 0
                error_count = 0

                for idx, conv in enumerate(conversations):
                    try:
                        #基本情報
                        chat_id = conv.get('uuid',f"unknown_{idx}")
                        title = conv.get('name','(無題)')
                        created_at = conv.get('created_at','')
                        chat_messages = conv.get('chat_messages',[])

                        #メッセージがない会話はスキップ
                        if not chat_messages:
                            continue

                        #メッセージからテキストを抽出
                        full_text_parts = []

                        for msg in chat_messages:
                            sender = msg.get('sender','unknown')

                            #content配列からtype="text"のみを抽出
                            content_array = mes.get('content',[])
                            text_parts = []

                            for content_item in content_array:
                                if content_item.get('type') == 'text':
                                    text = content_item.get('text','').strip()
                                    if text:
                                        text_parts.append(text)

                            #contentから抽出したテキストを結合
                            if text_parts:
                                combined_text = ' '.join(text_parts)
                                full_text_parts.append(f"[{sender}]: {combined_text}")
                        
                        full_text = '\n'.join(full_text_parts)

                        #空のテキストの場合はスキップ
                        if not full_text.strip():
                            continue

                        #ChromaDBに追加
                        collection.add(
                            documents = [full_text],
                            ids = [chat_id],
                            metadatas = [{
                                'chat_id':chat_id,
                                'title':title,
                                'created_at':created_at,
                                'message_count':len(chat_messages)
                            }]
                        )

                        success_count += 1

                    except Exception as e:
                        error_count += 1
                        st.error(f"エラー (会話 {idx}): {str(e)}")

                    #プログレスバー更新
                    progress_bar.progress((idx + 1) / len(conversations))
                    status_text.text(f"処理中： {idx + 1}/{len(conversations)}")

                progress_bar.empty()
                status_text.empty()

                st.success(f"✅インポート完了: {success_count} 件")
                if error_count > 0:
                    st.warning(f"⚠️エラー: {error_count} 件")

                st.rerun()
        
        except Exception as e:
            st.error(f"ファイル読み込みエラー: {str(e)}")

#メイン画面：検索
st.header("🔍検索")

query = st.text_input("検索キーワードを入力:",placeholder="例: Pythonのベクトル検索")

if query:
    #クエリをベクトル化
    response = client.embeddings.create(
        model = "text-embedding-3-small",
        input = query
    )
    query_embedding = response.data[0].embedding

    #検索
    results = collection.query(
        query_embeddings = [query_embedding],
        n_results = 5
    )

    #デバック表示
    with st.expander("🔍デバック情報(開発用)"):
        st.write("**results の構造:**")
        st.json(results)
        st.write("**documents の長さ:**",len(results.get('documents',[[]])[0]))
        st.write("**metadatas の長さ:**",len(results.get('metadatas',[[]])[0]))
    
    #結果表示
    documents = results.get('documents',[[]])[0]
    metadatas = results.get('metadatas',[[]])[0]

    st.subheader(f"検索結果:{len(results['documents'][0])}件")

    if len(documents) == 0:
        st.info("検索結果が見つかりませんでした")
    else:
        for i, (doc, metadata)in enumerate(zip(documents,metadatas)):
            #タイトルと日付
            title = metadata.get('title','Untitled')
            created_at = metadata.get('created_at','N/A')
            if created_at != 'N/A' and len(created_at) >= 10:
                date_str = created_at[:10]
            else:
                date_str = 'N/A'
            
            with st.expander(f"🔹{title} - {date_str}",expanded=(i==0)):
                st.write(f"**メッセージ数:** {metadata.get('message_count', 'N/A')}")
                st.write(f"**Chat ID:** {metadata.get('chat_id', 'N/A')}")
                st.divider()

                #本文表示
                if len(doc) > 500:
                    st.text(doc[:500] + "...")
                else:
                    st.text(doc)
                
                #全文表示オプション
                if len(doc) > 500:
                    if st.button(f"全文を表示",key=f"show_full_{i}"):
                        st.text(doc)
