from tqdm import tqdm
from src.logconf import log_setup
import logging
from openai import OpenAI, BadRequestError
import datasets
from datasets import Dataset, concatenate_datasets
import pyarrow as pa
from src.client_utils import build_openai_client, build_langchain_embeddings, UsageStats, ChatCompleter
from pathlib import Path
from dotenv import load_dotenv
from src.checkpointing import Checkpointing, checkpointed
from threading import Thread, Event
from src.args import DocType, get_args_func
from src.utils import get_chunks, get_doc_chunks, build_or_load_chunks, strip_str
from src.generate import generate_question, generate_question_cot_answer,generate_question_json

log_setup()

load_dotenv(override=True)  # take environment variables from .env.

logger = logging.getLogger("raft")


def test_generate_questions():
    """Test function for generating questions from a single chunk"""
    args = get_args_func()
    
    OPENAPI_API_KEY = args.openai_key
    client = build_openai_client(api_key=OPENAPI_API_KEY)
    chat_completer = ChatCompleter(client)
    
    CHUNK_SIZE = args.chunk_size
    datapath = args.datapath
    doctype = args.doctype
    completion_model = args.completion_model
    system_prompt_key = args.system_prompt_key
    output_path = Path(args.output).absolute()

    checkpoints_dir = Path(str(output_path) + "-checkpoints").absolute()
    # Build or load chunks
    chunks = build_or_load_chunks(datapath, doctype, CHUNK_SIZE, OPENAPI_API_KEY, args.embedding_model, checkpoints_dir)
    
    if not chunks:
        logger.error("No chunks generated/loaded")
        return None
    
    # Test with first chunk
    test_chunk = chunks[0]
    logger.info(f"Testing question generation on chunk: {test_chunk[:100]}...")
    
    try:
        questions = generate_question_json(
            chunk=test_chunk,
            chat_completer=chat_completer,
            x=args.questions,  # number of questions to generate
            model=completion_model,
            prompt_key=system_prompt_key
        )
        
        logger.info(f"Generated {len(questions)} questions:")
        for i, q in enumerate(questions, 1):
            logger.info(f"Q{i}: {q}")
        
        return questions
    
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        return None
    

def test_generate_answer_with_cot():
    """Test function for generating answer with chain-of-thought for a specific question"""
    args = get_args_func()
    
    OPENAPI_API_KEY = args.openai_key
    client = build_openai_client(api_key=OPENAPI_API_KEY)
    chat_completer = ChatCompleter(client)
    
    CHUNK_SIZE = args.chunk_size
    datapath = args.datapath
    doctype = args.doctype
    completion_model = args.completion_model
    system_prompt_key = args.system_prompt_key
    NUM_DISTRACT_DOCS = args.distractors
    p = args.p
    output_path = Path(args.output).absolute()
    checkpoints_dir = Path(str(output_path) + "-checkpoints").absolute()
    # Build or load chunks
    chunks = build_or_load_chunks(datapath, doctype, CHUNK_SIZE, OPENAPI_API_KEY, args.embedding_model, checkpoints_dir) 

    if not chunks:
        logger.error("No chunks generated/loaded")
        return None
    
    # Test with first chunk
    test_chunk = chunks[0]
    test_chunk_id = 0
    
    # Create a test question
    test_question = "What is the main topic discussed in this text?"
    
    logger.info(f"Testing answer generation with CoT")
    logger.info(f"Chunk: {test_chunk[:100]}...")
    logger.info(f"Question: {test_question}")
    
    try:
        cot_answer = generate_question_cot_answer(
            chunk=test_chunk,
            chunk_id=test_chunk_id,
            chunks=chunks,
            question=test_question,
            chat_completer=chat_completer,
            model=completion_model,
            doctype=doctype,
            prompt_key=system_prompt_key,
            num_distract=NUM_DISTRACT_DOCS,
            p=p
        )
        
        logger.info(f"Generated answer with CoT:")
        logger.info(f"Question: {cot_answer.get('question')}")
        logger.info(f"Answer: {cot_answer.get('answer')}")
        logger.info(f"Chain of Thought: {cot_answer.get('cot')}")
        logger.info(f"Distractor docs: {len(cot_answer.get('distractors', []))}")
        
        return cot_answer
    
    except BadRequestError as e:
        if e.code == "content_filter":
            logger.warning(f"Got content filter error: {e.message}")
        else:
            logger.error(f"OpenAI API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error generating answer with CoT: {e}")
        return None
