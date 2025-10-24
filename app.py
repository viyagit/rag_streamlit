import streamlit as st
from backend.azure_client import chat_with_azure, RATE_LIMIT_MESSAGE  # Assuming this is correctly implemented
from backend.visualizer import generate_visualization
import matplotlib.pyplot as plt
from backend.rag import rag_context
from backend.path_resolver import resource_path
from backend.ocr import run_rag_pipeline
import altair as alt
import tempfile
import os
from backend.logger import logger
from backend.get_ip import get_client_ip
import datetime
# timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
# user_ip = get_client_ip()
# logger.info(
#             "IP_LOG | USER_IP : {} : {}",user_ip, timestamp
#         )
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.3
if "max_tokens" not in st.session_state:
    st.session_state.max_tokens = 400
if "k" not in st.session_state:
    st.session_state.k = 2
def main():
    st.set_page_config(
    page_title="HR Navigator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    
)


    # --- SIMPLIFIED SIDEBAR ---
    with st.sidebar:      
        # 1. Upload Files
        st.header("Model Settings")
        st.session_state.temperature = st.slider(
        "Temperature", 0.0, 1.0, st.session_state.temperature, key="temperature_slider"
        )
        st.session_state.max_tokens = st.slider(
        "Max Tokens", 10, 1000, st.session_state.max_tokens, key="max_tokens_slider"
        )
        st.session_state.k = st.slider("Number of matches per document", 1, 10, st.session_state.k,key="k_slider")
        st.subheader("**1. Upload Files**")
        uploaded_files = st.file_uploader(
            "Choose documents (PDF) to process:", 
            type=["pdf"], 
            accept_multiple_files=True, 
            key="new_rag_files",
            label_visibility="collapsed"  # Hide the default label for a cleaner look
        )
        # 2. Generate Embeddings (Conditional based on files)
        st.subheader("**2. Load Files**")
        if st.button("Load", key="generate", use_container_width=True):
            if uploaded_files: # Assuming uploaded_files is st.file_uploader result
                st.info(f"Generating and saving embeddings for {len(uploaded_files)} file(s)...")
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Save each uploaded file to the temporary directory
                    for uploaded_file in uploaded_files:
                        file_path = os.path.join(temp_dir, uploaded_file.name)
                        # Write the content of the in-memory file to a disk file
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())   
                        # Now, call the original function with the path to the temporary directory
                    try:
                            # 1. GENERATE the new embeddings and get the unique path
                        with st.spinner("Generating Embeddings..."):                        
                            latest_embedding= run_rag_pipeline(temp_dir)
                            st.success(f"New embeddings loaded successfully")
                    except Exception as e:
                            st.error(f"Failed to generate and load NEW embeddings: {e}")

            else:
                st.warning("Please upload files first.")
        vector_db_path = resource_path('dependencies/vector_db')        
        options = [name for name in os.listdir(vector_db_path) if os.path.isdir(os.path.join(vector_db_path, name))]
        vb_selection = st.pills("List of DataBases", options, default=options,selection_mode="multi")
        

    # --- Main chat interface ---
    st.markdown("<h1 style='text-align:center;'>🤖 LTS CHATBOT</h1>", unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": "You are a assistant for Bosch, You will give clear concise and responses in tabular format with comparisons/analysis from previous years data."}
        ]

    # Chat display container with fixed height and vertical scroll
    chat_container = st.container()
    with chat_container:
        st.markdown(
    """
    <style>
        :root {
            --user-bg-light: #2e8b57;
            --user-bg-dark: #3cb371;
            --user-text: #ffffff;

            --assistant-bg-light: #444c56;
            --assistant-bg-dark: #5a5f69;
            --assistant-text: #f0f0f0;
        }

        @media (prefers-color-scheme: dark) {
            .user-msg {
                background-color: var(--user-bg-dark);
                color: var(--user-text);
            }
            .assistant-msg {
                background-color: var(--assistant-bg-dark);
                color: var(--assistant-text);
            }
        }

        @media (prefers-color-scheme: light) {
            .user-msg {
                background-color: var(--user-bg-light);
                color: var(--user-text);
            }
            .assistant-msg {
                background-color: var(--assistant-bg-light);
                color: var(--assistant-text);
            }
        }

        .user-msg, .assistant-msg {
            padding: 8px 12px;
            border-radius: 15px;
            margin-bottom: 8px;
            max-width: 70%;
            text-align: left;
            transition: background-color 0.3s ease;
        }

        .user-msg:hover {
            background-color: #4caf50; /* hover green */
        }

        .assistant-msg:hover {
            background-color: #5f6a78; /* hover gray */
        }
    </style>
    """,
    unsafe_allow_html=True
)

        # Display chat history
        for msg in st.session_state.messages:
            if msg["role"] == "system":
                continue
            elif msg["role"] == "user":
                st.markdown(f"<div class='user-msg'><strong>User:</strong> {msg['content']}</div>", unsafe_allow_html=True)
            elif msg["role"] == "assistant":
                st.markdown(f"<div class='assistant-msg'><strong>Assistant:</strong> {msg['content']}</div>", unsafe_allow_html=True)
                # Display visualization if present in the message state
                if "figure" in msg and msg["figure"] is not None:
                    # NOTE: st.pyplot() or st.altair_chart() must be called outside the markdown logic
                    viz_object = msg["figure"]
                    
                    # Check the type of the visualization object
                    if isinstance(viz_object, plt.Figure):
                        st.pyplot(viz_object)
                    try:
                        # This will work if viz_object is an Altair chart, or other compatible object
                        st.altair_chart(viz_object, use_container_width=True)
                    except Exception as e:
                        # Fallback to matplotlib if altair_chart fails (e.g., if it was a Matplotlib figure)
                        # We should only get here if the object isn't an Altair chart
                        st.pyplot(viz_object)

    # Layout inputs side by side


    chat_col, button_col = st.columns([5, 1])
    with chat_col:
        user_input = st.chat_input("Type your message and press Enter...")

    with button_col:
        visualization = st.button("Visualize", use_container_width=True, key="visual_button")            
            # --- START OF REVISED VISUALIZATION LOGIC ---
        if visualization:
                latest_assistant_response_index = None
                # Find the index of the latest assistant message
                for i in reversed(range(len(st.session_state.messages))):
                    if st.session_state.messages[i]["role"] == "assistant":
                        latest_assistant_response_index = i
                        break

                if latest_assistant_response_index is not None:
                    latest_response = st.session_state.messages[latest_assistant_response_index]["content"]
                    
                    with st.spinner("Generating visualization..."):
                        fig = generate_visualization(latest_response)

                    if fig:
                        # Save figure in session_state for persistent display
                        # This is what the chat loop reads to display the plot inline
                        st.session_state.messages[latest_assistant_response_index]["figure"] = fig
                        
                        # Rerun the script to display the updated chat history
                        st.rerun() 
                    else:
                        st.warning("Failed to generate visualization. The assistant's response may not  visualize data.")
                else:
                    st.warning("No assistant response available to visualize yet.")
            # --- END OF REVISED VISUALIZATION LOGIC ---
    if user_input:
                    if not user_input.strip():
                        st.warning("Please enter a message.")
                    else:
                        original_user_msg = user_input.strip()

                        try:
                                rag_context_str = rag_context(original_user_msg,vb_selection,st.session_state.k)
                                full_query = f"{rag_context_str}\n\n{original_user_msg}"
                        except Exception as e:
                                st.error(f"Error generating RAG context: {e}")
                                full_query = original_user_msg
                        # Append user message (original message)
                        st.session_state.messages.append({"role": "user", "content": original_user_msg})

                        with st.spinner("Calling Azure OpenAI..."):
                            try:
                                chat_history = [msg for msg in st.session_state.messages if msg["role"] != "system"]
                                api_messages = [st.session_state.messages[0]] + chat_history[:-1] + [{"role": "user", "content": full_query}]

                                response = chat_with_azure(api_messages, st.session_state.temperature, st.session_state.max_tokens)

                                if response == RATE_LIMIT_MESSAGE:
                                    st.error(RATE_LIMIT_MESSAGE)
                                    # Remove the last user message since we failed to get a response
                                    st.session_state.messages.pop()
                                else:
                                    st.session_state.messages.append({"role": "assistant", "content": response})

                                st.rerun()
                            except Exception as e:
                                # Catch TimeoutError, HTTPError, ConnectionError, etc. from the queue
                                st.error(f"Error calling Azure OpenAI: {e}")
                                # Remove the last user message since we failed to get a response
                                st.session_state.messages.pop() 


if __name__ == "__main__":
    main()