import streamlit as st

st.set_page_config(page_title="TFページ")

# --- TFページ専用の認証ロジック ---
if 'tf_logged_in' not in st.session_state:
    st.session_state.tf_logged_in = False

def check_tf_login():
    user = st.session_state.tf_username
    passwd = st.session_state.tf_password
    
    # secrets.toml の [tf_auth] を見に行きます
    if (user == st.secrets["tf_auth"]["username"] and 
        passwd == st.secrets["tf_auth"]["password"]):
        st.session_state.tf_logged_in = True
    else:
        st.error("TF認証に失敗しました")

# --- 画面表示 ---
if not st.session_state.tf_logged_in:
    st.title("🏃‍♂️ TF専用エリア")
    st.warning("ここから先は部員専用です。認証してください。")
    st.text_input("TFユーザー名", key="tf_username")
    st.text_input("TFパスワード", type="password", key="tf_password")
    st.button("入室する", on_click=check_tf_login)
else:
    # === ここにTFページの本当の中身を書きます ===
    st.title("🏃‍♂️ 陸上競技部 (TF) ダッシュボード")
    st.success("認証成功！")
    st.write("ここに部員へのお知らせや記録データを表示します。")