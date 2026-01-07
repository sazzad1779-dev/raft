from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from mdc import MDC
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
from src.utils import get_chunks, get_doc_chunks,build_or_load_chunks , strip_str
from src.generate import generate_instructions_gen, generate_question_cot_answer
log_setup()

load_dotenv(override=True)  # take environment variables from .env.

logger = logging.getLogger("raft")

def main():

    main_start = time.time()

    # run code
    args = get_args_func()

    # Validate arguments
    if args.output_chat_system_prompt and args.output_format != "chat":
        raise Exception("Parameter --output-chat-system-prompt can only be used with --output-format chat")

    OPENAPI_API_KEY = args.openai_key

    client = build_openai_client(
        api_key=OPENAPI_API_KEY,
    )
    chat_completer = ChatCompleter(client)

    CHUNK_SIZE = args.chunk_size
    NUM_DISTRACT_DOCS = args.distractors

    output_path = Path(args.output).absolute()

    checkpoints_dir = Path(str(output_path) + "-checkpoints").absolute()
    auto_clean_checkpoints = args.auto_clean_checkpoints
    if auto_clean_checkpoints:
        logger.info(f"Checkpoints will be automatically deleted after dataset generation. Remove --auto-clean-checkpoints to deactivate.")

    datapath: Path = args.datapath

    datasets.disable_progress_bars()

    # Chunks
    chunks = build_or_load_chunks(datapath, args.doctype, CHUNK_SIZE, OPENAPI_API_KEY, args.embedding_model, checkpoints_dir)

    cot_answers_ds = None

    num_chunks = len(chunks)
    num_questions = args.questions
    max_workers = args.workers
    doctype = args.doctype
    completion_model = args.completion_model

    system_prompt_key = args.system_prompt_key

    logger.info(f"Using system prompt key {system_prompt_key}")

    logger.info(f"Using {max_workers} worker threads")

    cot_answers_ds = stage_generate(chat_completer, checkpoints_dir, chunks, num_questions, max_workers, doctype, completion_model, system_prompt_key, num_distract=NUM_DISTRACT_DOCS, p=args.p, qa_threshold=args.qa_threshold)

    # Save as .arrow format
    datasets.enable_progress_bars()
    cot_answers_ds.save_to_disk(str(output_path))

    ############ Formater Operations ############
    # # Save as .jsonl format
    # formatter = DatasetConverter()

    # # Extract format specific params
    # format_params = {}
    # if args.output_chat_system_prompt:
    #     format_params['system_prompt'] = args.output_chat_system_prompt

    # if args.output_format == "completion":
    #     format_params['prompt_column'] = args.output_completion_prompt_column
    #     format_params['completion_column'] = args.output_completion_completion_column

    # formatter.convert(ds=cot_answers_ds, format=args.output_format, output_path=str(output_path), output_type=args.output_type, params=format_params)

    # # Warning, this deletes all intermediary checkpoint files
    # if auto_clean_checkpoints:
    #     shutil.rmtree(checkpoints_dir)

    # logger.info(f"Generated {len(cot_answers_ds)} question/answer/CoT/documents samples")
    # logger.info(f"Dataset saved to {output_path}")
    # logger.info(f"Done in {time.time() - main_start:.2f}s")

class StoppingException(Exception):
    """
    Raised by worker threads when the process is stopping early
    """
    pass

def stage_generate(chat_completer: ChatCompleter, checkpoints_dir, chunks, num_questions, max_workers, doctype, completion_model, system_prompt_key, num_distract, p, qa_threshold):
    """
    Given a chunk, create {Q, A, D} triplets and add them to the dataset.
    """

    questions_checkpointing = Checkpointing(checkpoints_dir / "questions")
    answers_checkpointing = Checkpointing(checkpoints_dir / "answers")
    num_chunks = len(chunks)

    # Tracking when the process is stopping, so we can stop the generation process early
    # Initial value is False
    is_stopping = Event()

    @checkpointed(questions_checkpointing)
    def generate_chunk_instructions_ds(chunk: str, chunk_id: int, doctype: str, *args, **kwargs):
        """
        Generates a dataset of instructions for a given chunk.
        """
        questions = generate_instructions_gen(chunk=chunk, *args, **kwargs)
        chunk_question_pairs = [{"chunk": chunk, "chunk_id": chunk_id, "question": question} for question in questions]
        questions_ds = Dataset.from_list(chunk_question_pairs)
        return questions_ds

    @checkpointed(answers_checkpointing)
    def generate_question_cot_answers(questions_ds, chunk_id: int, chunk: str, *args, **kwargs):
        def process_example(chunk, question):
            try:
                cot_answer = generate_question_cot_answer(chunk=chunk, chunk_id=chunk_id, chunks=chunks, question=question, *args, **kwargs)
            except BadRequestError as e:
                if e.code == "content_filter":
                    logger.warning(f"Got content filter error, skipping question '{question}': {e.message}")
                    return None
                raise e

            return cot_answer

        results = [process_example(chunk, question) for chunk, question in zip(questions_ds['chunk'], questions_ds['question'])] if len(questions_ds) > 0 else []
        results = [r for r in results if r is not None]
        table = pa.Table.from_pylist(results)
        ds = Dataset(table)
        return ds

    def process_chunk(i):
        if is_stopping.is_set():
            raise StoppingException()
        chunk = chunks[i]
        questions_ds = generate_chunk_instructions_ds(chunk=chunk, chunk_id=i, chat_completer=chat_completer, x=num_questions, model=completion_model, doctype=doctype, prompt_key=system_prompt_key)
        answers_ds = generate_question_cot_answers(questions_ds=questions_ds, chunk=chunk, chunk_id=i, chat_completer=chat_completer, model=completion_model, doctype=doctype, prompt_key=system_prompt_key, num_distract=num_distract, p=p)
        return answers_ds

    futures = []
    answers_ds_list = []
    usage_stats = UsageStats()

    # we use the checkpointing to keep track of the chunks that have already been processed
    # the answers are generated after the questions so the process might have been stopped in between a batch of answers and matching questions
    # so we need to use the answers checkpointing to keep track of which chunks we need to process
    # if the questions for a given chunk have already been checkpointed, they will just be loaded from the checkpoint
    # we set the tqdm's initial position to avoid having cached data skew the stats
    missing_chunks = answers_checkpointing.missing_checkpoints(num_chunks)

    gen_questions_count = 0
    if answers_checkpointing.has_checkpoints():
        ds = answers_checkpointing.collect_checkpoints()
        gen_questions_count = len(ds)

    done_chunks = num_chunks - len(missing_chunks)
    if done_chunks > 0 or gen_questions_count > 0:
        logger.info(f"Resuming generation from chunk {done_chunks}/{num_chunks} and {gen_questions_count} questions")

    # If we have a QA threshold, it makes more sense to keep track of the number of questions generated
    # Otherwise, track chunks
    track_questions = qa_threshold is not None

    if qa_threshold:
        logger.info(f"Will stop early as soon as the QA threshold is met: {qa_threshold}")

    if track_questions:
        tqdm_args = {"total": qa_threshold, "unit": "qa", "initial": gen_questions_count}
    else:
        tqdm_args = {"total": num_chunks, "unit": "chunk", "initial": done_chunks}

    tps = 0
    with tqdm(desc="Generating", **tqdm_args) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in missing_chunks:
                futures.append(executor.submit(process_chunk, i))
            for future in as_completed(futures):
                if qa_threshold and gen_questions_count >= qa_threshold:
                    logger.info(f"Met threshold {gen_questions_count} >= {qa_threshold} questions, stopping generation")
                    is_stopping.set()
                    break
                answers_ds = future.result()
                answers_ds_list.append(answers_ds)
                increment = min(len(answers_ds), qa_threshold - gen_questions_count) if track_questions else 1
                gen_questions_count += len(answers_ds)
                done_chunks += 1
                stats = chat_completer.get_stats_and_reset()
                if stats:
                    tps = stats.total_tokens / stats.duration
                    usage_stats += stats
                postfix = {'last tok/s': tps, 'avg tok/s': usage_stats.total_tokens / usage_stats.duration if usage_stats.duration > 0 else 0}
                if track_questions:
                    postfix['chunks'] = done_chunks
                else:
                    postfix['qa'] = gen_questions_count
                pbar.set_postfix(postfix)
                pbar.update(increment)

    ds = answers_checkpointing.collect_checkpoints()
    ds = ds.select(range(qa_threshold)) if qa_threshold else ds
    logger.info(f"Consumed {usage_stats.prompt_tokens} prompt tokens, {usage_stats.completion_tokens} completion tokens, {usage_stats.total_tokens} total tokens")

    return ds

def raft():
    with MDC(progress="0%"):
        main()
