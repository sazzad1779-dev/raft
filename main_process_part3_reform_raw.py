import os
from pathlib import Path
from dotenv import load_dotenv
import json
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

import time
from requests.exceptions import Timeout
from multiprocessing import Pool
import re
from main_process_prompt import PROMPT
load_dotenv()

INPUT_DIR = Path("output_directory2")
OUTPUT_DIR = Path("processed_md")
TRACK_FILE = Path("processed_files.json")


def load_processed_files() -> set:
    """Load already processed file paths from JSON."""
    if TRACK_FILE.exists():
        try:
            with open(TRACK_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Failed to load {TRACK_FILE}: {e}")
    return set()

def save_processed_file(file_path: str):
    """Append a file path to the JSON tracker."""
    processed = load_processed_files()
    processed.add(file_path)
    with open(TRACK_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(processed), f, indent=2)


def list_md_files(input_dir: Path) -> list[Path]:
    return sorted([p for p in input_dir.rglob("*.md") if p.is_file()])

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def write_output(output_root: Path, input_root: Path, input_file: Path, content: str):
    rel_path = input_file.relative_to(input_root)
    out_path = output_root / rel_path
    ensure_dir(out_path.parent)
    out_path.write_text(content, encoding="utf-8")

def split_markdown(raw_md: str, max_length: int = 2000) -> list[str]:
    raw_md = re.sub(r'\n\s*\n', '\n\n', raw_md.strip())
    paragraphs = [p.strip() for p in raw_md.split("\n\n") if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # Split long paragraphs
        while len(para) > max_length:
            match = re.search(r'.{1,' + str(max_length) + r'}[。！？]', para)
            split_pos = match.end() if match else max_length
            chunks.append(para[:split_pos].strip())
            para = para[split_pos:].strip()
        
        # Try to merge with current chunk
        if len(current_chunk) + len(para) + 2 <= max_length:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Merge small chunks back together
    merged = []
    temp = ""
    for chunk in chunks:
        if len(temp) + len(chunk) + 2 <= max_length:
            temp += chunk + "\n\n"
        else:
            if temp:
                merged.append(temp.strip())
            temp = chunk + "\n\n"
    if temp:
        merged.append(temp.strip())
    
    return merged
def process_with_langchain(llm, raw_md: str) -> str:

    chain = PROMPT | llm
    msg = chain.invoke({"raw_md": raw_md})

    # msg is AIMessage; content is the markdown text
    return (msg.content or "").strip()

def process_raw(args):
    file_path= args
    file_path_str = str(file_path)
    
    # Skip if already processed
    processed_files = load_processed_files()
    if file_path_str in processed_files:
        print(f"SKIPPED (already processed) -> {file_path.name}")
        return
    raw_md = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not raw_md:
        write_output(OUTPUT_DIR, INPUT_DIR, file_path, "")
        print(f"EMPTY -> {file_path.name}")
        save_processed_file(file_path_str)
        return

    try:
        print(f"Processing -> {file_path}")
        try:
            llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                temperature=0.0,
                # openai_api_key=api_key,
                timeout=100,
            )

            length = len(raw_md)
            if length > 8000:

                print(f"Warning: Input markdown length {length} exceeds typical limits.skipping file for now{file_path.name}")
                
                # chunks = split_markdown(raw_md, max_length=2000)
                # cleaned = ""
                # for i, chunk in enumerate(chunks):
                #     print(f"Processing chunk {i+1} with length {len(chunk)}")
                #     cleaned += process_with_langchain(llm, chunk)
            else:
                print(f"{file_path.name} file input markdown length: {length}") 
                cleaned = process_with_langchain(llm, raw_md)
            write_output(OUTPUT_DIR, INPUT_DIR, file_path, cleaned)
            print(f"OK -> {file_path.name}")
            save_processed_file(file_path_str)
            time.sleep(20)
        except Timeout:
            print("Request timed out!")
    except Exception as e:
        print(f"FAIL -> {file_path.name}: {e}")
        time.sleep(20)


import random
from multiprocessing import Pool

if __name__ == "__main__":
    ensure_dir(OUTPUT_DIR)
    md_files = list_md_files(INPUT_DIR)
    print(f"Found {len(md_files)} .md files to process.")
    if not md_files:
        print(f"No .md files found in: {INPUT_DIR}")

    # Assign a random API key for each file
    jobs = [f for f in md_files]

    with Pool(4) as pool:
        results = pool.map(process_raw, jobs)


