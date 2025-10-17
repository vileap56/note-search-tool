import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="note.com 記事検索ツール",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 note.com 記事検索ツール")
st.markdown("---")

# サイドバーで検索条件を設定
with st.sidebar:
    st.header("📋 検索条件")
    
    keyword = st.text_input("🔎 検索キーワード", value="", help="検索したいキーワードを入力")
    
    period_options = {
        "すべて": 0,
        "過去1日": 1,
        "過去2日": 2,
        "過去3日": 3,
        "過去1週間": 7,
        "過去2週間": 14,
        "過去1ヶ月": 30
    }
    period = st.selectbox("📅 期間", list(period_options.keys()), index=2)
    
    min_likes = st.number_input("❤️ 最低いいね数", min_value=0, max_value=10000, value=10, step=10)
    
    price_filter = st.selectbox("💰 記事タイプ", ["すべて", "無料のみ", "有料のみ"])
    
    max_results = st.number_input("📊 収集件数", min_value=1, max_value=1000, value=50, step=10)
    
    search_button = st.button("🚀 検索開始", type="primary", use_container_width=True)

def search_note_articles(keyword, min_likes, price_filter, max_results, days_back):
    """note.comの記事を検索"""
    all_articles = []
    start = 0
    size = 10
    base_url = "https://note.com/api/v3/searches"
    
    # 期間の計算
    if days_back > 0:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
    else:
        start_date = None
    
    # プログレスバーとステータス表示
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        while len(all_articles) < max_results:
            params = {
                'context': 'note',
                'q': keyword,
                'size': size,
                'start': start
            }
            
            if days_back > 0:
                params['sort'] = 'created_at'
            
            status_text.text(f"データ取得中... ({len(all_articles)}/{max_results}件)")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(base_url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                st.error(f"APIエラー: ステータスコード {response.status_code}")
                break
            
            data = response.json()
            
            # データ構造の確認
            contents = None
            if 'data' in data and 'notes' in data['data'] and isinstance(data['data']['notes'], dict):
                if 'contents' in data['data']['notes']:
                    contents = data['data']['notes']['contents']
            elif 'data' in data and 'contents' in data['data']:
                contents = data['data']['contents']
            elif 'data' in data and 'notes' in data['data'] and isinstance(data['data']['notes'], list):
                contents = data['data']['notes']
            elif 'contents' in data:
                contents = data['contents']
            elif 'notes' in data:
                contents = data['notes']
            
            if not contents or len(contents) == 0:
                break
            
            # 記事データを処理
            for item in contents:
                try:
                    # 公開日時の確認
                    if days_back > 0 and start_date:
                        publish_date_str = item.get('publish_at', item.get('created_at', item.get('publishedAt', '')))
                        
                        if publish_date_str:
                            try:
                                publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                                publish_date = publish_date.replace(tzinfo=None)
                                
                                if publish_date < start_date:
                                    continue
                            except:
                                pass
                    
                    # いいね数の取得
                    like_count = item.get('like_count', item.get('likeCount', item.get('likes', 0)))
                    
                    if like_count < min_likes:
                        continue
                    
                    # 価格の取得
                    price = item.get('price', item.get('selling_price', 0))
                    if price is None:
                        price = 0
                    is_paid = price > 0
                    
                    if price_filter == '無料のみ' and is_paid:
                        continue
                    elif price_filter == '有料のみ' and not is_paid:
                        continue
                    
                    # タイトルの取得
                    title = item.get('name', item.get('title', item.get('note_name', '(タイトルなし)')))
                    
                    # 公開日時の取得
                    publish_date_str = item.get('publish_at', item.get('created_at', item.get('publishedAt', '')))
                    if publish_date_str:
                        try:
                            publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                            publish_date_display = publish_date.strftime('%Y-%m-%d %H:%M')
                        except:
                            publish_date_display = '不明'
                    else:
                        publish_date_display = '不明'
                    
                    # URLの構築
                    user_urlname = ''
                    note_key = ''
                    
                    if 'user' in item and isinstance(item['user'], dict):
                        user_urlname = item['user'].get('urlname', item['user'].get('url_name', ''))
                    elif 'creator' in item and isinstance(item['creator'], dict):
                        user_urlname = item['creator'].get('urlname', item['creator'].get('url_name', ''))
                    
                    note_key = item.get('key', item.get('note_key', item.get('noteKey', '')))
                    
                    if user_urlname and note_key:
                        url = f"https://note.com/{user_urlname}/n/{note_key}"
                    else:
                        url = item.get('note_url', item.get('url', item.get('noteUrl', '不明')))
                    
                    # 記事情報を収集
                    article = {
                        'タイトル': title,
                        'いいね数': like_count,
                        '金額': '無料' if price == 0 else f'¥{price}',
                        '公開日時': publish_date_display,
                        'URL': url
                    }
                    
                    all_articles.append(article)
                    
                    # 進捗を更新
                    progress = min(len(all_articles) / max_results, 1.0)
                    progress_bar.progress(progress)
                    
                    if len(all_articles) >= max_results:
                        break
                
                except Exception as e:
                    continue
            
            start += size
            
            if len(contents) < size:
                break
            
            time.sleep(0.3)
        
        # いいね数で降順ソート
        all_articles.sort(key=lambda x: x['いいね数'], reverse=True)
        
        progress_bar.progress(1.0)
        status_text.text(f"✅ 検索完了! {len(all_articles)}件の記事を取得しました。")
        
        return all_articles
    
    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        return []

# メインエリア
if search_button:
    if not keyword:
        st.warning("⚠️ キーワードを入力してください。")
    else:
        with st.spinner('検索中...'):
            days_back = period_options[period]
            articles = search_note_articles(
                keyword, 
                min_likes, 
                price_filter, 
                max_results, 
                days_back
            )
            
            if articles:
                st.success(f"✅ {len(articles)}件の記事を取得しました！")
                
                # データフレームに変換
                df = pd.DataFrame(articles)
                
                # URLをクリック可能にする
                df['リンク'] = df['URL'].apply(lambda x: f'<a href="{x}" target="_blank">開く</a>' if x != '不明' else '不明')
                
                # 表示用のデータフレーム（URLなし）
                display_df = df[['タイトル', 'いいね数', '金額', '公開日時', 'リンク']]
                
                # テーブル表示
                st.markdown("### 📋 検索結果")
                st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                # CSVダウンロードボタン
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="💾 CSVでダウンロード",
                    data=csv,
                    file_name=f"note_search_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("条件に合う記事が見つかりませんでした。")
else:
    st.info("👈 左のサイドバーで条件を設定して、検索を開始してください。")
    
    # 使い方の説明
    with st.expander("📖 使い方"):
        st.markdown("""
        1. **検索キーワード**: 検索したい言葉を入力
        2. **期間**: 記事の公開期間を選択
        3. **最低いいね数**: この数以上のいいねがある記事のみ表示
        4. **記事タイプ**: 無料/有料/すべて から選択
        5. **収集件数**: 取得する記事の最大数
        6. **検索開始ボタン**をクリック
        7. 結果が表示されたら、CSVでダウンロード可能
        """)

# フッター
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit")