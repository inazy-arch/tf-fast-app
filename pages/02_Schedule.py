import streamlit as st

st.set_page_config(page_title="スケジュール管理")

# --- Scheduleページ専用の認証 ---
if 'schedule_logged_in' not in st.session_state:
    st.session_state.schedule_logged_in = False

def check_schedule_login():
    user = st.session_state.sched_username
    passwd = st.session_state.sched_password
    
    if (user == st.secrets["schedule_auth"]["username"] and 
        passwd == st.secrets["schedule_auth"]["password"]):
        st.session_state.schedule_logged_in = True
    else:
        st.error("認証に失敗しました")

# --- 画面表示 ---
if not st.session_state.schedule_logged_in:
    st.title("📅 スケジュール管理")
    st.warning("関係者専用ページです。")
    st.text_input("ID", key="sched_username")
    st.text_input("Password", type="password", key="sched_password")
    st.button("ログイン", on_click=check_schedule_login)
else:
    # === 本物の中身 ===
    st.title("📅 今月のスケジュール")
    st.success("ログイン成功")
    
    # 仮のカレンダー機能（後でExcel連携などに改造可能）
    st.date_input("日付を選択してください")
    st.write("予定リスト：")
    st.checkbox("10:00 - ミーティング")
    st.checkbox("13:00 - 練習対応")