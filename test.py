from datasets import Dataset
checkpoints_chunks_path= "results"
chunks_ds = Dataset.load_from_disk(checkpoints_chunks_path)
def view_data():
    print(chunks_ds)
    for result in chunks_ds:
        print(f"question: \n{result["question"]}\ncot_answer: \n{result["cot_answer"]}\n\ngeneric_answer: \n{result["generic_answer"]}\n\n\n")


def upload_data():
    from huggingface_hub import login, upload_folder
    from dotenv import load_dotenv
    load_dotenv(override=True)
    login()

    chunks_ds.push_to_hub("sha1779/sevensix_product_datasets")

view_data()