import os
import datetime
import re
from pdf2image import convert_from_path
import pytesseract
from tqdm import tqdm
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
import tempfile
# Assuming resource_path is defined elsewhere, keeping the structure
# from backend.path_resolver import resource_path 

# Fallback for resource_path if not provided, assuming it's available in the real environment
try:
    from backend.path_resolver import resource_path
except ImportError:
    # Placeholder function for resource resolution if missing
    def resource_path(relative_path):
        return relative_path

# --- CONFIGURATION ---
# IMPORTANT: For this to work, you must have Tesseract and Poppler installed and configured.
POPPLER_BIN_PATH = resource_path('dependencies/poppler-25.07.0/Library/bin')
pytesseract.pytesseract.tesseract_cmd = resource_path('dependencies/Tesseract-OCR/tesseract.exe')


# --- PART 1: OCR PROCESSING (Now processes a single file) ---
def process_single_pdf_to_text(pdf_path: str, text_output_directory: str) -> str:
    """
    Converts a single PDF file to a text file using OCR.

    Args:
        pdf_path (str): The path to the single PDF file.
        text_output_directory (str): The path where the extracted .txt file will be saved.
        
    Returns:
        str: The full path to the generated .txt file.
    """
    filename = os.path.basename(pdf_path)
    print(f"Starting OCR process for: {filename}")

    try:
        # Convert PDF to a list of PIL images
        # poppler_path is passed to ensure compatibility with Windows environments
        pil_pages = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_BIN_PATH)

        all_text = []
        # Process each page with OCR
        for i, page_image in enumerate(tqdm(pil_pages, desc=f"OCR for {filename}")):
            # Tesseract config for best results on a variety of documents
            text = pytesseract.image_to_string(page_image, config='--oem 3 --psm 3')
            all_text.append(f"\n\n--- Source File: {filename} | Page {i+1} ---\n\n")
            all_text.append(text)

        # Save the extracted text to a .txt file
        txt_filename = os.path.splitext(filename)[0] + ".txt"
        txt_filepath = os.path.join(text_output_directory, txt_filename)
        with open(txt_filepath, "w", encoding="utf-8") as f:
            f.write("".join(all_text))
        print(f"Successfully saved extracted text to {txt_filepath}")
        return txt_filepath

    except Exception as e:
        print(f"Error processing {filename}: {e}")
        # Re-raise the error so the main process can catch it
        raise e

# --- PART 2: EMBEDDING GENERATION ---
def generate_embeddings(text_content_directory: str, vector_db_name: str) -> str:
    BASE_VECTOR_DB_PATH = resource_path("dependencies/vector_db")
    """
    Loads text documents (expected to be a single file), splits them, 
    generates embeddings, and persists the vector store under the given name.

    Args:
        text_content_directory (str): The path to the temporary directory 
                                      containing the single .txt file.
        vector_db_name (str): The desired name for the persistence directory.

    Returns:
        str: The path to the persisted Chroma vector store directory.
    """
    print("Starting embedding generation...")
    # 1. Load documents
    loader = DirectoryLoader(
        text_content_directory,
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    data = loader.load()
    if not data:
        raise ValueError("No text documents were loaded. Check the input directory and file types.")

    # 2. Split documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=500)
    docs = text_splitter.split_documents(data)

    # 3. Initialize Embeddings Model
    model_path =resource_path('dependencies/embeddinggemma-300m')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Embedding model not found at '{model_path}'. Please ensure the model is in the correct directory.")
    embedding_function = SentenceTransformerEmbeddings(model_name=model_path)

    # 4. Define persistence directory using the generated name (unique per file)
    # Sanitizing again just in case, though it should be clean from the caller
    safe_db_name = re.sub(r'[^\w\-]', '_', vector_db_name)
    persist_directory = os.path.join(BASE_VECTOR_DB_PATH, safe_db_name) 
    
    # 5. Create and persist the vector store
    print(f"Creating vector store in '{persist_directory}'...")
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embedding_function,
        persist_directory=persist_directory
    )
    vectorstore.persist()
    print("Vector store persisted successfully.")

    return persist_directory

# --- MAIN PIPELINE FUNCTION (Iterates over files) ---
def run_rag_pipeline(pdf_input_dir: str) -> list[str]:
    """
    Orchestrates the entire RAG data generation pipeline from PDF to vector store,
    creating a separate vector store for each PDF file found in the input directory.

    Args:
        pdf_input_dir (str): The directory containing the uploaded PDF files.

    Returns:
        list[str]: A list of paths to the newly created and persisted vector stores.
    """
    # 1. Identify all PDF files
    pdf_files = [os.path.join(pdf_input_dir, f) 
                 for f in os.listdir(pdf_input_dir) 
                 if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        raise ValueError("No PDF files found in the input directory.")

    all_vector_store_paths = []

    # 2. Loop through each PDF file
    for pdf_path in pdf_files:
        filename_base = os.path.splitext(os.path.basename(pdf_path))[0]
        # Create a clean, unique name for the vector DB based on the file name
        vector_db_name = re.sub(r'[^\w\-]', '_', filename_base)
        
        print(f"\n--- Starting RAG pipeline for file: {os.path.basename(pdf_path)} ---")
        
        # Create a temporary directory for the intermediate text file for this specific PDF
        with tempfile.TemporaryDirectory() as text_output_dir:
            try:
                # Step 1: Convert single PDF to a single text file
                process_single_pdf_to_text(pdf_path, text_output_dir)

                # Step 2: Generate embeddings from the single text file, using the derived name
                vector_store_path = generate_embeddings(text_output_dir, vector_db_name)
                all_vector_store_paths.append(vector_store_path)
            except Exception as e:
                # Log the error and skip this file, continuing with the rest
                print(f"Failed to process and embed {os.path.basename(pdf_path)}: {e}")
                continue 

    if not all_vector_store_paths:
        raise Exception("Failed to generate vector stores for any uploaded file.")
        
    return all_vector_store_paths
