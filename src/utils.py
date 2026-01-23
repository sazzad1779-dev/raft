from pathlib import Path
from src.args import DocType
from src.client_utils import build_openai_client, build_langchain_embeddings, UsageStats, ChatCompleter
import logging
from src.logconf import log_setup
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import PyPDF2
import random
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from math import ceil
from datasets import Dataset, concatenate_datasets
import pyarrow as pa
log_setup()

logger = logging.getLogger("raft")
def get_chunks(
    data_path: Path, 
    doctype: DocType = "pdf", 
    chunk_size: int = 512, 
    openai_key: str | None = None,
    model: str = None
) -> list[str]:
    """
    Takes in a `data_path` and `doctype`, retrieves the document, breaks it down into chunks of size
    `chunk_size`, and returns the chunks.
    """
    chunks = []

    logger.info(f"Retrieving chunks from {data_path} of type {doctype} using the {model} model.")

    # embeddings = build_langchain_embeddings(openai_api_key=openai_key, model=model)
    embeddings = OpenAIEmbeddings(model=model)
    chunks = []
    file_paths = [data_path]
    if data_path.is_dir():
        file_paths = list(data_path.rglob('**/*.' + doctype))

    futures = []
    with tqdm(total=len(file_paths), desc="Chunking", unit="file") as pbar:
        with ThreadPoolExecutor(max_workers=2) as executor:
            for file_path in file_paths:
                futures.append(executor.submit(get_doc_chunks, embeddings, file_path, doctype, chunk_size))
            for future in as_completed(futures):
                doc_chunks = future.result()
                chunks.extend(doc_chunks)
                pbar.set_postfix({'chunks': len(chunks)})
                pbar.update(1)

    return chunks

def get_doc_chunks(
    embeddings: OpenAIEmbeddings,
    file_path: Path, 
    doctype: DocType = "pdf", 
    chunk_size: int = 512,
 ) -> list[str]:
    if doctype == "json":
        with open(file_path, 'r') as f:
            data = json.load(f)
        text = data["text"]
    elif doctype == "pdf":
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text += page.extract_text()
    elif doctype in ("txt", "md"):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        raise TypeError("Document is not one of the accepted types: api, pdf, json, txt")
    
    num_chunks = ceil(len(text) / chunk_size)
    logger.debug(f"Splitting text into {num_chunks} chunks.")

    text_splitter = SemanticChunker(embeddings, number_of_chunks=num_chunks)
    chunks = text_splitter.create_documents([text])
    chunks = [chunk.page_content for chunk in chunks]
    return chunks

def build_or_load_chunks(
        datapath: Path, 
        doctype: str,
        CHUNK_SIZE: int, 
        OPENAPI_API_KEY: str,
        embedding_model: str,
        checkpoints_dir: Path, 
        ):
    """
    Builds chunks and checkpoints them if asked
    """
    chunks_ds: Dataset = None
    chunks = None
    checkpoints_chunks_path = checkpoints_dir / "chunks"
    logger.info(f"Using checkpoint chunks {checkpoints_chunks_path}")
    if checkpoints_chunks_path.exists():
        chunks_ds = Dataset.load_from_disk(checkpoints_chunks_path)
        chunks = chunks_ds['chunk']

    if not chunks:
        chunks = get_chunks(datapath, doctype, CHUNK_SIZE, OPENAPI_API_KEY, model=embedding_model)

    if not chunks_ds:
        chunks_table = pa.table({ "chunk": chunks })
        chunks_ds = Dataset(chunks_table)
        chunks_ds.save_to_disk(checkpoints_chunks_path)
    return chunks

def strip_str(s: str) -> str:
    """
    Helper function for helping format strings returned by GPT-4.
    """
    l, r = 0, len(s)-1
    beg_found = False
    for i in range(len(s)):
        if s[i].isalpha():
            if not beg_found:
                l = i
                beg_found = True
            else:
                r = i 
    r += 2
    return s[l:min(r, len(s))]