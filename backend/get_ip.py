import streamlit as st
import datetime
import logging

# Configure logging (to a file or console)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_client_ip():
    """Retrieves the connecting IP address using Streamlit's context."""
    
    # 1. Use the official Streamlit context (most direct method)
    ip_address = None
    try:
        # st.context.ip_address should work in v1.50.0
        ip_address = st.context.ip_address
        
    except AttributeError:
        # Fallback for older versions or unusual environments (less likely with 1.50.0)
        logging.warning("st.context.ip_address not found. IP address cannot be retrieved.")
        return "Unknown - Context Error"

    # 2. Check for localhost/None case
    if ip_address is None or ip_address == '127.0.0.1':
        # This is expected when connecting via localhost or 127.0.0.1
        # To get the Network IP, the user must connect via the actual Network IP (e.g., 192.168.1.5:8501)
        return "Localhost/Loopback (None or 127.0.0.1)"
    
    return ip_address

# --- Streamlit Application Start ---


# ⚡ Call the function
user_ip = get_client_ip()
