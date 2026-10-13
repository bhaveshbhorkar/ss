import os

import requests
import streamlit as st

# Ye teeno values hosting platform ke Secrets mein rakhein, code mein kabhi nahi.
HOST = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
TOKEN = os.environ.get("DATABRICKS_TOKEN", "")
ENDPOINT = os.environ.get("SERVING_ENDPOINT", "")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")  # optional, par recommended
MAX_QUESTIONS = 20  # ek browser session mein kitne sawal

st.title("Ask the Assistant")

if not (HOST and TOKEN and ENDPOINT):
    st.error("DATABRICKS_HOST, DATABRICKS_TOKEN aur SERVING_ENDPOINT secrets set karein.")
    st.stop()

if not HOST.startswith("http"):
    HOST = "https://" + HOST
URL = f"{HOST}/serving-endpoints/{ENDPOINT}/invocations"

# ---- simple password gate ----
if APP_PASSWORD and not st.session_state.get("authed"):
    pwd = st.text_input("Password", type="password")
    if pwd:
        if pwd == APP_PASSWORD:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Galat password")
    st.stop()


def ask_agent(messages):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    # sirf aakhri 10 messages bhejein taaki request chhoti rahe
    r = requests.post(
        URL, headers=headers, json={"input": messages[-10:]}, timeout=300
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    data = r.json()

    texts = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    texts.append(c.get("text", ""))
    if texts:
        return texts[-1]

    if "choices" in data:
        return data["choices"][0]["message"]["content"]

    return str(data)


if "messages" not in st.session_state:
    st.session_state.messages = []
if "count" not in st.session_state:
    st.session_state.count = 0

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask your question"):
    if st.session_state.count >= MAX_QUESTIONS:
        st.warning("Is session ke sawal ki limit poori ho gayi. Page refresh karein.")
        st.stop()
    st.session_state.count += 1

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = ask_agent(st.session_state.messages)
            except Exception as e:
                answer = f"Sorry, something went wrong: {e}"
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
