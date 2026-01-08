from src.prompt import build_qa_messages, prompt_templates
from typing import Literal, Any, get_args
from src.client_utils import ChatCompleter
from openai import OpenAI, BadRequestError
from src.logconf import log_setup
from src.args import DocType
import logging
import random
import uuid
log_setup()# take environment variables from .env.
logger = logging.getLogger("raft")

def generate_question(chat_completer: ChatCompleter, chunk: Any, x: int = 5, model: str = None, prompt_key : str = "gpt") -> list[str]:
    """
    Generates `x` questions / use cases for `chunk`. Used when the input document is of general types 
    `pdf`, `json`, or `txt`.
    """
    try:
        response = chat_completer(
            model=model,
            messages=build_qa_messages[prompt_key](chunk, x),
            max_tokens=min(100 * x, 1024), # 25 tokens per question
        )
    except BadRequestError as e:
        if e.code == "content_filter":
            logger.warning(f"Got content filter error, skipping chunk: {e.message}")
            return []
        raise e

    content = response.choices[0].message.content
    queries = content.split('\n') if content else []
    #queries = [strip_str(q) for q in queries]
    queries = [q for q in queries if any(c.isalpha() for c in q)]
    return queries


def encode_question_gen(question: str, chunk: Any, prompt_key : str = "gpt") -> list[str]:
    """
    Encode multiple prompt instructions into a single string for the general case (`pdf`, `json`, or `txt`).
    """
    
    prompts = []

    prompt = prompt_templates[prompt_key].format(question=question, context=str(chunk))
    prompts.append({"role": "system", "content": "You are a helpful question answerer who can provide an answer given a question and relevant context."})
    prompts.append({"role": "user", "content": prompt})
    return prompts

def generate_answer(chat_completer: ChatCompleter, question: str, context: Any, doctype: DocType = "pdf", model: str = None, prompt_key : str = "gpt") -> str | None:
    """
    Generates the label / answer to `question` using `context` and GPT-4.
    """
    question = encode_question_gen(question, context, prompt_key)
    response = chat_completer(
        model=model,
        messages=question,
        n=1,
        temperature=0,
        max_tokens=1024,
    )
    response = response.choices[0].message.content
    return response

def generate_question_cot_answer(
        chat_completer: ChatCompleter,
        chunks: list[str], 
        chunk: str, 
        chunk_id, 
        question,
        doctype: DocType = "api", 
        num_distract: int = 3, 
        p: float = 0.8,
        model: str = None,
        prompt_key: str = "gpt",
        ):
    datapt = {
            "id": None,
            "type": None,
            "question": None,
            "context": None,
            "oracle_context": None,
            "cot_answer": None
        }

    datapt["id"] = str(uuid.uuid4())
    datapt["type"] = "api call" if doctype == "api" else "general"
    datapt["question"] = question

    # add num_distract distractor docs
    docs = [chunk]
    indices = list(range(0, len(chunks)))
    indices.remove(chunk_id)
    for j in random.sample(indices, num_distract):
        docs.append(chunks[j])
    # decides whether to add oracle document
    oracle = random.uniform(0, 1) < p
    if not oracle:
        docs[0] = chunks[random.sample(indices, 1)[0]]
    random.shuffle(docs)

    d = {
        "title": [],
        "sentences": []
    }

    d["title"].append(["placeholder_title"]*(num_distract+1))
    d["sentences"].append(docs)
    datapt["context"] = d
    datapt["oracle_context"] = chunk

    # add answer to q
    datapt["cot_answer"] = generate_answer(chat_completer, question, chunk, doctype, model=model, prompt_key=prompt_key)

    # construct model instruction 
    context = ""
    for doc in docs:
        context += "<DOCUMENT>" + str(doc) + "</DOCUMENT>\n"
    context += question
    datapt["instruction"] = context
    return datapt