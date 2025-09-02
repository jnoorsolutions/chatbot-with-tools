#from langgraph.graph import StateGraph, START, END
from langgraph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from dotenv import load_dotenv
import sqlite3
import requests
import time
import uuid

load_dotenv()

# -------------------
# 1. LLM
# -------------------
llm = ChatGroq(model='llama-3.3-70b-versatile')
#llm = ChatOpenAI()

# -------------------
# 2. Tools
# -------------------
# Tools
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)
    return r.json()


tools = [search_tool, get_stock_price, calculator]          # tools ki list banai jo AI agent use karega (search, stock price aur calculator)
llm_with_tools = llm.bind_tools(tools)                      # LLM ko in tools ke sath bind kar rahe hain taake LLM in tools ko call kar sake

# -------------------
# 3. State
# -------------------
class ChatState(TypedDict):                                 # ChatState aik TypedDict hai jo conversation state hold karega
    messages: Annotated[list[BaseMessage], add_messages]    # messages ka list jo conversation history rakhta hai, add_messages decorator lagaya gaya
    title: str                                              # thread ka title save karne ke liye field

# -------------------
# 4. Nodes
# -------------------
def chat_node(state: ChatState):                            # aik function jo LLM node define karta hai
    """LLM node that may answer or request a tool call."""  # docstring: LLM jawab bhi de sakta hai aur tool request bhi kar sakta hai
    messages = state["messages"]                            # state se messages extract kar liye
    response = llm_with_tools.invoke(messages)              # LLM ko tools ke sath call kar rahe hain
    return {"messages": [response]}                         # LLM ka jawab wapis kar rahe hain ek dict ke form me

tool_node = ToolNode(tools)                                 # tool node banaya jo tools ko manage karega

# -------------------
# 5. Checkpointer
# -------------------
conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)   # sqlite database connection banaya (chatbot.db)
checkpointer = SqliteSaver(conn=conn)                                    # SqliteSaver use karke checkpoints database me save karne ke liye object banaya

# -------------------
# 6. Graph
# -------------------
graph = StateGraph(ChatState)                               # StateGraph banaya jo ChatState ko manage karega
graph.add_node("chat_node", chat_node)                      # graph me aik node add kiya (chat_node)
graph.add_node("tools", tool_node)                          # graph me aik node add kiya (tools)

graph.add_edge(START, "chat_node")                          # START se chat_node tak edge banaya (conversation start hota hai)

graph.add_conditional_edges("chat_node", tools_condition)   # chat_node ke baad agar condition match ho to tools call hoga
graph.add_edge('tools', 'chat_node')                        # tools ke complete hone ke baad wapas chat_node me aayega

chatbot = graph.compile(checkpointer=checkpointer)          # graph ko compile kiya aur checkpointer attach kiya (db me save hoga)

# -------------------
# 7. Helper
# -------------------
def retrieve_all_threads_set():                                          # helper function threads ko set form me retrieve karta hai
    all_threads = set()                                                  # ek khali set banaya
    for checkpoint in checkpointer.list(None):                           # checkpointer se saare checkpoints iterate kiye
        all_threads.add(checkpoint.config["configurable"]["thread_id"])  # thread_id ko set me add kiya
    return list(all_threads)                                             # set ko list bana kar return kiya

def retrieve_all_threads_list():                        # threads ko list ke form me retrieve karne wala helper
    all_threads = []                                    # khali list banayi
    for cp in checkpointer.list(None):                  # checkpoints iterate kiye
                                                        # cp ek CheckpointTuple hai => fields: config, checkpoint, metadata, versions
        cfg = cp.config                                 # config extract kiya
        tid = cfg["configurable"]["thread_id"]          # thread_id nikala config se

        cp_payload = cp.checkpoint or {}                # checkpoint data liya
        data = cp_payload.get("data", {}) or {}         # usme se data nikala
        title = data.get("title", f"Thread {tid[:6]}")  # agar title nahi mila to default title banaya

        all_threads.append({"id": tid, "title": title})   # list me dict append kiya jisme id aur title hai
    
    return all_threads                                    # saari threads list return ki

def retrieve_all_threads_dict():                              # threads ko dict form me retrieve karne wala helper
    all_threads = {}                                          # khali dict banaya
    for checkpoint in checkpointer.list(None):                # saare checkpoints iterate kiye
        tid = checkpoint.config["configurable"]["thread_id"]  # thread_id nikala
        data = checkpoint.checkpoint.get("data", {})          # checkpoint ka data nikala
        title = data.get("title", f"Thread {tid[:6]}")        # agar title missing ho to default title banaya
        all_threads[tid] = title                              # dict me mapping banayi {thread_id: title}
    return all_threads                                        # dict return kiya

def save_title_to_checkpoint(thread_id: str, title: str):    # thread ka title db (checkpoint) me save karne ka helper
    cfg = {                                                  # config banaya jisme thread_id aur namespace rakha
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "default"
        }
    }

    cp = checkpointer.get(cfg)                       # checkpointer se purana checkpoint nikalne ki koshish ki

    if cp is None:                                   # agar pehli dafa save kar rahe ho
        checkpoint = {                               # naya checkpoint banaya
            "id": thread_id,       
            "ts": time.time(),
            "data": {"title": title}
        }
    else:                                                               # agar pehle se checkpoint exist karta hai
        cp_payload = cp.get("checkpoint", {}) or {}                     # purana checkpoint payload nikala
        existing_data = cp.get("checkpoint", {}).get("data", {}) or {}  # purane data me se "data" nikala
        existing_data["title"] = title                                  # title update kiya

        checkpoint = {                                                  # updated checkpoint banaya
            "id": cp_payload.get("id", thread_id),   
            "ts": time.time(),
            "data": existing_data
        }

    checkpointer.put(               # updated ya naya checkpoint db me save kiya
        config=cfg,
        checkpoint=checkpoint,
        metadata={},
        new_versions={}
    )

print("Threads in DB:", retrieve_all_threads_list())
