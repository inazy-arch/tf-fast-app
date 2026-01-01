import streamlit as st
import utils
# Viewsフォルダから各機能をインポート
from views import public, member, admin

# --- ⚙️ 設定 ---
st.set_page_config(page_title="UEC T&F Portal", layout="wide", page_icon="uec_tf_icon.jpg")
utils.apply_custom_css()  # デザイン適用
utils.apply_mobile_css()

# --- 🔐 セッション初期化 ---
if 'user_info' not in st.session_state: st.session_state.user_info = None

# --- 🎨 ヘッダー・フッター関数 ---
def show_header(user):
    """ 全ページ共通のヘッダー表示 """
    if user:
        # ログイン中
        st.caption(f"Login: {user['name']} ({user.get('role_title', '部員')})")
    else:
        # 未ログイン
        st.caption("Guest User")
    st.markdown("---")

def show_footer():
    """ 全ページ共通のフッター表示 """
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888; font-size: 0.8rem; margin-top: 20px;">
            &copy; 2025 UEC Track & Field Club Portal System
        </div>
        """,
        unsafe_allow_html=True
    )

# --- 🚀 メイン処理 ---
user = st.session_state.user_info

# 1. ヘッダー表示
show_header(user)

# 2. サイドバー & ページルーティング
if user is None:
    # === 未ログイン (一般公開) ===
    with st.sidebar:
        st.header("UEC T&F")
        menu = st.radio(
            "Menu", 
            ["Top", "Members", "Result", "Blog", "OBOG", "Link", "Login"], 
            key="public_menu_radio"
        )
    
    # ページ表示
    if menu == "Top": public.page_home()
    elif menu == "Members": public.page_members()
    elif menu == "Result": public.page_result()
    elif menu == "Blog": public.page_blog()
    elif menu == "OBOG": public.page_obog()
    elif menu == "Link": public.page_link()
    elif menu == "Login": public.page_login()

else:
    # === ログイン済み (部員・管理者) ===
    with st.sidebar:
        st.header(f"{user['name']}")
        role_title = user.get("role_title", "部員")
        st.caption(f"役職: {role_title}")
        
        # --- 権限設定 ---
        my_role = user.get("role_title", "")
        
        # 権限グループ定義
        ADMIN_ROLES = ["主将", "副主将", "競技会", "広報", "会計", "管理者", "主務"]
        COMP_ROLES = ["主将", "副主将", "競技会", "管理者"]
        PR_ROLES = ["主将", "副主将", "広報", "管理者"]
        ACC_ROLES = ["主将", "副主将", "会計", "管理者"]
        
        # メニュー構築
        menu_items = ["ダッシュボード", "アカウント情報", "エントリー募集一覧", "タイムテーブル", "ブログ投稿", "部費・集金"]
        
        # 権限がある場合のみメニューを追加
        if my_role in ADMIN_ROLES:
            menu_items.append("部員名簿(管理者)")
            menu_items.append("組レーン結果登録(管理者)")
            
        if my_role in COMP_ROLES:
            menu_items.append("エントリー管理(競技会)")
            menu_items.append("新規大会登録(競技会)")
            
        if my_role in PR_ROLES:
            menu_items.append("データ登録・インポート(広報)")
            
        if my_role in ACC_ROLES:
            menu_items.append("会計管理")

        # メニュー選択
        sel = st.radio("Menu", menu_items, label_visibility="collapsed", key="member_menu_radio")
        
        st.markdown("---")
        if st.button("Logout", key="logout_btn"):
            st.session_state.user_info = None
            st.rerun()

    # ページ表示の振り分け (日本語メニューに対応)
    if sel == "ダッシュボード": member.page_top()
    elif sel == "アカウント情報": member.page_account()
    elif sel == "エントリー募集一覧": member.page_entry_recruitment()
    elif sel == "タイムテーブル": member.page_time_table()
    elif sel == "ブログ投稿": member.page_blog_write()
    elif sel == "部費・集金": member.page_accounting_member()
    
    # --- 管理者用ページ ---
    elif sel == "部員名簿(管理者)": member.page_member_list()
    elif sel == "組レーン結果登録(管理者)": admin.page_result_registration()
    elif sel == "エントリー管理(競技会)": admin.page_entry_management()
    elif sel == "新規大会登録(競技会)": admin.page_competition_reg()
    elif sel == "データ登録・インポート(広報)": admin.page_migration()
    elif sel == "会計管理": admin.page_accounting_admin()

# 3. フッター表示
show_footer()