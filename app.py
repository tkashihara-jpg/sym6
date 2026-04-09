import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run_scraper(max_pages=10, progress_bar=None, status_text=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,1024") # dodaはサイズが小さいと要素が隠れる場合があるため指定
    
    import os
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    # dodaのベースURL（ページ番号を除いたもの）
    base_url = "https://doda.jp/DodaFront/View/JobSearchList/j_pr__13/-oc__03L/-op__1/-preBtn__1/"
    
    try:
        for page in range(1, max_pages + 1):
            # dodaのページ送りはURLパラメータの最後に /?so=50&tp=1 などを付与（tpがページ数）
            url = f"{base_url}?so=50&tp={page}"
            
            if status_text:
                status_text.text(f"ページ {page}/{max_pages} を取得中... (URL: {url})")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            try:
                # dodaの求人カードが読み込まれるのを待機
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "project_title")))
            except Exception:
                # ページが見つからない、または最終ページを超えた場合
                if status_text:
                    status_text.text(f"ページ {page} の読み込みに失敗しました（終了の可能性があります）。")
                break
            
            # 少しスクロールして要素を読み込ませる
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(1)
            
            # dodaの企業名は class="company_name" 内にあることが多い
            # ※構成により複数のセレクタがあるため、より確実な「求人タイトルの親要素」付近から取得
            elements = driver.find_elements(By.CSS_SELECTOR, "span.company_name")
            
            page_count = 0
            for el in elements:
                name = el.text.replace("株式会社", " 株式会社").strip() # 見やすさのため整形
                name = name.split("\n")[0] # 余計なサブテキストが入るのを防ぐ
                if name:
                    job_data.append({
                        "ページ番号": page,
                        "企業名": name
                    })
                    page_count += 1
            
            if page_count == 0:
                break
            
            # サーバー負荷軽減
            time.sleep(5)
        
        return job_data
    
    finally:
        driver.quit()

# --- Streamlitの画面構成 ---
st.title("doda 求人リスト取得アプリ")
st.write("dodaから東京のエンジニア求人（IT/通信）企業名を取得します。")

max_pages = st.slider("取得するページ数", min_value=1, max_value=50, value=5)

if st.button("スクレイピング開始"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("dodaからデータを取得中..."):
        data = run_scraper(
            max_pages=max_pages,
            progress_bar=progress_bar,
            status_text=status_text
        )
    
    if data:
        status_text.text("完了！")
        df = pd.DataFrame(data)
        st.success(f"{len(df)}件のデータを取得しました！")

        tab_all, tab_unique = st.tabs(["📋 全件一覧", "🏢 企業名（重複除去）"])

        with tab_all:
            st.dataframe(df, use_container_width=True)

        with tab_unique:
            df_unique = (
                df.drop_duplicates(subset="企業名", keep="first")
                  .reset_index(drop=True)
            )
            st.write(f"**{len(df_unique)} 社**（重複除去後）")
            st.dataframe(df_unique, use_container_width=True)

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 全件CSVをダウンロード",
                data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="doda_list_all.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                label="📥 企業名（重複除去）CSVをダウンロード",
                data=df_unique.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="doda_list_unique.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        status_text.text("エラー")
        st.error("データが取得できませんでした。サイトの構造が変わったか、アクセスがブロックされた可能性があります。")
