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

def run_scraper():
    # --- Seleniumの設定 (ここが重要！) ---
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # サーバー上では画面を出せないので必須
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    job_data = []
    
    try:
        url = "https://next.rikunabi.com/job_search/area-tokyo/oc-engineering/"
        driver.get(url)

        # 読み込み待機
        wait = WebDriverWait(driver, 20) 
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h3")))

        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(2)

        elements = driver.find_elements(By.CSS_SELECTOR, "span[class*='employerNameBase']")

        for el in elements:
            name = el.text.strip()
            if name:
                job_data.append({"企業名": name})
        
        return job_data

    finally:
        driver.quit()

# --- Streamlitの画面構成 ---
st.title("求人リスト取得アプリ")
st.write("リクナビNEXTから東京のエンジニア求人企業名を取得します。")

if st.button("スクレイピング開始"):
    with st.spinner("データを取得中..."):
        data = run_scraper()
        
        if data:
            df = pd.DataFrame(data)
            st.success(f"{len(df)}件のデータを取得しました！")
            st.dataframe(df) # 画面に表を表示
            
            # CSVダウンロードボタン
            csv = df.to_csv(index=False, encoding="utf-8-sig").encode('utf-8-sig')
            st.download_button(
                label="CSVをダウンロード",
                data=csv,
                file_name="job_list.csv",
                mime="text/csv",
            )
        else:
            st.error("データが取得できませんでした。")