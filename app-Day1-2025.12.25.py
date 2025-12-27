import streamlit as st
import chromadb
from openai import OpenAI

st.title("🔍会話履歴検索 MVP")

_ = '''
#APIキーのサイドバー入力
with st.sidebar:
    api_key = st.text_input("OpenAI Key", type ="password")
    if not api_key:
        st.warning("⚠️APIキーを入力してください")
        st.stop()
'''

#APIキーのsecrets.tomlからの読み込み
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


#テスト用のデータ
test_conversations = [
    "今日はPythonでベクトル検索を学んでいます",
    "CHromaDBは簡単に使えるベクトルデータベースです",
    "Streamlitで素早くUIを作れます",
]

#ChromaDBの初期化
@st.cache_resource
def init_chromadb():
    client = chromadb.PersistentClient(path = "./chroma_db")
    collection = client.get_or_create_collection("test_chats")
    return collection

collection = init_chromadb()

_ = '''
#OpenAI初期化
client = OpenAI(api_key=api_key)
'''


#データを追加
if st.button("テストデータを追加"):
    for i, text in enumerate(test_conversations):
        response = client.embeddings.create(
            model = "text-embedding-3-small",
            input = text
        )
        embedding = response.data[0].embedding

        #ChromaDBに保存
        collection.add(
            embeddings = [embedding],
            documents = [text],
            ids = [f"conv_{i}"]
        )
    st.success("✅データを追加しました!")

query = st.text_input("検索キーワードを入力:","Python")

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
        n_results = 3
    )


    #結果表示
    st.subheader("検索結果:")
    for i, doc in enumerate(results['documents'][0]):
        st.write(f"{i+1}. {doc}")
    