import argparse
from src.format import DatasetConverter, datasetFormats, outputDatasetTypes
from pathlib import Path
from typing import Literal, Any, get_args

DocType = Literal["api", "pdf", "json", "txt"]
docTypes = list(get_args(DocType))

SystemPromptKey = Literal["gpt", "llama"]
systemPromptKeys = list(get_args(SystemPromptKey))

def get_args_func() -> argparse.Namespace:
    """
    Parses and returns the arguments specified by the user's command
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--datapath", type=Path, default="test_data", help="If a file, the path at which the document is located. If a folder, the path at which to load all documents")
    parser.add_argument("--output", type=str, default="results1", help="The path at which to save the dataset")
    parser.add_argument("--output-format", type=str, default="chat", help="The format of the output dataset.", choices=datasetFormats)
    parser.add_argument("--output-type", type=str, default="jsonl", help="Type to export the dataset to. Defaults to jsonl.", choices=outputDatasetTypes)
    parser.add_argument("--output-chat-system-prompt", type=str, default="You are an expert technical assistant for sevensix company.", help="The system prompt to use when the output format is chat")
    parser.add_argument("--output-completion-prompt-column", type=str, default="prompt", help="The prompt column name to use for the completion format")
    parser.add_argument("--output-completion-completion-column", type=str, default="completion", help="The completion column name to use for the completion format")
    parser.add_argument("--distractors", type=int, default=1, help="The number of distractor documents to include per data point / triplet")
    parser.add_argument("--p", type=float, default=1.0, help="The percentage that the oracle document is included in the context")
    parser.add_argument("--questions", type=int, default=2, help="The number of data points / triplets to generate per chunk")
    parser.add_argument("--chunk_size", type=int, default=300, help="The size of each chunk in number of tokens")
    parser.add_argument("--doctype", type=str, default="txt", help="The type of the document, must be one of the accepted doctypes", choices=docTypes)
    parser.add_argument("--openai_key", type=str, default=None, help="Your OpenAI key used to make queries to GPT-3.5 or GPT-4")
    parser.add_argument("--embedding_model", type=str, default="text-embedding-3-small", help="The embedding model to use to encode documents chunks (text-embedding-3-small, ...)")
    parser.add_argument("--completion_model", type=str, default="gpt-4o-mini", help="The model to use to generate questions and answers (gpt-3.5, gpt-4, ...)")
    parser.add_argument("--system-prompt-key", default="gpt", help="The system prompt to use to generate the dataset", choices=systemPromptKeys)
    parser.add_argument("--workers", type=int, default=2, help="The number of worker threads to use to generate the dataset")
    parser.add_argument("--auto-clean-checkpoints", type=bool, default=False, help="Whether to auto clean the checkpoints after the dataset is generated")
    parser.add_argument("--qa-threshold", type=int, default=None, help="The number of Q/A samples to generate after which to stop the generation process. Defaults to None, which means generating Q/A samples for all documents")

    return parser.parse_args()
