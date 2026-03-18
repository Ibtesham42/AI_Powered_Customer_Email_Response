#  AI Customer Support Automation System

An end-to-end AI-powered Customer Support System that automates email handling using **RAG (Retrieval-Augmented Generation) + LLM**, with human-in-the-loop review.

---

##  Features

*  Auto Email Reading (IMAP)
*  AI Response Generation (RAG + LLM)
*  Multi-User Knowledge Base
*  Vector Search using FAISS
*  Human Review & Edit (Admin Panel)
*  Email Sending (SMTP)
*  Chat Interface (Simulated Customer Email Input)
*  Company-wise Data Isolation

---

##  Architecture

```
Customer Email
      ↓
Email Listener (IMAP)
      ↓
RAG Pipeline (FAISS + Embeddings)
      ↓
LLM (Llama 3)
      ↓
AI Draft Reply
      ↓
Queue (Human Review)
      ↓
Admin Edits & Approves
      ↓
Email Sender (SMTP)
```

---

## 📁 Project Structure

```
app/
 ├── email/
 │   ├── email_listener.py
 │   ├── email_responder.py
 │   ├── email_sender.py
 │
 ├── rag/
 |   |---Chunking.py
 │   ├── preprocess.py
 │   ├── rag_pipeline.py
 │   ├── retriever.py
 │   ├── vector_store.py
 │
 ├── llm/
 │   ├── llm_client.py
 │   ├── prompt_builder.py
 │
 ├── queue/
 │   ├── email_queue.py
 │
 ├── utils/
 │   ├── workspace_manager.py

data/
 ├── users/
     ├── companyA/
     ├── DummyData/

scripts/
 ├── build_rag.py
 ├── email_worker.py

streamlit_app/
 ├── email_streamlit_ui.py
 ├── chat_app.py
```

---

##  Setup Instructions

### 1️ Clone Repository

```bash
git clone https://github.com/Ibtesham42/AI_Powered_Customer_Email_Response.git
cd your-project
```

---

### 2️ Create Virtual Environment

```bash
python -m venv venv
```

---

### 3️ Activate Virtual Environment

#### Windows:

```bash
venv\Scripts\activate
```

#### Linux / Mac:

```bash
source venv/bin/activate
```

---

### 4️ Install Requirements

```bash
pip install -r requirements.txt
```

---
## This Steps Are for initial building from root 

##  Data Preparation (RAG Setup)

### Step 1: Add Data

Place your company data inside:

```
data/users/<USER_ID>/raw/
```

Example:

```
data/users/companyA/raw/
```

---

### Step 2: Run Preprocessing

```bash
python -m app.rag.preprocess --user_id companyA
```

---

### Step 3: Build Vector Database

```bash
python scripts/build_rag.py --user_id companyA
```

---

##  Run Email Automation System (Admin Panel)

```bash
 streamlit run email_streamlit_ui.py
```

### Features:

* Fetch incoming emails
* AI generates replies automatically
* Emails added to queue
* Admin can:

  * Review
  * Edit
  * Send response

---

##  Run Chat Interface (Customer Simulation)

```bash
streamlit run chat_app.py

```

### Use Case:

* Simulate customer emails
* Input email manually
* Get AI-generated reply instantly

---

##  Environment Variables (.env)

Create a `.env` file:

```
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
USER_ID=companyA
GROQ_API_KEY="Your_API_KEY"





LLM_PROVIDER=groq



EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
```

---

##  Tech Stack

| Component  | Technology  |
| ---------- | ----------- |
| Backend    | Python      |
| UI         | Streamlit   |
| LLM        | Llama 3     |
| Embeddings | BGE-base-en |
| Vector DB  | FAISS       |
| Email      | IMAP + SMTP |

---

##  Key Highlights

* Multi-tenant architecture (per company RAG)
* Secure data handling (sensitive info masked)
* Human-in-the-loop validation
* Scalable design (can extend to APIs / SaaS)

---

##  Future Improvements

* Real-time email streaming (no manual fetch)
* Background workers (Celery / Redis)
* Analytics dashboard
* Intent classification system
* Auto-learning knowledge base

---

##  Author

**Ibteshm Akhtar**

* Data Science | AI | GenAI
* Built real-world RAG-based automation system

---

##  If you like this project

Give it a on GitHub!
