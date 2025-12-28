import streamlit as st
import chromadb
from chromadb.config import Settings
import openai
import json

#OpenAI API設定
openai.api_key = st.secrets["OPENAI_API_KEY"]

#ChromaDB初期化
@st.cache_resource  #Streamlitはボタンを押すたびにコードを再実行するが、重くなる。そこで、一度接続したら、その接続を使い回すと設定している。
def init_chromadb():
    client = chromadb.PersistentClient(path="./chroma_db")  #データをファイル'./chroma_db'として保存し、アプリを閉じてもデータが消えない。
    collection = client.get_or_create_collection(
        name = "conversations",
        embedding_function = None,
        metadata = {"hnsw:space":"cosine"}
    )
    return collection

collection = init_chromadb()

#タイトル
st.title("🔍会話履歴検索ツール - Memory Layer MVP")

# サイドバー - データ管理
st.sidebar.header("📁データ管理")

#データベース統計
try:
    total_docs = collection.count()
    st.sidebar.metric("保存済み会話数",total_docs)   #streamlitの指標を表示するコマンド
except:
    st.sidebar.metric("保存済み会話数",0)

#JSONファイルアップロード
st.sidebar.subheader("📤 会話履歴インポート")
uploaded_file = st.sidebar.file_uploader("conversations.json",type=['json'])    #conversations.jsonというラベルをつけた、.jsonのみを受け付けるファイルの受け皿

if uploaded_file:
    try:
        #JSONを読み込み
        conversations = json.load(uploaded_file)

        st.sidebar.success(f"✅ {len(conversations)} 件の会話を検出")

        #統計情報
        total_messages = sum(len(conv.get('chat_messages',[]))for conv in conversations)    #エラー防止のためデータがなければ空リストとして扱い、メッセージのリストを取り出す。len()でその会話に含まれるメッセージの数を数える。
        st.sidebar.info(f"📊 総メッセージ数: {total_messages} 件")

        #インポートボタン
        if st.sidebar.button("🚀 データベースにインポート",type="primary"):

            progress_bar = st.sidebar.progress(0)
            status_text = st.sidebar.empty()

            success_count = 0
            error_count = 0
            skipped_count = 0
            
            for idx, conv in enumerate(conversations):  #'enumerate'でリストの順番(idx)と中身(conv)を同時に取得する。
                try:
                    #基本情報
                    chat_id = conv.get('uuid',f"unknown_{idx}")
                    title = conv.get('name','(無題)')
                    created_at = conv.get('created-at','')
                    chat_messages = conv.get('chat_messages',[])

                    #メッセージがない会話はスキップ
                    if not chat_messages:
                        skipped_count += 1
                        continue

                    #メッセージからテキストを抽出
                    full_text_parts = []

                    for msg in chat_messages:
                        sender = msg.get('sender','unknown')

                        #content配列からtype="text"のみを抽出
                        content_array = msg.get('content',[])
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
                        skipped_count += 1
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
                    st.sidebar.error(f"エラー(会話 {idx}): {str(e)[:100]}")

                #プログレスバー更新
                progress_bar.progress((idx + 1)/len(conversations))
                status_text.text(f"処理中: {idx + 1}/{len(conversations)}")

            progress_bar.empty()
            status_text.empty()

            #結果表示
            st.sidebar.success(f"✅インポート完了: {success_count} 件")
            if skipped_count > 0:
                st.sidebar.info(f"ℹ️ スキップ: {skipped_count} 件（空の会話）")
            if error_count > 0:
                st.sidebar.warning(f"⚠️ エラー:{error_count} 件")

            st.rerun()
    except Exception as e:
        st.sidebar.error(f"ファイル読み込みエラー: {str(e)}")

#データベースリセット
if st.sidebar.button("🗑️データベースリセット"):
    try:
        collection.delete(where={})
        st.sidebar.success("✅データベースをリセットしました")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"エラー: {str(e)}")

#メイン画面 - 検索
st.header("🔍検索")

query = st.text_input("検索キーワードを入力",placeholder="例: マイクロ波、実験、Python")

if query:
    try:
        #OpenAI Embeddingでクエリをベクトル化
        response = openai.embeddings.create(
            input = query,
            model = "text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding

        #ChromaDBで検索
        results = collection.query(
            query_embeddings = [query_embedding],
            n_results = 5
        )

        st.subheader(f"検索結果: {len(results['documents'][0])} 件")

        #結果がない場合
        if len(results['documents'][0]) == 0:
            st.info("🔍検索結果が見つかりませんでした")
        else:
            #結果表示
            for i, (doc,metadata,distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0],
            )):
                #タイトルと日付
                title = metadata.get('title','(無題)')
                created_at = metadata.get('created_at','N/A')
                if created_at != 'N/A' and len(created_at) >= 10:
                    date_str = created_at[:10]
                else:
                    date_str = 'N/A'

                #類似度スコア
                similarity = 1 - distance

                with st.expander(f"📄 {i+1}. {title} - {date_str} (類似度: {similarity:.3f})",expanded=(i==0)):
                    st.markdown(f"**メッセージ数:** {metadata.get('message_count','N/A')}件")
                    st.markdown(f"**チャットID:** `{metadata.get('chat_id','N/A')}`")
                    st.divider()

                    #内容プレビュー
                    st.markdown("**内容プレビュー:**")
                    if len(doc) > 500:
                        st.text(doc[:500] + "...")
                        #全文表示ボタン
                        if st.button(f"全文を表示",key = f"show_full_{i}"):
                            st.text(doc)
                        else:
                            st.text(doc)
            #デバック情報
            with st.expander("🔍デバック情報(開発用)"):
                st.write("results の構造:")
                st.json(results)
                st.write(f"documents の長さ: `{len(results['documents'][0])}`")
                st.write(f"metadatas の長さ: `{len(results['metadata'][0])}`")
            
    except Exception as e:
        st.error(f"検索エラー: {str(e)}")

