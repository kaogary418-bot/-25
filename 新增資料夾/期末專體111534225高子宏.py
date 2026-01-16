import json, os, base64
from flask import Flask, request, redirect, url_for, session, render_template_string

app = Flask(__name__)
app.secret_key = "nuk_rich_options_v25"

# --- 1. 資料路徑設定 ---
COURSES_FILE = "courses.json"
SELECTIONS_FILE = "selections.json"
USERS_FILE = "users_profile.json"

# --- 2. 擴充選單資料庫 ---
# 班級選單選項
DEPARTMENTS = [
    "數應一A", "數應一B", "數應二A", "數應三A", 
    "資工一A", "資工二B", "電機一A", "土木三A",
    "資管二B", "企管一A", "法律一A", "西洋語一A",
    "運動一A", "全校通識", "體育選項"
]

# 預設快速新增科目
PRESET_SUBJECTS = [
    "微積分", "線性代數", "程式設計", "資料結構", 
    "英文寫作", "物理學", "離散數學", "網頁開發",
    "通識：心理學", "通識：音樂欣賞", "體育：羽球", "體育：游泳"
]

def get_default_courses():
    """預設鎖定的 API 課程"""
    return [
        {"id": 101, "name": "高等微積分", "class": "數應一A", "time": "週一, 週三", "is_api": True},
        {"id": 102, "name": "人工智慧導論", "class": "資工三B", "time": "週二", "is_api": True},
        {"id": 103, "name": "大學體育", "class": "體育選項", "time": "週五", "is_api": True}
    ]

# --- 3. JSON 資料存取工具 ---
def load_json(path, default_factory):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default_factory()
    return default_factory()

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 4. 前端介面 (HTML/JS) ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>NUK 選課系統</title>
    <style>
        :root { --primary: #2563eb; --success: #10b981; --danger: #ef4444; --warning: #f59e0b; --bg: #f8fafc; }
        body { font-family: 'PingFang TC', sans-serif; background: var(--bg); margin: 0; }
        .nav { background: #1e293b; color: white; padding: 12px 30px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
        .user-avatar { width: 42px; height: 42px; border-radius: 50%; border: 2px solid white; object-fit: cover; background: #ddd; cursor: pointer; }
        .main { display: flex; padding: 20px; gap: 20px; }
        .sidebar { width: 320px; background: white; padding: 20px; border-radius: 12px; height: fit-content; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .container { flex: 1; display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
        .card { background: white; padding: 15px; border-radius: 12px; border: 2px solid #e2e8f0; position: relative; transition: 0.3s; }
        .selected { border: 2px solid var(--success); background: #f0fdf4; }
        .btn { padding: 10px; border-radius: 6px; border: none; font-weight: bold; width: 100%; cursor: pointer; margin-top: 8px; font-size: 14px; }
        .btn-add { background: var(--primary); color: white; }
        .btn-edit { background: var(--warning); color: white; border: 1px solid #000; }
        .input { width: 100%; padding: 10px; margin: 5px 0 10px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        .label { font-size: 13px; font-weight: bold; color: #475569; }
        .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
        #editModal, #profileModal { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 15px; z-index: 1001; width: 360px; box-shadow: 0 0 40px rgba(0,0,0,0.3); }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="overlay" id="overlay" onclick="closeAll()"></div>

    <div id="editModal">
        <h3>✏️ 編輯課程</h3>
        <form action="/edit_course" method="POST">
            <input type="hidden" name="course_id" id="modal_id">
            <div class="label">課程名稱</div>
            <input name="name" id="modal_name" class="input" required>
            <div class="label">調整上課日</div>
            <div style="display:flex; gap:5px;">
                <select name="d1" class="input">{% for d in ['週一','週二','週三','週四','週五'] %}<option value="{{d}}">{{d}}</option>{% endfor %}</select>
                <select name="d2" class="input"><option value="">無</option>{% for d in ['週一','週二','週三','週四','週五'] %}<option value="{{d}}">{{d}}</option>{% endfor %}</select>
            </div>
            <button class="btn btn-add">儲存修改</button>
        </form>
    </div>

    <div id="profileModal">
        <h3>👤 修改個人資料</h3>
        <form action="/update_profile" method="POST" enctype="multipart/form-data">
            <div class="label">更換顯示名稱</div>
            <input name="new_name" value="{{ user.name }}" class="input">
            <div class="label">修改密碼</div>
            <input type="password" name="new_pw" class="input" placeholder="不改請留空">
            <div class="label">更換大頭貼</div>
            <input type="file" name="avatar_file" class="input" accept="image/*">
            <button class="btn btn-add">確認更新</button>
        </form>
    </div>

    <nav class="nav">
        <div style="font-weight:bold; font-size:1.2rem;">🏛️ NUK 智慧選課系統</div>
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="text-align:right">
                <div style="font-weight:bold;">{{ user.name }}</div>
                <div style="font-size:11px; color:#cbd5e1;">已選 {{ sel_ids|length }} 門課</div>
            </div>
            <img src="{{ user.avatar if user.avatar else 'https://ui-avatars.com/api/?name='+user.name }}" class="user-avatar" onclick="openProfile()">
            <a href="/logout" style="color:#f87171; text-decoration:none; font-size:12px;">登出</a>
        </div>
    </nav>

    <div class="main">
        <aside class="sidebar">
            <button class="btn" style="background:#6366f1; color:white;" onclick="location.href='/?mode={{ 'all' if filter_mode=='selected' else 'selected' }}'">
                {{ '🔍 顯示全部課程' if filter_mode=='selected' else '✅ 只看我的加選' }}
            </button>
            <hr>
            <h4>➕ 自定義新增課程</h4>
            <form action="/add_course" method="POST">
                <div class="label">選擇科目</div>
                <select name="preset_name" class="input" id="pSelect" onchange="toggleCustom()">
                    {% for s in presets %}<option value="{{s}}">{{s}}</option>{% endfor %}
                    <option value="CUSTOM">-- 手動輸入 --</option>
                </select>
                <input name="custom_name" id="cInput" placeholder="請輸入科目名稱" class="input hidden">

                <div class="label">選擇班級</div>
                <select name="class_name" class="input">
                    {% for d in depts %}<option value="{{d}}">{{d}}</option>{% endfor %}
                </select>

                <button class="btn btn-add">建立課程並存檔</button>
            </form>
            <hr>
            <div style="text-align:center;"><a href="/reset" style="color:#94a3b8; font-size:11px; text-decoration:none;">🔄 重置系統資料</a></div>
        </aside>

        <section class="container">
            {% for c in courses %}
            {% if filter_mode == 'all' or (filter_mode == 'selected' and c.id in sel_ids) %}
            <div class="card {{ 'selected' if c.id in sel_ids }}">
                <div style="color:#64748b; font-size:11px;">{{ c.class }}</div>
                <div style="font-weight:bold; margin:5px 0; font-size:1.1rem;">{{ c.name }}</div>
                <div style="font-size:13px; color:var(--primary);">📅 {{ c.time }}</div>
                
                {% if c.id in sel_ids %}
                    <a href="/drop/{{ c.id }}"><button class="btn" style="background:var(--danger); color:white;">退選課程</button></a>
                {% else %}
                    <a href="/pick/{{ c.id }}"><button class="btn btn-add">加選課程</button></a>
                {% endif %}

                {% if not c.is_api %}
                <div style="display:flex; gap:5px;">
                    <button class="btn btn-edit edit-trigger" data-id="{{ c.id }}" data-name="{{ c.name }}">編輯</button>
                    <a href="/del_course/{{ c.id }}" style="flex:1;"><button class="btn" style="background:#e2e8f0; color:#475569;">刪除</button></a>
                </div>
                {% endif %}
            </div>
            {% endif %}
            {% endfor %}
        </section>
    </div>

    <script>
        function toggleCustom() { document.getElementById('cInput').classList.toggle('hidden', document.getElementById('pSelect').value !== 'CUSTOM'); }
        function openProfile() { document.getElementById('profileModal').style.display='block'; document.getElementById('overlay').style.display='block'; }
        function closeAll() { document.getElementById('profileModal').style.display='none'; document.getElementById('editModal').style.display='none'; document.getElementById('overlay').style.display='none'; }

        // 綁定編輯觸發
        document.querySelectorAll('.edit-trigger').forEach(btn => {
            btn.onclick = function() {
                document.getElementById('modal_id').value = this.getAttribute('data-id');
                document.getElementById('modal_name').value = this.getAttribute('data-name');
                document.getElementById('editModal').style.display = 'block';
                document.getElementById('overlay').style.display = 'block';
            };
        });
    </script>
</body>
</html>
'''

# --- 5. 後端路由邏輯 ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """帳密：student / 1234"""
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        users = load_json(USERS_FILE, lambda: {"student": {"pw": "1234", "name": "學生用戶", "avatar": ""}})
        if u in users and users[u]['pw'] == p:
            session['user'] = u
            return redirect(url_for('index'))
        return "帳號或密碼錯誤！"
    return '<body style="background:#1e293b; color:white; display:flex; justify-content:center; align-items:center; height:100vh;"><form method="post" style="background:white; padding:40px; border-radius:15px; color:black;"><h2>NUK 選課登入</h2><input name="u" placeholder="帳號" style="display:block;margin:10px 0;padding:10px;"><input name="p" type="password" placeholder="密碼" style="display:block;margin:10px 0;padding:10px;"><button style="width:100%;padding:10px;background:#2563eb;color:white;border:none;border-radius:5px;">進入系統</button></form></body>'

@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    u = session['user']
    mode = request.args.get('mode', 'all')
    users = load_json(USERS_FILE, lambda: {"student": {"pw": "1234", "name": "學生用戶", "avatar": ""}})
    courses = load_json(COURSES_FILE, get_default_courses)
    sels = load_json(SELECTIONS_FILE, lambda: {})
    # 傳送擴充後的選單資料給前端
    return render_template_string(HTML_UI, user=users[u], courses=courses, sel_ids=sels.get(u, []), filter_mode=mode, depts=DEPARTMENTS, presets=PRESET_SUBJECTS)

@app.route('/add_course', methods=['POST'])
def add_course():
    """處理新增課程邏輯"""
    db = load_json(COURSES_FILE, get_default_courses)
    name = request.form.get('custom_name') if request.form.get('preset_name') == "CUSTOM" else request.form.get('preset_name')
    cls = request.form.get('class_name')
    new_id = max([c['id'] for c in db]) + 1 if db else 100
    db.append({"id": new_id, "name": name, "class": cls, "time": "週一", "is_api": False})
    save_json(COURSES_FILE, db)
    return redirect(url_for('index'))

@app.route('/edit_course', methods=['POST'])
def edit_course():
    """編輯現有課程"""
    db = load_json(COURSES_FILE, get_default_courses)
    cid = int(request.form.get('course_id'))
    days = [request.form.get('d1'), request.form.get('d2')]
    time_str = ", ".join([d for d in days if d])
    for c in db:
        if c['id'] == cid:
            c['name'] = request.form.get('name')
            c['time'] = time_str
    save_json(COURSES_FILE, db)
    return redirect(url_for('index'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    """更新名字、密碼與頭像照片"""
    u = session['user']
    users = load_json(USERS_FILE, lambda: {})
    users[u]['name'] = request.form.get('new_name')
    if request.form.get('new_pw'): users[u]['pw'] = request.form.get('new_pw')
    file = request.files.get('avatar_file')
    if file and file.filename != '':
        encoded = base64.b64encode(file.read()).decode('utf-8')
        users[u]['avatar'] = f"data:{file.content_type};base64,{encoded}"
    save_json(USERS_FILE, users)
    return redirect(url_for('index'))

# --- 課程加選路由 ---
@app.route('/pick/<int:cid>')
def pick(cid):
    u = session['user']  # 從 Session 獲取當前登入的使用者帳號
    # 讀取選課紀錄 JSON 檔，若檔案不存在則回傳空字典
    sels = load_json(SELECTIONS_FILE, lambda: {}) 
    
    # 如果該使用者還沒有選課紀錄，先幫他建立一個空清單
    if u not in sels: sels[u] = []
    
    # 如果這門課(cid)還不在使用者的選課清單中，則加入
    if cid not in sels[u]: sels[u].append(cid)
    
    # 將更新後的選課資料存回 JSON 檔案中，確保資料持久化
    save_json(SELECTIONS_FILE, sels)
    return redirect(url_for('index'))  # 動作完成後跳轉回主頁

# --- 課程退選路由 ---
@app.route('/drop/<int:cid>')
def drop(cid):
    u = session['user']
    sels = load_json(SELECTIONS_FILE, lambda: {})
    
    # 檢查該使用者是否有選課紀錄，且該課程是否在清單中
    if u in sels and cid in sels[u]: 
        sels[u].remove(cid)  # 從清單中移除該課程 ID
        
    save_json(SELECTIONS_FILE, sels)
    return redirect(url_for('index'))

# --- 徹底刪除課程路由 (僅限手動新增課程) ---
@app.route('/del_course/<int:cid>')
def del_course(cid):
    # 讀取主課程資料庫
    db = load_json(COURSES_FILE, get_default_courses)
    
    # 使用串列綜合解構 (List Comprehension) 過濾掉要刪除的課程 ID
    db = [c for c in db if c['id'] != cid]
    
    save_json(COURSES_FILE, db)  # 儲存更新後的課程資料庫
    return redirect(url_for('index'))

# --- 系統重置路由 ---
@app.route('/reset')
def reset():
    # 遍歷所有的資料檔 (課程、選課紀錄、用戶資料)
    for f in [COURSES_FILE, SELECTIONS_FILE, USERS_FILE]:
        if os.path.exists(f): 
            os.remove(f)  # 刪除實體檔案，達成清空效果
            
    return redirect(url_for('login'))  # 重置後強制跳回登入頁

# --- 使用者登出路由 ---
@app.route('/logout')
def logout():
    """
    此函數負責清除目前使用者的連線狀態 (Session)
    讓系統回到未登入的狀態
    """
    session.clear()  # 清空所有的 Session 資料 (包含使用者帳號、權限等)
    return redirect(url_for('login'))  # 清除完成後，重新導向到登入畫面

# --- 程式主入口 (Entry Point) ---
if __name__ == '__main__':
    """
    當這份 .py 檔被直接執行時，會執行下方的程式碼。
    debug=True 代表開啟開發模式，程式碼存檔後會自動重新載入，
    且網頁報錯時會顯示詳細的除錯訊息 (方便開發與老師檢查)。
    """
    app.run(debug=True)
    # --- 課程加選路由 (加入人數上限控管) ---
@app.route('/pick/<int:cid>')
def pick(cid):
    u = session['user']
    # 讀取課程資料庫與選課紀錄
    courses = load_json(COURSES_FILE, get_default_courses)
    sels = load_json(SELECTIONS_FILE, lambda: {})
    
    # 找出該課程的詳細資料 (為了取得人數上限)
    target_course = next((c for c in courses if c['id'] == cid), None)
    
    # 計算目前這門課有多少人選 (遍歷所有使用者的選課紀錄)
    current_enrolled = sum(1 for user_id in sels if cid in sels[user_id])
    
    # 設定預設上限 (如果資料沒寫，預設為 5 人)
    max_cap = target_course.get('max_capacity', 5)

    # --- 核心控管邏輯 ---
    if current_enrolled >= max_cap:
        # 如果人數已滿，回傳提示 (也可以跳轉回主頁並顯示錯誤)
        return f"選課失敗！{target_course['name']} 人數已滿 (上限 {max_cap} 人)"
    
    # 若人數未滿，執行原本的加選邏輯
    if u not in sels: sels[u] = []
    if cid not in sels[u]: 
        sels[u].append(cid)
    
    save_json(SELECTIONS_FILE, sels)
    return redirect(url_for('index'))