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
    # ユーザーエージェントを設定（dodaなどのサイトではbot検知を避けるために重要）
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    import os
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    # dodaの東京・エンジニア職種のベースURL（検索条件により適宜変更してください）
    base_url = "https://doda.jp/DodaFront/View/JobSearchList.action?ss=1&pic=1&ds=0&oc=0112M%2C0113M%2C0104M&pre=13"
    
    try:
        for page in range(1, max_pages + 1):
            # dodaのページ指定は通常 &page=n
            url = f"{base_url}&page={page}"
            
            if status_text:
                status_text.text(f"doda ページ {page}/{max_pages} を取得中...")
            if progress_bar:
                progress_bar.progress(page / max_pages)
            
            driver.get(url)
            
            try:
                # dodaの求人カードが読み込まれるのを待機
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "comapny_name"))) # 企業名が含まれる一般的なクラス名
            except Exception:
                # ページによってはクラス名が異なる場合があるため、h3などで代用
                try:
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h3")))
                except:
                    status_text.text(f"ページ {page} の読み込みに失敗。終了します。")
                    break
            
            # 少しスクロールして動的コンテンツを読み込む
            driver.execute_script("window.scrollTo(0, 1500);")
            time.sleep(2)
            
            # dodaの企業名を取得（.company_name または span[class*='company']）
            # セレクターはサイト更新により変わる可能性があるため、複数を考慮
            elements = driver.find_elements(By.CSS_SELECTOR, "span.company_name, h3.entry_title, a.company_name")
            
            page_count = 0
            for el in elements:
                name = el.text.replace("株式会社", "").replace("有限会社", "").strip()
                # 余計な「新着」などのテキストを除去
                name = name.split("\n")[0]
                
                if name and len(name) > 1:
                    job_data.append({
                        "ページ番号": page,
                        "企業名": name
                    })
                    page_count += 1
            
            if page_count == 0:
                if status_text:
                    status_text.text(f"ページ {page} でデータが見つかりませんでした。")
                break
            
            # サーバー負荷軽減のための待機
            time.sleep(1.5)
        
        return job_data
    
    finally:
        driver.quit()

# --- Streamlitの画面構成 ---
st.title("doda 求人リスト取得アプリ")
st.write("dodaから東京のエンジニア求人企業名を取得します。")

max_pages = st.slider("取得するページ数", min_value=1, max_value=50, value=5)

if st.button("スクレイピング開始"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner("dodaのデータを解析中..."):
        data = run_scraper(
            max_pages=max_pages,
            progress_bar=progress_bar,
            status_text=status_text
        )
    
    if data:
        df = pd.DataFrame(data)
        status_text.text("完了！")
        st.success(f"{len(df)}件のデータを取得しました！")

        tab_all, tab_unique = st.tabs(["📋 全件一覧", "🏢 企業名（重複除去）"])

        with tab_all:
            st.dataframe(df, use_container_width=True)

        with tab_unique:
            df_unique = df.drop_duplicates(subset="企業名", keep="first").reset_index(drop=True)
            st.write(f"**{len(df_unique)} 社**")
            st.dataframe(df_unique, use_container_width=True)

        st.divider()
        st.download_button(
            label="📥 企業リスト(CSV)をダウンロード",
            data=df_unique.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
            file_name="doda_job_list.csv",
            mime="text/csv",
        )
    else:
        st.error("データが取得できませんでした。検索条件のURLや要素名を確認してください。")
