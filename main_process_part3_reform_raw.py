import os
from pathlib import Path
from dotenv import load_dotenv
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import time
from requests.exceptions import Timeout
from multiprocessing import Pool
import re
load_dotenv()

INPUT_DIR = Path("output_directory")
OUTPUT_DIR = Path("processed_md")

MODEL = "gemini-2.5-flash"

SYSTEM_STYLE = """
You are a technical content cleaner and organizer.

Goal:
- Convert raw markdown into a clean, well-structured markdown document.
- Keep important info, remove irrelevant/duplicated fluff.
- Improve readability and depth without inventing facts.
- If tables exist or can be derived (specs, features, comparisons), produce a clean descriptive markdown sentence of the tables.
- Use clear headings, bullets, and concise paragraphs.
- Preserve code blocks and technical values exactly as-is.

Rules:
- Do NOT add fake specs or unknown values.
- Do NOT remove technical details.
- Do NOT invent new sections or content.
- Do NOT change product names, model numbers, units, wavelengths, ranges, part numbers.
- Keep content sequence as it is, reorganize only within existing content.

Table Guidelines:
1. Provide **descriptive sentences** for large tables to summarize the content clearly.
2. Include **relevant headers** in the description to give context.
3. For **large tables** (e.g., specifications, feature comparisons), give an **in-depth yet concise description**, covering all important details without skipping critical information.
4. For **small tables** (e.g., 2-3 rows/columns), a brief summary is sufficient.

Product overviews:
- at the start of the document, include a brief product overview as utilizing product name,model,model number, category, and  manufacturer if available.

Output:
- Return ONLY markdown. No extra commentary.
- Respond in Japanese。
- Never remove pdf urls or links, keep them as is.

Instructions:
- Follow the requirements strictly.
- Never hallucinate or fabricate information.
- Never fall in loops.

"""
PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_STYLE),
        (
            "human",
            """Process the following markdown.
Requirements:
1) Remove irrelevant navigation/footer/noise (cookie banners, repeated menus, unrelated links).
2) Fix broken markdown.
3) Make sections more in-depth by reorganizing what is already present (do not invent).
4) If content includes specs/parameters scattered in text, convert to a descriptive markdown table.
5) Keep product names, model numbers, units, wavelengths, ranges, part numbers unchanged.
6) Don't add any irrelevant commentary or explanation. 

RAW MARKDOWN:
---
{raw_md}
---
""",
        ),
    ]
)



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
    file_path, api_key = args
    file_path_str = str(file_path)
    
    # Skip if already processed
    processed_files = load_processed_files()
    if file_path_str in processed_files:
        print(f"SKIPPED (already processed) -> {file_path.name}")
        return
    print(f"using api key: {api_key} for file: {file_path.name}")
    raw_md = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not raw_md:
        write_output(OUTPUT_DIR, INPUT_DIR, file_path, "")
        print(f"EMPTY -> {file_path.name}")
        save_processed_file(file_path_str)
        return

    try:
        print(f"Processing -> {file_path}")
        try:
            # llm = ChatGoogleGenerativeAI(
            #     model=MODEL,
            #     temperature=0.0,
            #     api_key=api_key,
            #     timeout=50,
            # )
            llm = ChatGroq(
                model_name="moonshotai/kimi-k2-instruct",#"openai/gpt-oss-120b",
                temperature=0.1,
                timeout=50
                )

            length = len(raw_md)
            if length > 4000:

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

    # Load API keys from environment
    api_keys_str = os.getenv("GEMINI_API_KEYS", "")
    api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
    if not api_keys:
        raise ValueError("No API keys found in GEMINI_API_KEYS")

    # Assign a random API key for each file
    jobs = [(f, random.choice(api_keys)) for f in md_files]

    with Pool(4) as pool:
        results = pool.map(process_raw, jobs)


