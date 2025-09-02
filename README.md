# LangGraph Chatbot with Tools

A conversational AI chatbot built using **LangGraph**, **LangChain**, and **Streamlit**.  
This project demonstrates:

- Real-time tool usage  
- Persistent conversation storage with thread IDs  
- Dynamic chat title generation from the first user input  

## 🚀 Features

### 🛠️ Integrated Tools
1. **Math Tool**  
   Perform basic arithmetic operations:  
   - Addition  
   - Subtraction  
   - Multiplication  
   - Division  

2. **Stock Price Fetcher**  
   Fetch the **latest stock price** for a given symbol (e.g., `AAPL`, `TSLA`)  
   using **Alpha Vantage API** (API key provided via URL).  

### 💾 Persistent Conversations
- Every chat session is saved with a unique `thread_id`.  
- Conversation history is restored after refresh.  
- Titles are automatically generated based on the first user message.  

### 🖥️ Streamlit Frontend
- Sidebar with **New Chat** button and list of saved conversations.  
- Chat history rendered in **chat-style messages**.  
- Real-time assistant streaming response with tool status indicators.

🧪 Application Url
https://chatbot-with-tools-rbb2lrpkoorvjagxsjlojp.streamlit.app/

## 📂 Project Structure

    project/
    │── streamlit_frontend_tool.py   # Streamlit UI and chat logic
    │── langgraph_tool_backend.py    # LangGraph backend + checkpoint storage
    │── requirements.txt             # Python dependencies
    │── README.md                    # Project documentation
    │── .gitignore                   # git ingnore
    

------------------------------------------------------------------------

## ⚙️ Installation

1.  **Clone the repository**

    ``` bash
    git clone https://github.com/jnoorsolutions/chatbot-with-tools.git
    cd langgraph-chatbot
    ```

2.  **Create a virtual environment**

    ``` bash
    python -m venv venv
    source venv/bin/activate   # Linux/Mac
    venv\Scripts\activate    # Windows
    ```

3.  **Install dependencies**

    ``` bash
    pip install -r requirements.txt
    ```

------------------------------------------------------------------------

## ▶️ Usage

Run the Streamlit application:

``` bash
streamlit run streamlit_frontend_tool.py
```

Then open your browser at **http://localhost:8501**.

-   Start a new chat using the **New Chat** button.\
-   The first user input generates a **title** automatically.\
-   Switch between saved conversations using the **sidebar**.\
-   Tool usage and assistant replies are streamed live.

------------------------------------------------------------------------

## 🛠️ Tech Stack

-   **LangGraph** -- stateful AI workflows\
-   **LangChain** -- language model integration\
-   **Streamlit** -- frontend UI\
-   **SQLite** -- checkpoint persistence

------------------------------------------------------------------------

## 📌 Notes

-   Each conversation is uniquely identified by `thread_id`.\
-   Chat titles update dynamically on the **first message**.\
-   Backend can be extended with additional **tools** or **memory
    modules**.

------------------------------------------------------------------------

## 📜 License

Released under the **MIT License**.\
You are free to use, modify, and distribute this project.

---

## 👨‍💻 Author  
Developed by **Junaid Noor Siddiqui** ✨  
