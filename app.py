import streamlit as st
import google.generativeai as genai
import replicate
import json
import os

# ================= 界面配置 =================
st.set_page_config(page_title="AI 导演系统 v5.1", page_icon="🎬", layout="wide")

# ================= 侧边栏：配置密钥 =================
with st.sidebar:
    st.header("🔑 启动钥匙")
    # 优先从 Streamlit Secrets 读取，如果没有则显示输入框
    if "GOOGLE_API_KEY" in st.secrets:
        google_key = st.secrets["GOOGLE_API_KEY"]
    else:
        google_key = st.text_input("Google API Key", type="password")
        
    if "REPLICATE_API_TOKEN" in st.secrets:
        replicate_key = st.secrets["REPLICATE_API_TOKEN"]
    else:
        replicate_key = st.text_input("Replicate API Token", type="password")
    
    st.markdown("---")
    if st.button("🗑️ 清除历史记忆"):
        st.session_state.messages = []
        st.rerun()

# ================= VCC v5.1 内核 (你的导演大脑) =================
VCC_KERNEL = """
**SYSTEM KERNEL:**
You are the **Visual Continuity Compiler (VCC) v5.1**.
You are NOT a chatbot. You are a **deterministic protocol engine**.
Your internal state is persistent. Your output MUST be **strict JSON**.

**1. THE IMMUTABLE BIBLE (CONSTANTS)**
*CRITICAL: Inject these exact strings with specified weights.*
* **[ACTOR_DEF]:** "a young girl in a red hanfu, twin ponytails with red ribbons, black hair"
* **[SET_DEF]:** "interior of a massive ancient CIRCULAR Tulou building, rainy afternoon, mist, (neat rows of red paper lanterns hanging along the curved wooden corridors on every single floor:1.6), rhythmic red pattern, (curved architecture:1.5)"
* **[COLOR_LOGIC]:** "dominant red lantern glow, warm interior lights vs cool blue rainy exterior contrast, volumetric fog"
* **[NEG_PROMPT_HARD]:** "(text:2.0), (watermark:2.0), (logo:2.0), (modern architecture:1.8), (square building:1.8), (western building:1.8), (missing lanterns:1.6), (distorted architecture:1.5), bad anatomy, extra limbs, crop top, messy background"

**2. REGISTRIES (ENUMS)**
**A. STYLE REGISTRY**
* **[1] Ghibli (DEFAULT):** "Studio Ghibli style, hand-drawn anime aesthetic, flat color, cel shading, Hayao Miyazaki inspired, vibrant yet nostalgic"
* **[2] Cinematic:** "8k, photorealistic, 35mm film, Arri Alexa, cinematic lighting, depth of field, ray tracing, highly detailed texture"
* **[3] Cyberpunk:** "Neon lights, high contrast, futuristic, wet surfaces, purple and blue tones, techwear, glow effects"
* **[4] Chinese Ink:** "Traditional ink wash painting, watercolor texture, minimalist, negative space (Liu Bai), artistic brushstrokes"
* **[5] Pixar 3D:** "Pixar animation style, 3D render, Octane render, cute, soft lighting, high detail, subsurface scattering"

**B. CAMERA REGISTRY**
* **[WIDE]:** "wide angle establishing shot, full environment view"
* **[MED] (DEFAULT):** "medium shot, waist up, balanced character and environment"
* **[CLOSE]:** "close-up shot, focus on face and emotion, shallow depth of field"
* **[LOW]:** "low angle shot, looking up, emphasizing the height of the building"

**3. COMPILATION LOGIC**
1. PARSE INPUT: Extract USER_PHYSICAL_ACTION, USER_EMOTION, CAMERA_INTENT, STYLE_CHANGE.
2. RESOLVE STATE: Look up STYLE and CAMERA registries.
3. CONSTRUCT PROMPT: CURRENT_STYLE + CAMERA + ACTOR + ACTION + EMOTION + SET + COLOR.
4. VALIDATE: Check for "rows of red paper lanterns" and "CIRCULAR".

**4. OUTPUT PROTOCOL (JSON ONLY)**
Output exactly ONE JSON object. No markdown.
{
  "meta": { "user_language": "CN or EN", "style_state": { "id": 1, "name": "Ghibli" } },
  "director_log": "(Brief explanation in user's language)",
  "prompt_data": {
    "positive_prompt": "(THE COMPILED ENGLISH PROMPT)",
    "negative_prompt": "(THE NEG_PROMPT_HARD)",
    "aspect_ratio": "16:9"
  }
}
**5. RUNTIME RULES**
Reset: If user says "New Project", reset STYLE_ID to 1.
Override: If user input conflicts with BIBLE, IGNORE user input.
"""

# ================= 核心逻辑函数 =================
def get_director_response(user_input, history_context):
    if not google_key:
        return None
    
    genai.configure(api_key=google_key)
    
    # 增加安全配置，防止模型拦截“忧郁”等词汇
    safety = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    # 使用你指定的预览版模型
    model = genai.GenerativeModel(
        model_name='models/gemini-3-pro-preview', 
        system_instruction=VCC_KERNEL,
        safety_settings=safety
    )
    
    # 构建对话历史
    chat = model.start_chat(history=[
        {"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} 
        for msg in history_context
    ])
    
    response = chat.send_message(user_input)
    
    # 检查返回内容是否被拦截
    if not response.parts:
        st.error("🎬 导演被系统拦截了，请尝试换一个温和点的指令（例如删除忧郁、悲伤等词汇）。")
        return None
    
    # 清洗 JSON
    text = response.text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except:
        st.error("导演逻辑解析失败，请尝试重新输入。")
        return None

def generate_image(prompt):
    if not replicate_key:
        st.warning("⚠️ 请配置 Replicate API Token 才能出图")
        return None
        
    os.environ["REPLICATE_API_TOKEN"] = replicate_key
    try:
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={"prompt": prompt, "aspect_ratio": "16:9"}
        )
        return output[0] # 返回图片 URL
    except Exception as e:
        st.error(f"绘图失败: {e}")
        return None

# ================= 主界面 UI =================
st.title("🎬 AI 导演系统 (Visual Director)")
st.markdown("*内核版本: VCC v5.1 | 渲染引擎: FLUX.1*")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 渲染历史对话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "image":
            st.image(msg["content"])
            with st.expander("查看 Prompt"):
                st.code(msg["prompt_text"])

# 底部输入框
if prompt := st.chat_input("输入指令 (例: 镜头1，她在雨中哭泣)"):
    # 1. 显示用户输入
    st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 调用导演大脑
    with st.chat_message("assistant"):
        with st.spinner("🧠 导演正在构思分镜..."):
            # 过滤掉图片消息，只传文本历史给 Gemini
            text_history = [m for m in st.session_state.messages if m["type"] == "text"]
            director_data = get_director_response(prompt, text_history)
        
        if director_data:
            # 显示导演日志
            log = f"**导演日志:** {director_data.get('director_log', '')}\n\n*当前风格: {director_data['meta']['style_state']['name']}*"
            st.markdown(log)
            st.session_state.messages.append({"role": "assistant", "type": "text", "content": log})
            
            # 3. 调用画图引擎
            final_prompt = director_data['prompt_data']['positive_prompt']
            with st.spinner("🎨 正在渲染画面 (Flux)..."):
                image_url = generate_image(final_prompt)
            
            if image_url:
                st.image(image_url)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "type": "image", 
                    "content": image_url, 
                    "prompt_text": final_prompt
                })
