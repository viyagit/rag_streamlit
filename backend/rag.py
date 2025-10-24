import os
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
# Assuming backend.path_resolver is available for resource_path
from backend.path_resolver import resource_path 

# --- Configuration and Initialization ---
# Define the root path where all vector store directories are located
VECTOR_DB_ROOT = resource_path("dependencies/vector_db")

# Path to your local Sentence Transformer model
MODEL_PATH = resource_path("dependencies/embeddinggemma-300m") 

# Initialize the embedding model once using SentenceTransformerEmbeddings
embedding_model = SentenceTransformerEmbeddings(model_name=MODEL_PATH)


def init_chroma(persist_dir: str) -> Chroma:
    """Initializes a Chroma vector store from a persistent directory."""
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_model
    )

def init_selected_vector_stores(vb_selection: List[str]) -> List[Tuple[str, Chroma]]:
    """
    Initializes Chroma instances only for the directory names provided in vb_selection.
    """
    vector_stores: List[Tuple[str, Chroma]] = []
    
    # Iterate through the selected database names
    for db_name in vb_selection:
        db_path = Path(VECTOR_DB_ROOT) / db_name
        
        # Check if the path is a directory
        if db_path.is_dir():
            try:
                # Initialize the Chroma store
                store = init_chroma(db_path.as_posix())
                vector_stores.append((db_name, store))
            except Exception as e:
                # Log a warning if a selected database cannot be initialized
                print(f"Warning: Could not initialize Chroma from selected DB '{db_name}': {e}")
        else:
            # Log a warning if the selected path is not found or not a directory
            print(f"Warning: Selected vector database path not found or not a directory: '{db_name}' at {db_path.as_posix()}")

    return vector_stores

# --- ParallelRAGRetriever Class ---

class ParallelRAGRetriever:
    def __init__(self, stores: List[Tuple[str, Chroma]]):
        self.stores = stores

    def _search_single_db(self, db_name: str, vector_store: Chroma, query: str, k_per_db: int) -> List[Document]:
        """Performs a similarity search on a single vector store."""
        try:
            # Use similarity_search to retrieve k_per_db documents
            results = vector_store.similarity_search(query, k=k_per_db)
            
            modified_results: List[Document] = []
            
            # String to prepend to the content
            prefix_string = f"According to data from {db_name} the relevant context is :\n"
            
            for doc in results:
                new_page_content = prefix_string + doc.page_content
                modified_doc = Document(
                    page_content=new_page_content,
                    metadata=doc.metadata
                )
                modified_results.append(modified_doc)
                
            return modified_results
            
        except Exception as e:
            # Handle search errors gracefully
            print(f"Error during search in {db_name}: {e}")
            return []

    def get_context(self, query: str, k_per_db: int) -> List[Document]:
        """
        Retrieves context from all initialized vector stores in parallel.
        k_per_db: The number of documents to retrieve from *each* database.
        """
        all_results: List[Document] = []
        
        if not self.stores:
            return all_results

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=len(self.stores)) as executor:
            future_to_db = {
                # k_per_db is now passed from the calling function (rag_context)
                executor.submit(self._search_single_db, name, store, query, k_per_db): name
                for name, store in self.stores
            }
            
            for future in future_to_db:
                try:
                    results_from_db = future.result()
                    all_results.extend(results_from_db)
                except Exception as e:
                    print(f"Error retrieving results from a thread: {e}")
                    
        return all_results

# NOTE: The instantiation of the retriever object must now be done INSIDE
# the rag_context function or at the top level with a default/empty selection, 
# as it depends on the vb_selection parameter which comes from main.py.

# The discovery and instantiation code block is removed from the global scope.

# The main RAG function is updated to accept vb_selection and k
def rag_context(query: str, vb_selection: List[str], k: int) -> str:
    """
    Initializes selected vector stores, performs parallel retrieval, 
    and returns a concatenated string of the context.
    
    query: The user's query string.
    vb_selection: List of vector database directory names to use.
    k: The number of documents to retrieve from *each* selected database.
    """
    # 1. Initialize ONLY the selected vector stores
    selected_stores = init_selected_vector_stores(vb_selection)
    
    if not selected_stores:
        print("Warning: No vector databases were initialized for retrieval.")
        return ""
        
    # 2. Instantiate the parallel retriever object with selected stores
    parallel_rag_retriever = ParallelRAGRetriever(selected_stores)
    
    # 3. Perform retrieval with the specified k
    context_documents: List[Document] = parallel_rag_retriever.get_context(query, k_per_db=k)
    
    # 4. Format the result as a single string (as suggested by the main.py usage: rag_context_str)
    # The documents are already formatted with the prefix in _search_single_db.
    context_str = "\n---\n".join([doc.page_content for doc in context_documents])
    
    return context_str

# IMPORTANT: The return type of rag_context is assumed to be a string (rag_context_str in main.py)
# If you actually need List[Document], change the return type and the last few lines.