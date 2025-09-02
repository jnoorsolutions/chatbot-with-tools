import streamlit as st
from langgraph_tool_backend import chatbot, retrieve_all_threads_list, save_title_to_checkpoint
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid

# =========================== Utilities ===========================
def generate_thread_id():
    return str(uuid.uuid4())   # Har nayi conversation ke liye unique thread ID generate karta hai (UUID)

def reset_chat():
    thread_id = generate_thread_id()   # Naya thread_id banao
    st.session_state["thread_id"] = thread_id   # Session me set karo
    default_title = f"New Chat {len(st.session_state['chat_threads']) + 1}"  # Default title auto-generate
    add_thread(thread_id, default_title)   # Nayi thread ko session aur DB me add karo
    st.session_state["message_history"] = []   # Conversation history reset

def add_thread_old(thread_id):
    if thread_id not in st.session_state["chat_threads"]:   # Agar thread list me nahi hai
        st.session_state["chat_threads"].append(thread_id)  # Purane version: sirf ID append karta hai (title nahi)

def add_thread(thread_id: str, title: str):
    thread_id = str(thread_id)   # Ensure ID string ho

    if thread_id not in st.session_state["chat_threads"]:   # Agar thread list me pehle nahi hai
        clean_title = (title or f"Thread {thread_id[:6]}").strip()   # Title ko clean karo (fallback: "Thread xyz")

        st.session_state["chat_threads"][thread_id] = {   # Dict banata hai har thread ke liye
            "id": thread_id,   
            "title": clean_title
        }
        st.session_state["titles"][thread_id] = {"title": clean_title}   # Titles dict me bhi save karo

        save_title_to_checkpoint(thread_id, clean_title)   # Title ko DB checkpoint me bhi save karo

# Title generator (auto from first user input)
def auto_title_on_first_message(user_input: str):
    thread_id = st.session_state.get("thread_id")   # Current thread_id lo

    # Ensure karo ke titles dict ban chuki ho
    if thread_id not in st.session_state["titles"] or not isinstance(st.session_state["titles"][thread_id], dict):
        st.session_state["titles"][thread_id] = {"title": "New Chat"}

    # Agar title abhi bhi "New Chat" hai to first user message se short title banao
    if st.session_state["titles"][thread_id]["title"].startswith("New Chat"):
        short_title = user_input.strip().split("\n")[0][:30]  # First line ke 30 chars tak title
        st.session_state["titles"][thread_id]["title"] = short_title   # Titles dict update

        if thread_id in st.session_state["chat_threads"]:   # Agar UI threads dict me hai to update karo
            st.session_state["chat_threads"][thread_id]["title"] = short_title

        save_title_to_checkpoint(thread_id, short_title)   # DB me bhi update karo

def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})   # LangGraph se state load karo
    return state.values.get("messages", [])   # Sirf messages return karo


# ======================= Session Initialization ===================
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []   # Har nayi session ke liye empty history

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()   # Default ek thread id banao

if "titles" not in st.session_state:
    st.session_state["titles"] = {}   # Thread titles dict banani zaroori hai

if "current_thread" not in st.session_state:
    st.session_state["current_thread"] = None   # Currently selected thread id

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = {}   # Conversations dict

# DB se purane threads load karke UI me dikhana
for t in retrieve_all_threads_list():   
    add_thread(t["id"], t["title"])   # Har ek ko sidebar me load karo


# ============================ Sidebar ============================
st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")

threads = list(st.session_state["chat_threads"].items())[::-1]
for thread_id, thread in threads:
    if st.sidebar.button(thread["title"], key=f"btn_{thread['id']}"):
        st.session_state["thread_id"] = thread["id"]
        messages = load_conversation(thread["id"])

        temp_messages = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            temp_messages.append({"role": role, "content": msg.content})
        st.session_state["message_history"] = temp_messages


# ============================ Main UI ============================
# Render conversation history
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("Type here")   # Input box

if user_input:
    auto_title_on_first_message(user_input)   # Title auto-generate

    # User ka message history me save karo
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    CONFIG = {   # LangGraph config
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    # Assistant streaming response
    with st.chat_message("assistant"):
        status_holder = {"box": None}   # Tool status ke liye placeholder

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                # Agar tool use ho raha hai to UI update karo
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                # Sirf assistant ke tokens stream karo
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())   # Stream response UI me dikhana

        # Agar tool use hua to finalize karo
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="Tool finished", state="complete", expanded=False
            )

    # Assistant ka final message history me save karo
    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )

# Summary:
# reset_chat → naya conversation start karta hai.
# add_thread → thread ko session aur DB me save karta hai.
# auto_title_on_first_message → first user input se title generate hota hai.
# Sidebar → purane conversations ko list karta hai.
# Main UI → messages render karta hai aur new messages handle karta hai.
