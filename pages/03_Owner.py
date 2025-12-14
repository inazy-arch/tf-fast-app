import streamlit as st

st.set_page_config(page_title="管理者設定")

# --- Ownerページ専用の認証 ---
if 'owner_logged_in' not in st.session_state:
    st.session_state.owner_logged_in = False

def check_owner_login():
    user = st.session_state.owner_username
    passwd = st.session_state.owner_password
    
    if (user == st.secrets["owner_auth"]["username"] and 
        passwd == st.secrets["owner_auth"]["password"]):
        st.session_state.owner_logged_in = True
    else:
        st.error("管理者権限がありません")

# --- 画面表示 ---
if not st.session_state.owner_logged_in:
    st.title("👑 管理者 (Owner) ページ")
    st.error("ここは管理者専用です。")
    st.text_input("Owner ID", key="owner_username")
    st.text_input("Owner Password", type="password", key="owner_password")
    st.button("管理者ログイン", on_click=check_owner_login)
else:
    # === 本物の中身 ===
    st.title("👑 システム管理画面")
    st.info("ようこそ、管理者様")
    
    st.write("### 設定メニュー")
    st.button("ユーザーの追加・削除")
    st.button("全データのバックアップ")
    st.button("システムログの確認")