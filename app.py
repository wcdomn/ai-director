import streamlit as st
import google.generativeai as genai
import replicate
import json
import os

# ================= 页面配置 =================
st.set_page_config(
    page_title="AI 导演系统 v5.1",
    page_icon="🎬",
    layout="wide"
)

# ================= 侧边栏 =================
with st.sidebar:
    st.header("🔑 启动钥匙")

    google_key = st.secrets.get("GOOGLE_API_KEY") or st.text_input(
        "Google API Key", type="password"
    )
    replicate_key = st.secrets.get("REPLICATE_API_TOKEN") or st.text_input(
        "Replicate API Token", type="password"
    )

    st.markdown("---")
    if st.button("🗑️ 清除历史记忆"):
        st.session_state.messages = []
        st.rerun()

# ================= VCC 内核 =================
VCC_KERNEL = """
You are the Visual Continuity Compiler (VCC) v5.1.
You are NOT a chatbot.
You output STRICT JSON ONLY.

IMMUTABLE CONSTANTS:
ACTOR: a young girl in a red hanfu, twin ponytails with red ribbons, black hair
SET: interior of a massive ancient CIRCULAR Tulou building, rainy afternoon, mist,
     neat rows of red paper lanterns hanging along the curved wooden corridors
COLOR: dominant red lantern glow, warm interior lights vs cool blue rainy exterior
NEGATIVE: (text:2.0), (watermark:2.0), (logo:2.0), bad anatomy, extra limbs

STYLE DEFAULT: Ghibli
CAMERA DEFAULT: medium shot

OUTPUT FORMAT:
{
  "meta": {
    "user_language": "CN or EN",
    "style_state": { "id": 1, "name": "Ghibli" }
  },
  "director_log": "string",
  "prompt_data": {
    "positive_prompt": "string",
    "negative_prompt": "string",
    "aspect_ratio": "16:9"
  }
}
"""

# ================= 导演大脑 =================
def get_director_response(user_input, history):
    if not google_key:
        st.error("❌ 缺少 Google API Key")
        return None

    genai.configure(api_key=google_key)

    model = genai.GenerativeModel(
        model_name="models/gemini-3-pro-preview",
        system_instruction=VCC_KERNEL
    )

    chat = model.start_chat(history=[
        {
            "role": "user" if m["role"] == "user" else "model",
            "parts": [m["content"]]
        }
        for m in history
    ])

    response = chat.send_message(user_input)

    if not response.text:
        st.error("❌ Gemini 无返回内容")
        return None

    try:
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        st.error("❌ JSON 解析失败")
        st.code(response.text)
        return None

# ================= 图像生成（已修复） =================
def generate_image(positive_prompt, negative_prompt):
    if not replicate_key:
        st.error("❌ 缺少 Replicate API Token")
        return None

    os.environ["REPLICATE_API_TOKEN"] = replicate_key

    try:
        output = replicate.run(
            "black-forest-labs/flux-1.1",
            input={
                "prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "aspect_ratio": "16:9",
                "num_outputs": 1
            }
        )

        # ⚠️ Replicate 返回的是 iterator
        for img in output:
            return img

    except Exception as e:
        st.error(f"❌ 绘图失败: {e}")
        return None

# ================= 主界面 =================
st.title("🎬 AI 导演系统 (Visual Director)")
st.markdown("*内核版本: VCC v5.1 ｜ 渲染引擎: FLUX 1.1*")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 历史渲染
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "image":
            st.image(msg["content"])
            with st.expander("查看 Prompt"):
                st.code(msg["prompt_text"])

# ================= 输入区 =================
if user_input := st.chat_input("输入指令（例：镜头1，她站在雨中的土楼）"):
    # 用户消息
    st.session_state.messages.append({
        "role": "user",
        "type": "text",
        "content": user_input
    })

    with st.chat_message("assistant"):
        with st.spinner("🧠 导演正在构思分镜..."):
            text_history = [m for m in st.session_state.messages if m["type"] == "text"]
            director = get_director_response(user_input, text_history)

        if director:
            log = f"**导演日志：** {director['director_log']}\n\n" \
                  f"*风格：{director['meta']['style_state']['name']}*"
            st.markdown(log)

            st.session_state.messages.append({
                "role": "assistant",
                "type": "text",
                "content": log
            })

            pos = director["prompt_data"]["positive_prompt"]
            neg = director["prompt_data"]["negative_prompt"]

            with st.spinner("🎨 正在渲染画面..."):
                img_url = generate_image(pos, neg)

            if img_url:
                st.image(img_url)
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "image",
                    "content": img_url,
                    "prompt_text": pos
                })
