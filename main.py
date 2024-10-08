from PyPDF2 import PdfReader
import streamlit as st
import requests
import json
import io
import hashlib

LOGO = "images/clydes-ai.png"
# Set up the API endpoint
API_URL = st.secrets['API_URL'] # Change this to your actual API URL
CORRECT_PASSWORD = st.secrets['CORRECT_PASSWORD']

if not CORRECT_PASSWORD:
    st.error("Please set the APP_PASSWORD environment variable.")
    st.stop()

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()

def login():
    st.session_state.authenticated = True

def logout():
    st.session_state.authenticated = False
    
def calculate_file_hash(file):
    """Calculate a hash for the file content."""
    hasher = hashlib.md5()
    for chunk in iter(lambda: file.read(4096), b""):
        hasher.update(chunk)
    file.seek(0)  # Reset file pointer
    return hasher.hexdigest()

# Login form
if not st.session_state.authenticated:
    st.image(LOGO, use_column_width=True)
    st.title("Login")
    password = st.text_input("Enter password", type="password")
    if st.button("Login"):
        if password == CORRECT_PASSWORD:
            login()
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
else:

  st.title("AI Chat and Document Upload")

  st.sidebar.image(LOGO, use_column_width=True)

  # Sidebar for selecting the section
  section = st.sidebar.radio("Choose a section", ["Live Chat", "Upload Documents"])

  if section == "Live Chat":
      st.header("Live Chat")

      # Initialize chat history
      if "messages" not in st.session_state:
          st.session_state.messages = []

      # Display chat messages
      for message in st.session_state.messages:
          with st.chat_message(message["role"]):
              st.markdown(message["content"])

      # Chat input
      if prompt := st.chat_input("What is your question?"):
          st.session_state.messages.append({"role": "user", "content": prompt})
          with st.chat_message("user"):
              st.markdown(prompt)

          # Prepare the payload for the API
          payload = {
              "indexName": "drclydesai",
              "question": prompt,
              "namespace": "",
              "temperature": 0.3,
              "searchSource": "all",
              "messages": []
          }
          
          print(prompt)

          # Make API request
          with st.spinner("Thinking..."):
              response = requests.post(f"{API_URL}/query", json=payload)
              if response.status_code == 200:
                  answer = response.json()["answer"]
                  st.session_state.messages.append({"role": "assistant", "content": answer})
                  with st.chat_message("assistant"):
                      st.markdown(answer)
              else:
                  st.error("Failed to get a response from the API.")

  elif section == "Upload Documents":
        st.header("Upload Documents")

        # File uploader for multiple files
        uploaded_files = st.file_uploader("Choose text or PDF files", type=["txt", "pdf"], accept_multiple_files=True)

        if uploaded_files:
            # Input fields for index name and namespace
            index_name = "drclydesai"
            namespace = ""

            if st.button("Process Documents"):
                files_to_process = []
                for uploaded_file in uploaded_files:
                    file_hash = calculate_file_hash(uploaded_file)
                    if file_hash not in st.session_state.processed_files:
                        files_to_process.append((uploaded_file, file_hash))
                    else:
                        st.warning(f"File '{uploaded_file.name}' has already been processed. Skipping.")

                for uploaded_file, file_hash in files_to_process:
                    # Read file contents
                    if uploaded_file.type == "text/plain":
                        document_content = uploaded_file.getvalue().decode("utf-8")
                    elif uploaded_file.type == "application/pdf":
                        pdf_reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
                        document_content = ""
                        for page in pdf_reader.pages:
                            document_content += page.extract_text() + "\n"
                    else:
                        st.warning(f"Unsupported file type: {uploaded_file.type}")
                        continue

                    # Prepare the payload for the API
                    payload = {
                        "document": document_content,
                        "indexName": index_name,
                        "namespace": namespace
                    }

                    # Make API request
                    with st.spinner(f"Processing document: {uploaded_file.name}..."):
                        response = requests.post(f"{API_URL}/add_document", json=payload)
                        if response.status_code == 200:
                            st.success(f"Document {uploaded_file.name} processed successfully!")
                            st.session_state.processed_files.add(file_hash)
                        else:
                            st.error(f"Failed to process the document: {uploaded_file.name}")

                # Clear the file uploader
                # st.rerun()

  # Add some information about the app
  st.sidebar.markdown("---")
  st.sidebar.info(
      "This app allows you to chat with an AI assistant and upload documents for processing. "
      "Use the 'Live Chat' section to ask questions, and the 'Upload Documents' section to add new documents to the knowledge base."
  )