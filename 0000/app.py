import streamlit as st
import google.generativeai as genai
import json
import os

# ==========================================
# 1. 遊戲基礎設定與介面初始化
# ==========================================
st.set_page_config(page_title="AI 海龜湯情境猜謎系統", layout="wide", page_icon="🐢")

# 修正：st.html 不需要 unsafe_allow_html=True
st.html("""
<style>
/* ===== 全站背景 ===== */
[data-testid="stAppViewContainer"]{
    background:
    radial-gradient(circle at 20% 20%, rgba(0,212,255,.18), transparent 30%),
    radial-gradient(circle at 80% 30%, rgba(168,85,247,.18), transparent 30%),
    radial-gradient(circle at 50% 80%, rgba(0,212,255,.10), transparent 40%),
    linear-gradient(135deg, #020617 0%, #0f172a 40%, #111827 70%, #030712 100%);
    color:white;
}

[data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottomBlockContainer"], div[data-testid="stBottom"] > div {
    background-color: transparent !important;
    background: transparent !important;
}

.main .block-container {
    background-image:
        linear-gradient(rgba(15, 23, 42, 0.75), rgba(15, 23, 42, 0.75)),
        linear-gradient(135deg, #00d4ff, #8b5cf6, #ff007f, #00ffcc, #00d4ff) !important;
    background-origin: border-box !important;
    background-clip: padding-box, border-box !important;
    background-size: 300% 300% !important;
    border: 2px solid transparent !important;
    border-radius: 20px !important;
    backdrop-filter: blur(12px);
    padding: 2rem;
}

h1{
    color:white !important;
    text-shadow: 0 0 10px #00d4ff, 0 0 20px #00d4ff, 0 0 40px #8b5cf6;
}

h2, h3, p, li, label, span, [data-testid="stMarkdownContainer"] p {
    color: white !important;
}

section[data-testid="stSidebar"]{
    background: linear-gradient(180deg, rgba(5,10,20,.95), rgba(15,23,42,.95));
    border-right:1px solid rgba(0,212,255,.3);
}
section[data-testid="stSidebar"] * { color: white !important; }

.stButton button{
    background: linear-gradient(90deg, #00d4ff, #8b5cf6) !important;
    color:white !important;
    border:none !important;
    border-radius:12px !important;
    font-weight:bold !important;
}
.stButton button:hover{
    transform: translateY(-2px) !important;
    box-shadow: 0 0 15px #00d4ff, 0 0 50px #8b5cf6 !important;
}

div[data-baseweb="select"] *, div[data-baseweb="popover"] *, [data-baseweb="menu"] * {
    color: #000000 !important;
}
</style>
""")

# ---- 核心資安：從 Streamlit Cloud Secrets 讀取金鑰 ----
api_key = ""
if "Gemini_Key" in st.secrets:
    api_key = st.secrets["Gemini_Key"]
else:
    api_key_input = st.sidebar.text_input("請輸入 API Key：", type="password")
    api_key = api_key_input

if not api_key:
    st.warning("⚠️ 請先設定 GEMINI_KEY 以啟動遊戲")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 2. 讀取外部題庫與初始化成就紀錄
# ==========================================
try:
    with open('riddles.json', 'r', encoding='utf-8') as f:
        riddle_bank = json.load(f)
except FileNotFoundError:
    st.error("❌ 找不到題庫檔案 'riddles.json'！")
    st.stop()

if "completed_riddles" not in st.session_state:
    st.session_state.completed_riddles = []
if "completed_histories" not in st.session_state:
    st.session_state.completed_histories = {}
if "page" not in st.session_state:
    st.session_state.page = "home"

def navigate_to_solved_riddle(title):
    st.session_state.selectbox_title = title
    st.session_state.current_title = title
    if title in st.session_state.completed_histories:
        st.session_state.chat_history = list(st.session_state.completed_histories[title])
    else:
        st.session_state.chat_history = []

# ==========================================
# 3. 頁面分流架構 (首頁 vs 遊戲頁)
# ==========================================
if st.session_state.page == "home":
    st.title("🐢 AI 海龜湯遊戲系統")
    st.markdown("## 歡迎來到情境猜謎的世界！")
    
    # 修正：確保多行文字正確包在 st.markdown 的引號內，避免排版與語法錯誤
    st.markdown("""
    海龜湯是一種考驗邏輯思考與想像力的遊戲。
    你將看到一個表面看似不合理、不完整的神祕事件，你需要透過不斷向 AI 主持人提問來抽絲剝繭，最終拼湊出完整的真相。

    ### 🎮 遊戲核心模式：
    1. **提問模式**：您可以自由向 AI 提問，但主持人非常嚴格，只會回答：是、不是、與故事/題目無關、不完全是。
    2. **認證完整答案模式**：當您在提問中拼湊出完整的真相後，切換至此模式提交答案。若答對核心，即可完美通關並解鎖完整謎底！
    """)

    st.info("💡 準備好挑戰您的邏輯推理極限了嗎？點擊下方按鈕開始遊戲吧！")
    if st.button("進入遊戲", use_container_width=True):
        st.session_state.page = "game"
        st.rerun()

elif st.session_state.page == "game":
    st.title("AI海龜湯遊戲系統")
    st.sidebar.header("⚙️ 遊戲控制台")

    if st.sidebar.button("返回首頁", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

    riddle_titles = [item["title"] for item in riddle_bank]

    if "selectbox_title" not in st.session_state:
        st.session_state.selectbox_title = riddle_titles[0]

    selected_title = st.sidebar.selectbox("📚 挑選題目：", riddle_titles, key="selectbox_title")

    current_puzzle = next(item for item in riddle_bank if item["title"] == selected_title)
    riddle_text = current_puzzle["riddle"]
    secret_answer_text = current_puzzle["secret_answer"]

    st.sidebar.markdown("---")
    st.sidebar.subheader("🏁 已完成的題目紀錄")
    if st.session_state.completed_riddles:
        for solved in st.session_state.completed_riddles:
            st.sidebar.button(
                f"✅ {solved}",
                key=f"nav_btn_{solved}",
                use_container_width=True,
                on_click=navigate_to_solved_riddle,
                args=(solved,)
            )
    else:
        st.sidebar.write("💡 尚未有完成紀錄，加油！")

    if "current_title" not in st.session_state:
        st.session_state.current_title = selected_title
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.session_state.current_title != selected_title:
        st.session_state.current_title = selected_title
        if selected_title in st.session_state.completed_histories:
            st.session_state.chat_history = list(st.session_state.completed_histories[selected_title])
        else:
            st.session_state.chat_history = []
        st.rerun()

    st.info(f"### 當前湯面：\n\n {riddle_text}")

    game_mode = st.radio(
        "請選擇互動模式：",
        ["提問模式 (是非題尋找線索)", "認證完整答案模式 (提交真相)"],
        horizontal=True
    )

    st.divider()

    for message in st.session_state.chat_history:
        current_avatar = "🔴" if message["role"] == "user" else "🍊"
        with st.chat_message(message["role"], avatar=current_avatar):
            st.markdown(message["content"])

    if user_input := st.chat_input("在下方輸入您的內容..."):
        with st.chat_message("user", avatar="🔴"):
            st.markdown(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        if game_mode == "提問模式 (是非題尋找線索)":
            defense_prompt = f"""
            你現在是專業海龜湯主持人。
            題目：{riddle_text}
            真相：{secret_answer_text}
            玩家提問：{user_input}
            【規則】：你只能回答以下四種字串之一，絕對不能解釋：
            是、不是、與故事/題目無關、不完全是。
            """
        else:
            defense_prompt = f"""
            你現在是專業海龜湯主持人。
            題目：{riddle_text}
            真相：{secret_answer_text}
            玩家提交了真相推論：{user_input}
            【規則】：
            1. 比對玩家答案是否抓到真相核心。
            2. 如果玩家答對，請務必在回應開頭加上「🎉 恭喜完全答對！」並在此句之後公布這題的完整真相謎底（{secret_answer_text}）。
            3. 如果玩家答錯，請告知玩家尚未抓到重點，並提示可換回提問模式。
            """

        formatted_history = []
        for msg in st.session_state.chat_history[:-1]:
            formatted_history.append({"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]})

        try:
            # 修正：將模型名稱改為正確的 'gemini-1.5-flash'
            model = genai.GenerativeModel('gemini-1.5-flash')
            chat = model.start_chat(history=formatted_history)

            with st.spinner("主持人思考中..."):
                response = chat.send_message(defense_prompt)
                ai_reply = response.text.strip()

                if game_mode == "提問模式 (是非題尋找線索)" and ai_reply not in ["是", "不是", "與故事/題目無關", "不完全是"]:
                    ai_reply = "與故事/題目無關"

                if "🎉 恭喜完全答對！" in ai_reply:
                    if selected_title not in st.session_state.completed_riddles:
                        st.session_state.completed_riddles.append(selected_title)

                with st.chat_message("assistant", avatar="🍊"):
                    st.markdown(ai_reply)
                st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})

                if selected_title in st.session_state.completed_riddles:
                    st.session_state.completed_histories[selected_title] = list(st.session_state.chat_history)

        except Exception as e:
            st.error(f"Gemini 連線錯誤: {e}")
