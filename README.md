# Personal AI - Memory Layer MVP

## WHY

現在のAIは「チャットに閉じ込められている」  
記憶を持たず、パートナーではなくツールでしかない。

Personal AIは、デジタルパートナーとしての新しい関係性を創る。

## 現在の状態

**Week 1 (Day 1-3完了)**: 会話履歴検索ツール開発中

- Streamlit + ChromaDB + OpenAI Embeddings
- Claude.ai会話履歴43件をインポート
- ベクトル検索で過去の会話を発見

## 技術スタック

- Python 3.12.7
- Streamlit (UI)
- ChromaDB (ベクトルDB)
- OpenAI Embeddings (text-embedding-3-small)

## セットアップ
```bash
# 依存関係インストール
pip install -r requirements.txt --break-system-packages

# 環境変数設定（Streamlit secrets）
# .streamlit/secrets.toml に OPENAI_API_KEY を設定

# アプリ起動
streamlit run app.py
```

## ビジョン

### Phase 1: Memory Layer（今ここ）
ユーザーを理解する記憶システム

### Phase 2: Active Inference
文脈を理解し、能動的に推論する

### Phase 3: Personal AI
どこにでもいるデジタルパートナー

## 開発状況

- [x] 環境構築
- [x] データインポート機能
- [x] ベクトル検索機能
- [ ] UI改善（Week 1後半）
- [ ] 会話全文表示機能

## Build in Public

開発プロセスを全公開しています

## ライセンス

MIT License

---

**デジタルパートナーという新しい関係性を、一緒に創りませんか？**