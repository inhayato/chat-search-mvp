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
    uploaded_file = st.file_uploader("会話履歴JSONをアップロード",type=['json'])

    if uploaded_file and st.button("インポート開始"):
        #JSONを読み込み
        data = json.load(uploaded_file)

        progress_bar = st.progress(0)
        total_messages = 0

        #会話ごとに処理
        for idx, conv in enumerate(data.get('conversations',[])):
            chat_id = conv.get('id',f'chat_{idx}')
            chat_title = conv.get('title','Untitled')
            created_at = conv.get('created_at','')

            #メッセージを結合してインデックス化
            messages_text = []
            for msg in conv.get('messages',[]):
                role = msg.get('role','unknown')
                content = msg.get('content','')
                messages_text.append(f"{role}:{content}")

            full_text = "\n".join(messages_text)

            #ベクトル化
            response = client.embeddings.create(
                model = "text-embedding-3-small",
                input = full_text
            )
            embedding = response.data[0].embedding

            #ChromaDBに保存
            collection.add(
                embeddings = [embedding],
                documents = [full_text],
                metadatas = [{
                    'chat_id':chat_id,
                    'title':chat_title,
                    'created_at':created_at,
                    'message_count':len(conv.get('messages',[]))
                }],
                ids = [chat_id]
            )

            total_messages += len(conv.get('messages',[]))
            progress_bar.progress((idx + 1) / len(data.get('conversations',[])))
        st.success(f"✅{len(data.get('conversations',[]))}チャット、{total_messages}メッセージをインポートしました!")

    #統計情報
    st.divider()
    st.subheader("📊統計")
    try:
        count = collection.count()
        st.metric("保存済みチャット数",count)
    except:
        st.metric("保存済みチャット数",0)

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
    with st.expander("🔍デバッグ情報(開発用)"):
        st.write("**results の構造:**")
        st.json(results)
        st.write("**documents の長さ:**",len(results.get('documents', [[]])[0]))
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
        # for i, (doc, metadata) in enumerate(zip(results['documents'][0],results['metadatas'][0])):
        #     with st.expander(f"🔸{metadata.get('title','Untitled')} - {metadata.get('created_at','N/A')[:10]}"):
        #         st.write(f"**メッセージ数:**{metadata.get('message_count','N/A')}")
        #         st.write(f"**Chat ID:** {metadata.get('chat_id','N/A')}")
        #         st.divider()
        #         st.text(doc[:500] + "..." if len(doc) > 500 else doc)


