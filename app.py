import streamlit as st

st.set_page_config(page_title="ポータルサイト", layout="wide")

# --- 認証ロジック ---
# セッション状態（ログインしているかどうか）の初期化
if 'home_logged_in' not in st.session_state:
    st.session_state.home_logged_in = False

def check_login():
    # secrets.tomlに入力された情報と一致するか確認
    user = st.session_state.username_input
    passwd = st.session_state.password_input
    
    if (user == st.secrets["home_auth"]["username"] and 
        passwd == st.secrets["home_auth"]["password"]):
        st.session_state.home_logged_in = True
    else:
        st.error("ユーザー名またはパスワードが間違っています")

# --- 画面表示 ---
if not st.session_state.home_logged_in:
    # ログインしていない時の画面
    st.title("🔒 ログイン")
    st.text_input("ユーザー名", key="username_input")
    st.text_input("パスワード", type="password", key="password_input")
    st.button("ログイン", on_click=check_login)

else:
    # ログイン成功後の画面（ホームページの中身）
    st.title("🏠 メインポータル")
    st.success("ログインしました")
    
    st.write("各機能へ移動してください（現在は準備中）：")
    
    # 3つの機能への案内（今はただのテキストです）
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("TF")
        st.write("陸上競技部関連")
    with col2:
        st.subheader("Schedule")
        st.write("スケジュール管理")
    with col3:
        st.subheader("Owner")
        st.write("管理者専用")