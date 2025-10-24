# build/streamlit_app.spec
# -*- mode: python ; coding: utf-8 -*-
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)

from PyInstaller.utils.hooks import collect_all
langchain_data, langchain_binaries, langchain_hiddenimports = collect_all('langchain')
block_cipher = None
chromadb_data, chromadb_binaries, chromadb_hiddenimports = collect_all('chromadb')
# Collect all of Streamlit's package data and hidden imports
streamlit_data, streamlit_binaries, streamlit_hiddenimports = collect_all('streamlit')
manual_hiddenimports = [
    # Langchain components
    'langchain.embeddings',
    'langchain.llms',
    'onnxruntime',
    'tokenizers',
    'tqdm',
    'loguru',
    # ChromaDB components (frequently missed due to dynamic imports/telemetry)
    'chromadb.telemetry.product.posthog', # <--- FIX for the current error
    'chromadb.api.segment',
    'chromadb.api.rust',
    'chromadb.db.impl.sqlite',
    'chromadb.migrations.embeddings_queue',
    'chromadb.segment.impl.manager.local',
    
    # Add other high-level langchain or chromadb submodules if you use them
     'langchain.vectorstores', 
     'chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2', # If you use default Chroma embeddings
]
a = Analysis(
    ['build/app_entry.py'],   # entrypoint
    pathex=[],
    binaries=[],
    datas=[
        ('ui/*', 'ui'),           # include UI folder
        ('backend/*', 'backend'), # include backend folder
        ('.env', '.'),
        ('.streamlit/config.toml', '.streamlit'),             # include .env if needed
    ] 
    # Corrected list concatenation for collected data
    + streamlit_data
    + langchain_data
    + chromadb_data, 
    hiddenimports=streamlit_hiddenimports + langchain_hiddenimports + manual_hiddenimports,  # add streamlit hidden imports
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

# also add collected binaries
a.binaries += streamlit_binaries
a.binaries += langchain_binaries 
a.binaries += chromadb_binaries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='app_entry',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # change to False if you don’t want a console window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='app_entry'
)
