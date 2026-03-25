import streamlit as st
import pdfplumber
import cohere
import os
import json
import pandas as pd

co = cohere.Client(os.getenv("5k2l6NqnbHUuWcsQcSUQW6Xvklw9uFLOqR90hABx"))

# LLM call
def call_llm(prompt):
    response = co.chat(
        model="command-a-03-2025",
        message=prompt
    )
    return response.text

# Extract PDF
def extract_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# Extract structured data
def extract_data(text):
    prompt = f"""
    Extract asset details in JSON:
    asset_id, asset_name, location, current_status, last_maintenance_date, risk_level

    Text:
    {text[:3000]}
    """

    response = call_llm(prompt)
    response = response.replace("```json", "").replace("```", "").strip()

    return json.loads(response)

# UI
st.title("🤖 Asset Chatbot")

uploaded_file = st.file_uploader("Upload Asset PDF", type=["pdf"])

# Store PDF text in session
if uploaded_file:
    st.session_state["pdf_text"] = extract_pdf(uploaded_file)
    st.success("PDF uploaded and processed!")

# Chat history
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

    # Bot response
    if "pdf_text" not in st.session_state:
        bot_reply = "Please upload a PDF first."
    else:
        if "extract" in user_input.lower():
            data = extract_data(st.session_state["pdf_text"])
            bot_reply = data

            # Save Excel
            df = pd.DataFrame([data])
            df.to_excel("output.xlsx", index=False)

            st.download_button("Download Excel", df.to_csv(index=False), "output.csv")
        else:
            # General Q&A
            prompt = f"""
            Answer based on this document:
            {st.session_state["pdf_text"][:3000]}

            Question: {user_input}
            """
            bot_reply = call_llm(prompt)

    st.session_state.messages.append({"role": "assistant", "content": bot_reply})

    with st.chat_message("assistant"):
        st.write(bot_reply)
