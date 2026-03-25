import streamlit as st
import pdfplumber
import cohere
import json
import pandas as pd
import re

# API
co = cohere.Client(st.secrets["COHERE_API_KEY"])

# 🔹 LLM call
def call_llm(prompt):
    response = co.chat(
        model="command-a-03-2025",
        message=prompt
    )
    return response.text


# 🔹 Extract PDF
def extract_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


# 🔹 Extract structured data (FIXED)
def extract_data(text):
    prompt = f"""
    Extract asset details in STRICT JSON only.

    Do NOT add explanation.
    Do NOT add text before or after.

    Format:
    {{
      "asset_id": "...",
      "asset_name": "...",
      "location": "...",
      "current_status": "...",
      "last_maintenance_date": "...",
      "risk_level": "..."
    }}

    If any field missing → "NOT FOUND"

    Text:
    {text[:3000]}
    """

    response = call_llm(prompt)

    # 🔧 Clean markdown
    response = response.replace("```json", "").replace("```", "").strip()

    # 🔧 Extract JSON safely
    match = re.search(r"\{.*\}", response, re.DOTALL)

    if not match:
        st.error("❌ Could not extract JSON")
        st.write(response)
        return None

    json_str = match.group()

    try:
        return json.loads(json_str)
    except Exception as e:
        st.error("❌ JSON parsing failed")
        st.write(json_str)
        return None


# ================= UI =================

st.title("🤖 Asset Chatbot")

uploaded_file = st.file_uploader("Upload Asset PDF", type=["pdf"])

# Store PDF text
if uploaded_file:
    st.session_state["pdf_text"] = extract_pdf(uploaded_file)
    st.success("✅ PDF uploaded and processed!")

# Chat memory
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
user_input = st.chat_input("Ask something about the document...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    # 🔹 Bot logic
    if "pdf_text" not in st.session_state:
        bot_reply = "⚠️ Please upload a PDF first."

    else:
        # 👉 Extraction mode
        if "extract" in user_input.lower():
            data = extract_data(st.session_state["pdf_text"])

            if data:
                bot_reply = data

                df = pd.DataFrame([data])
                df.to_excel("output.xlsx", index=False)

                st.download_button(
                    "📥 Download Excel",
                    df.to_csv(index=False),
                    "output.csv"
                )
            else:
                bot_reply = "❌ Extraction failed. Please try again."

        # 👉 Q&A mode
        else:
            prompt = f"""
            Answer based on this document:

            {st.session_state["pdf_text"][:3000]}

            Question: {user_input}
            """

            bot_reply = call_llm(prompt)

    # Save response
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})

    with st.chat_message("assistant"):
        st.write(bot_reply)
