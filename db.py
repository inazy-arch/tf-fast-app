import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import utils 

SPREADSHEET_KEY = "156ClxCEF8kOhLIOOqTw_qX1g58sLq9Q5qBYfpF9B5Wg"

# --- 接続 ---
def get_gspread_client():
    try:
        key_dict = json.loads(st.secrets["gcp_service_account"]["json_content"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"GCP Error: {e}")
        return None

def get_sheet():
    client = get_gspread_client()
    if not client: return None
    try:
        return client.open_by_key(SPREADSHEET_KEY)
    except Exception as e:
        st.error(f"スプレッドシートエラー: {e}")
        return None

# --- Users ---
@st.cache_data(ttl=5)
def load_users():
    wb = get_sheet()
    if not wb: return {}
    try:
        try: sheet = wb.worksheet("members")
        except: return {}
        records = sheet.get_all_records()
        users = {}
        for r in records:
            uid = str(r.get("user_id"))
            if not uid: continue
            
            # JSON列の復元
            try: events = json.loads(str(r.get("events","")).replace("'", '"'))
            except: events = []
            if isinstance(events, str): events = [e.strip() for e in events.split(",") if e.strip()]
            
            try: pbs = json.loads(str(r.get("pbs","")).replace("'", '"'))
            except: pbs = {}
            
            # 必要なデータを辞書化
            u_data = r.copy()
            u_data["events"] = events
            u_data["pbs"] = pbs
            u_data["id"] = uid # idキーも確保
            users[uid] = u_data
        return users
    except: return {}

def save_user(uid, user_data):
    """
    列の場所を自動で探して保存する「絶対ズレない」バージョン
    """
    wb = get_sheet()
    if not wb: return False
    try:
        try: sheet = wb.worksheet("members")
        except: return False
        
        # 1. 1行目のヘッダー（列名）をすべて読み込む
        headers = sheet.row_values(1)
        
        # 2. 必要な列があるかチェック（なければ作る）
        required_cols = ["user_id", "image", "bio", "name", "role", "role_title", "status", "block", "affiliation", "univ_cat", "grad_year", "events", "pbs", "name_kana", "password"]
        
        # ヘッダーに足りない列があれば追加する機能
        missing_cols = [c for c in required_cols if c not in headers]
        if missing_cols:
            # 足りない列を右端に追加
            sheet.add_cols(len(missing_cols))
            # ヘッダーを更新
            first_row_len = len(headers)
            for i, col_name in enumerate(missing_cols):
                sheet.update_cell(1, first_row_len + i + 1, col_name)
            # ヘッダーを再取得
            headers = sheet.row_values(1)

        # 3. どのデータが何列目か（インデックス）を特定
        # 例: {"user_id": 0, "name": 1, "image": 13 ...}
        col_map = {name: i for i, name in enumerate(headers)}
        
        # 4. 保存する行のデータを作る
        # まずは空文字で埋めたリストを作る
        row_values = [""] * len(headers)
        
        # user_dataの中身を、正しい場所に配置する
        for key, val in user_data.items():
            if key in col_map:
                idx = col_map[key]
                # リストや辞書はJSON文字列に
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                row_values[idx] = val
        
        # 5. 更新対象の行を探す (user_id が一致する行)
        cell = None
        try:
            # user_id列(A列とは限らないので探す)
            uid_col_idx = col_map.get("user_id") + 1
            cell = sheet.find(str(uid), in_column=uid_col_idx)
        except:
            pass

        if cell:
            # 更新: その行をまるごと書き換え
            # gspreadの update メソッドで行更新
            # A1記法を作るのが面倒なので、行番号を指定して更新
            row_num = cell.row
            
            # 安全のため、セル範囲を計算して更新
            # 1行分の範囲 (例: A2:Z2)
            end_col_char = chr(ord('A') + len(row_values) - 1)
            # 列数が26を超えると 'AA' とかになるので、厳密にはこう書く↓
            sheet.update(f"A{row_num}", [row_values])
        else:
            # 新規: 末尾に追加
            sheet.append_row(row_values)
            
        load_users.clear()
        return True

    except Exception as e:
        print(f"Save User Error: {e}")
        return False

def save_users_batch(user_list):
    wb = get_sheet()
    if not wb: return False, "Connection Failed"
    try:
        sheet = wb.get_worksheet(0)
        records = sheet.get_all_records()
        existing_ids = {str(r["user_id"]): i for i, r in enumerate(records)}
        new_rows = []
        for u in user_list:
            uid = str(u["user_id"])
            if uid in existing_ids: continue 
            row_data = [
                uid, u.get("name", ""), u.get("name_kana", ""), "", "",
                str(u.get("password", "1234")), "player", "なし", "", "学部",
                "現役", u.get("block", ""), u.get("affiliation", ""), "", "", "{}"
            ]
            new_rows.append(row_data)
        if new_rows:
            sheet.append_rows(new_rows)
            load_users.clear()
            return True, f"{len(new_rows)} users added."
        else: return True, "No new users."
    except Exception as e: return False, str(e)

def save_all_users_overwrite(users_list):
    """
    ユーザーリスト(辞書のリスト)を受け取り、シート全体を上書き保存する
    """
    wb = get_sheet()
    if not wb: return False
    try:
        sheet = wb.worksheet("members")
        
        # ★修正: image と bio を追加して、全15列に合わせました
        header = [
            "user_id", "name", "password", "role", "role_title", "status", 
            "block", "affiliation", "univ_cat", "grad_year", 
            "events", "pbs", "name_kana", "image", "bio"
        ]
        
        # 2. データをリスト形式(行)に変換
        rows = [header] # 1行目はヘッダー
        
        for u in users_list:
            row = []
            for col in header:
                val = u.get(col, "")
                # リストや辞書は文字列(JSON)に変換して保存
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                row.append(val)
            rows.append(row)
            
        # 3. シートをクリアして書き込み
        sheet.clear()
        sheet.update(rows) 
        
        load_users.clear() # キャッシュクリア
        return True
    except Exception as e:
        st.error(f"Save All Users Error: {e}")
        return False
    
# --- Competitions ---
@st.cache_data(ttl=5)
def load_competitions():
    wb = get_sheet()
    if not wb: return []
    try:
        try: sheet = wb.worksheet("competitions")
        except: return []
        
        records = sheet.get_all_records()
        
        # ★互換性対応:
        # シート上は "comp_id", "comp_name" ですが、
        # アプリ側のコード(views)が "id", "name" を使っているため、
        # 両方のキーでアクセスできるように調整して返します。
        for r in records:
            # comp_id があれば id にも入れる
            if "comp_id" in r:
                r["id"] = r["comp_id"]
            # comp_name があれば name にも入れる
            if "comp_name" in r:
                r["name"] = r["comp_name"]
                
        return records
    except: return []

def save_competition(d):
    """
    大会を保存する
    列定義: comp_id, comp_name, date, location, deadline, status, events, valid_start, valid_end
    """
    wb = get_sheet()
    if not wb: return False
    try:
        try: s = wb.worksheet("competitions")
        except: 
            s = wb.add_worksheet("competitions", 100, 10)
            # ★ヘッダーを更新
            s.append_row(["comp_id", "comp_name", "date", "location", "deadline", "status", "events", "valid_start", "valid_end"])
        
        # ヘッダー確認 (もし古い "id", "name" のままなら、列名だけ修正するか、作り直すのが無難ですが、ここでは追加のみ行います)
        
        # 新規作成
        # d["name"] で渡ってくることが多いので、それを comp_name として保存
        c_name = d.get("name") or d.get("comp_name")
        
        new_row = [
            str(uuid.uuid4())[:8],  # comp_id
            c_name,                 # comp_name
            str(d["date"]), 
            d["location"], 
            str(d["deadline"]),
            d.get("status", "募集中"), 
            json.dumps(d["events"], ensure_ascii=False),
            str(d.get("valid_start") or ""), 
            str(d.get("valid_end") or "")
        ]
        s.append_row(new_row)
        load_competitions.clear()
        return True
    except Exception as e: 
        st.error(f"Save Error: {e}")
        return False

def update_competition_status(comp_id, new_status):
    wb = get_sheet()
    if not wb: return False
    try:
        sheet = wb.worksheet("competitions")
        cell = sheet.find(str(comp_id))
        if cell:
            # statusはF列(6)と仮定するが、検索して特定推奨
            header = sheet.row_values(1)
            col_idx = header.index("status") + 1
            sheet.update_cell(cell.row, col_idx, new_status)
            load_competitions.clear()
            return True
    except: pass
    return False

# --- Entries ---
@st.cache_data(ttl=5)
def load_entries(cid=None):
    wb = get_sheet()
    if not wb: return []
    try:
        sheet = wb.worksheet("entries")
        recs = sheet.get_all_records()
        if cid: return [r for r in recs if str(r.get("comp_id")) == str(cid)]
        return recs
    except: return []

def save_entry(d):
    wb = get_sheet()
    if not wb: return False
    try:
        try: s = wb.worksheet("entries")
        except: s = wb.add_worksheet("entries", 1000, 10)
        
        # 既存チェック
        records = s.get_all_records()
        target_row = None
        for i, r in enumerate(records):
            if str(r.get("comp_id")) == str(d["comp_id"]) and str(r.get("user_id")) == str(d["user_id"]):
                target_row = i + 2
                break
        
        row_data = [
            d.get("entry_id", str(uuid.uuid4())[:8]),
            str(d["comp_id"]), str(d["user_id"]), d["user_name"],
            json.dumps(d["events"], ensure_ascii=False),
            json.dumps(d["times"], ensure_ascii=False),
            d.get("comment", ""), str(datetime.now())
        ]
        
        if target_row:
            # 列数に合わせて更新（A:H）
            s.update(f"A{target_row}:H{target_row}", [row_data])
        else:
            if not records: s.append_row(["entry_id","comp_id","user_id","user_name","events","times","comment","timestamp"])
            s.append_row(row_data)
            
        load_entries.clear()
        return True
    except: return False

# --- Results (Normalized) ---
# ここが重要：保存はIDのみ、読み込み時にJOIN

@st.cache_data(ttl=3)
def load_results(comp_id=None):
    wb = get_sheet()
    if not wb: return []
    try:
        try: sheet = wb.worksheet("results")
        except: return []
        
        raw_results = sheet.get_all_records()
        if not raw_results: return []

        # 1. 大会マスタと部員マスタを取得
        comps = load_competitions()
        comp_map = {str(c["id"]): c for c in comps}
        
        users = load_users() # ID -> UserData
        
        cleaned_results = []
        
        target_cid = str(comp_id) if comp_id else None
        
        for r in raw_results:
            # フィルタリング
            row_cid = str(r.get("comp_id", ""))
            if target_cid and row_cid != target_cid: continue
            
            row_uid = str(r.get("user_id", ""))
            
            # --- JOIN処理 ---
            # 大会情報
            c_info = comp_map.get(row_cid, {})
            comp_name = c_info.get("name", "未登録大会")
            comp_date = str(c_info.get("date", "2000-01-01"))
            
            # 部員情報
            u_info = users.get(row_uid, {})
            user_name = u_info.get("name", "未登録選手")
            
            # データ構築 (UI表示用に名称を含める)
            cleaned_results.append({
                "result_id": str(r.get("result_id", "")),
                "comp_id": row_cid,
                "comp_name": comp_name, # 表示用
                "date": comp_date,      # 表示用
                
                "user_id": row_uid,
                "user_name": user_name, # 表示用
                
                "event": str(r.get("event", "")),
                "division": str(r.get("division", "")),
                "round": str(r.get("round", "")),
                "heat": str(r.get("heat", "")),
                "lane": str(r.get("lane", "")),
                "result": str(r.get("result", "")),
                "wind": str(r.get("wind", "")),
                "rank": str(r.get("rank", "")),
                "comment": str(r.get("comment", ""))
            })
            
        return cleaned_results
    except Exception as e:
        print(e)
        return []

def save_results_batch(results_list):
    """
    結果データを保存する。ヘッダーがない場合は強制的に挿入する。
    """
    wb = get_sheet()
    if not wb: return False
    try:
        # シート取得（なければ作成）
        try: sheet = wb.worksheet("results")
        except: sheet = wb.add_worksheet("results", 5000, 15)
        
        # ★決定版のヘッダー定義
        header = [
            "result_id", "comp_id", "user_id", "event", 
            "division", "round", "heat", "lane", 
            "result", "wind", "rank", "comment"
        ]
        
        # ★修正ポイント: get_all_values() ではなく、具体的に1行目を確認する
        # 1行目のデータを取得
        first_row = sheet.row_values(1)
        
        # 「1行目が空っぽ」または「1行目の先頭が result_id ではない」場合
        # ヘッダー行を【挿入】します（appendではなくinsertを使うことで最上段を確保）
        if not first_row or first_row[0] != "result_id":
            sheet.insert_row(header, index=1)
            
        # データ作成
        rows_to_add = []
        for r in results_list:
            if not r.get("comp_id") or not r.get("result"):
                continue
                
            row = [
                str(r.get("result_id", uuid.uuid4())), 
                str(r.get("comp_id")),
                str(r.get("user_id", "")),
                str(r.get("event", "")),
                str(r.get("division", "")),
                str(r.get("round", "")),
                str(r.get("heat", "")),
                str(r.get("lane", "")),
                str(r.get("result", "")),
                str(r.get("wind", "")),
                str(r.get("rank", "")),
                str(r.get("comment", ""))
            ]
            rows_to_add.append(row)
            
        if rows_to_add:
            sheet.append_rows(rows_to_add)
            load_results.clear()
            return True
        
        return True
        
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

# --- Start List (Start List も正規化思想で扱うが、便宜上名前も保持する場合がある。今回はIDベースで検索) ---
@st.cache_data(ttl=10)
def load_start_list(comp_id):
    """ 指定された大会のスタートリスト（番組編成）を読み込む """
    wb = get_sheet()
    if not wb: return []
    try:
        try: sheet = wb.worksheet("start_list")
        except: return []
        
        records = sheet.get_all_records()
        # comp_id が一致するものだけ抽出 (文字列にして比較)
        target_str = str(comp_id)
        return [r for r in records if str(r.get("comp_id")) == target_str]
    except:
        return []

def save_start_list_overwrite(comp_id, data_list):
    """ 指定された大会のスタートリストを上書き保存する """
    wb = get_sheet()
    if not wb: return False
    try:
        try: sheet = wb.worksheet("start_list")
        except: sheet = wb.add_worksheet("start_list", 1000, 20)
        
        # 1. 既存データを全取得
        all_records = sheet.get_all_records()
        
        # 2. 今回保存する大会以外のデータは残す
        target_str = str(comp_id)
        kept_records = [r for r in all_records if str(r.get("comp_id")) != target_str]
        
        # 3. 新しいデータを追加（comp_idを付与）
        for row in data_list:
            row["comp_id"] = target_str
            kept_records.append(row)
        
        # 4. シートをクリアして全書き込み
        if kept_records:
            header = list(kept_records[0].keys())
            # 順番を整えるための固定ヘッダー定義
            preferred_order = ["comp_id", "競技始", "種目", "組", "レーン", "ナンバー", "氏名", "現PB", "目標記録", "所属", "招集始", "招集終", "備考"]
            # データに含まれるキーだけでヘッダーを作る
            final_header = [h for h in preferred_order if h in header] + [h for h in header if h not in preferred_order]
            
            rows = [final_header]
            for r in kept_records:
                rows.append([r.get(col, "") for col in final_header])
            
            sheet.clear()
            sheet.update(rows)
        else:
            sheet.clear() # データが空になった場合
            
        load_start_list.clear() # キャッシュクリア
        return True
    except Exception as e:
        st.error(f"Save Start List Error: {e}")
        return False

###########################################################################
###########################################################################
# get_user_best_in_period, News, Blog, Accountingなどは既存を使用してください
@st.cache_data(ttl=5)
def load_fees():
    """ 集金イベント一覧を読み込む """
    wb = get_sheet()
    if not wb: return []
    try:
        try: sheet = wb.worksheet("accounting")
        except: return []
        
        records = sheet.get_all_records()
        # status_map (誰が払ったか) はJSONなので復元
        for r in records:
            if isinstance(r.get("status_map"), str):
                try: r["status_map"] = json.loads(r["status_map"].replace("'", '"'))
                except: r["status_map"] = {}
        return records
    except:
        return []

def save_fee_event(fee_data):
    """ 新しい集金イベントを作成・更新 """
    wb = get_sheet()
    if not wb: return False
    try:
        try: sheet = wb.worksheet("accounting")
        except: sheet = wb.add_worksheet("accounting", 1000, 10)
        
        # 既存データを全取得
        all_records = sheet.get_all_records()
        
        # IDが一致するものがあれば更新、なければ追加
        target_id = str(fee_data["id"])
        updated = False
        
        # 保存用にデータを整形
        save_row = {
            "id": target_id,
            "title": fee_data["title"],
            "amount": fee_data["amount"],
            "deadline": fee_data["deadline"],
            # 辞書はJSON文字列化
            "status_map": json.dumps(fee_data["status_map"], ensure_ascii=False)
        }
        
        # ヘッダー確認 & 行構築
        header = ["id", "title", "amount", "deadline", "status_map"]
        
        # シートが空ならヘッダー追加
        if not all_records and sheet.row_values(1) == []:
            sheet.append_row(header)
            all_records = []

        # 更新対象を探す
        target_row_idx = -1
        for i, r in enumerate(all_records):
            if str(r.get("id")) == target_id:
                target_row_idx = i + 2 # 1行目ヘッダー + 0始まり補正
                break
        
        row_vals = [save_row[h] for h in header]
        
        if target_row_idx > 0:
            # 更新 (A列～E列)
            sheet.update(f"A{target_row_idx}:E{target_row_idx}", [row_vals])
        else:
            # 新規追加
            sheet.append_row(row_vals)
            
        load_fees.clear()
        return True
    except Exception as e:
        print(f"Fee Save Error: {e}")
        return False
    
# db.py に追加・修正

# === 📢 公式News (自動生成される結果報告) ===
@st.cache_data(ttl=10)
def load_news():
    wb = get_sheet()
    if not wb: return []
    try:
        # シート名を 'news' に変更
        try: sheet = wb.worksheet("news")
        except: return []
        records = sheet.get_all_records()
        records.sort(key=lambda x: x.get("date", ""), reverse=True)
        return records
    except: return []

def save_news(news_data):
    """ Newsを保存 (ID, date, title, content) """
    wb = get_sheet()
    if not wb: return False
    try:
        try: sheet = wb.worksheet("news")
        except: sheet = wb.add_worksheet("news", 1000, 10)
        
        # ヘッダー確認
        if not sheet.get_all_values():
            sheet.append_row(["id", "date", "title", "content"]) # 画像や著者は不要
            
        sheet.append_row([
            news_data["id"], 
            news_data["date"], 
            news_data["title"], 
            news_data["content"]
        ])
        load_news.clear()
        return True
    except: return False

# === 📝 選手ブログ ===
@st.cache_data(ttl=10)
def load_blogs():
    wb = get_sheet()
    if not wb: return []
    try:
        try: sheet = wb.worksheet("blogs")
        except: return []
        records = sheet.get_all_records()
        records.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return records
    except: return []

def save_blog(blog_data):
    """ ブログを保存 """
    wb = get_sheet()
    if not wb: return False
    try:
        try: sheet = wb.worksheet("blogs")
        except: sheet = wb.add_worksheet("blogs", 1000, 10)
        
        header = ["id", "created_at", "title", "content", "author_name", "author_id", "image"]
        if not sheet.get_all_values(): sheet.append_row(header)
        
        # 新規追加のみ実装（編集は省略）
        sheet.append_row([
            blog_data["id"],
            blog_data["created_at"],
            blog_data["title"],
            blog_data["content"],
            blog_data["author_name"],
            blog_data["author_id"],
            blog_data.get("image", "")
        ])
        load_blogs.clear()
        return True
    except: return False

# --- db.py の末尾に追加 ---

def get_user_best_in_period(user_id, event, start_date=None, end_date=None):
    """
    指定された期間内での、特定のユーザー・種目のベスト記録データを返します。
    （トラック種目はタイムの最小値、フィールド種目は距離の最大値をベストとみなします）
    """
    # 1. 全リザルトを読み込む
    results = load_results(None)
    
    # 2. 対象の記録をフィルタリング（抽出）
    targets = []
    for r in results:
        # IDチェック
        if str(r.get("user_id")) != str(user_id): continue
        # 種目チェック
        if r.get("event") != event: continue
        
        # 日付チェック（期間指定がある場合のみ）
        r_date = r.get("date") # "YYYY-MM-DD"形式
        if not r_date: continue
        
        if start_date and r_date < start_date: continue
        if end_date and r_date > end_date: continue
        
        targets.append(r)

    if not targets:
        return None

    # 3. ベスト記録を選定するロジック
    best_record = None
    best_val = None
    
    # 簡易判定: 種目名に特定の文字が含まれる場合は「フィールド種目（大きい方が良い）」とする
    # それ以外は「トラック種目（小さい方が良い）」とする
    is_field = False
    field_keywords = ["跳", "投", "砲丸", "円盤", "やり", "ハンマー", "ジャベリックス"]
    for k in field_keywords:
        if k in event:
            is_field = True
            break

    for r in targets:
        try:
            # 記録を数値に変換してみる
            val = float(str(r["result"]).strip())
        except:
            # 数値にできないもの（DNS, NM, 欠場など）はスキップ
            continue

        if best_val is None:
            best_val = val
            best_record = r
        else:
            if is_field:
                # フィールド: 数値が大きい方が良い
                if val > best_val:
                    best_val = val
                    best_record = r
            else:
                # トラック: 数値（タイム）が小さい方が良い
                if val < best_val:
                    best_val = val
                    best_record = r
                    
    return best_record