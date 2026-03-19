
Step -1

### 1️ Clone Repository


git clone https://github.com/Ibtesham42/AI_Powered_Customer_Email_Response.git
cd your-project

cloning done 
Step-2

### 2️ Create Virtual Environment


python -m venv venv



Step-3

### 3️ Activate Virtual Environment

#### Windows:

```bash
venv\Scripts\activate
```
step -3
#### Linux / Mac:

```bash
source venv/bin/activate
```

step -4

### 4️ Install Requirements

```bash
pip install -r requirements.txt

You have to install cuda torch after installing requirements
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124


mean while  we wil go to step 5
step - 5 
 
create data FOLDER
inside data folder create user FOLDER
paste company data folder here

This above process only for data which has been already fead to  RAG Architecture 
and vector db is created document.json ,indexing also

Requirement file stil downloading so we have to wait some time wait some more time
done nae 6

Step -6
for chat input output  run below command
streamlit run chat_app.py

for recive email automated generation just human interaction needed to review edit and send

streamlit run email_streamlit_ui.py

ERROR SOLVe
pip install -r requirements.txt

You have to install cuda torch after installing  pip  requirements.txt

it might take 15 minutes to half hour, depending upon internet mine i have already install in my own new environment

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

so its running.
we will input email as customer and output as company email 
naw we will move to email streamlit


Here email is connected 
automaticaly it wil read email and generate
new email according to email and company knwledge base 
That all Thank u