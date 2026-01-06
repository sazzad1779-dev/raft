from datasets import Dataset
checkpoints_chunks_path= "results1-checkpoints/questions/checkpoint-0"
chunks_ds = Dataset.load_from_disk(checkpoints_chunks_path)
print(chunks_ds)
for result in chunks_ds:
    print(f"question: {result["question"]}\ncot_answer: {result["cot_answer"]}\n\n\n")