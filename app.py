# Importing required packages
import hmac
import streamlit as st
import openai
import uuid
import time
import pandas as pd
import io
from openai import OpenAI
from streamlit_cookies_controller import CookieController

# Initialize cookie controller
cookie_controller = CookieController()

# Initialize OpenAI client
client = OpenAI()

# Your chosen model
# MODEL = "gpt-4-1106-preview"

# Initialize session state variables
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "run" not in st.session_state:
    st.session_state.run = {"status": None}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "retry_error" not in st.session_state:
    st.session_state.retry_error = 0


def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the passward is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input("Hasło", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("😕 Niepoprawne hasło")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.


# Set up the page
st.set_page_config(page_title="Natalia GPT", page_icon=":robot_face:")
st.sidebar.title("🤖 Natalia GPT")

st.sidebar.markdown("Twoj osobisty asystent w pisaniu pracy.")
st.sidebar.divider()
st.sidebar.markdown("Masz pytania, lub wszelkiego rodzaju problemy?")
st.sidebar.markdown("Zapytaj swojego asystenta!")
st.sidebar.divider()

# Initialize OpenAI assistant


from openai import OpenAI

openai.api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI()

if "assistant" not in st.session_state:
    st.session_state.assistant = openai.beta.assistants.retrieve(
        st.secrets["assistant_id"]
    )
    if "ThreadID" in cookie_controller.getAll():
        st.session_state.thread = client.beta.threads.retrieve(
            cookie_controller.get("ThreadID")
        )
    else:
        st.session_state.thread = client.beta.threads.create()
        cookie_controller.set("ThreadID", st.session_state.thread.id)


# Display chat messages
st.session_state.messages = client.beta.threads.messages.list(
    thread_id=st.session_state.thread.id
)
for message in reversed(st.session_state.messages.data):
    if message.role in ["user", "assistant"]:
        with st.chat_message(message.role):
            for content_part in message.content:
                message_text = content_part.text.value
                st.markdown(message_text)

# Chat input and message creation with file ID
if prompt := st.chat_input("Jak moge Ci dzisiaj pomóc?"):
    with st.chat_message("user"):
        st.write(prompt)

    message_data = {
        "thread_id": st.session_state.thread.id,
        "role": "user",
        "content": prompt,
    }

    # Include file ID in the request if available
    if "file_id" in st.session_state:
        message_data["file_ids"] = [st.session_state.file_id]

    st.session_state.messages = client.beta.threads.messages.create(**message_data)

    st.session_state.run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread.id,
        assistant_id=st.session_state.assistant.id,
    )
    if st.session_state.retry_error < 3:
        time.sleep(1)
        st.rerun()

# Handle run status
if hasattr(st.session_state.run, "status"):
    if st.session_state.run.status == "running":
        with st.chat_message("assistant"):
            st.write("Myślę...")
        if st.session_state.retry_error < 3:
            time.sleep(1)
            st.rerun()

    elif st.session_state.run.status == "failed":
        st.session_state.retry_error += 1
        with st.chat_message("assistant"):
            if st.session_state.retry_error < 3:
                st.write("Błąd podczas uruchamiania. Spróbuj ponownie za chwile.")
                time.sleep(3)
                st.rerun()
            else:
                st.error("Błąd podczas uruchamiania. Spróbuj ponownie za chwile.")

    elif st.session_state.run.status != "completed":
        st.session_state.run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread.id,
            run_id=st.session_state.run.id,
        )
        if st.session_state.retry_error < 3:
            time.sleep(3)
            st.rerun()
