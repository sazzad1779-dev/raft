
prompt_templates = {
    "gpt": """
        Question: {question}
        Context: {context}

        Answer this question using the information given in the context above.
        
        Instructions:
        - All the response should be in English but maintain full descriptions.
        - Provide step-by-step reasoning on how to answer the question.
        - Explain which parts of the context are meaningful and why.
        - Copy paste the relevant sentences from the context in ##begin_quote## and ##end_quote##.
        - Provide a summary of how you reached your answer.
        - End your response with the final answer in the form <ANSWER>: $answer, the answer should be succinct.
        - You MUST begin your final answer with the tag "<ANSWER>:".
        
        Output structure:
        1. Brief factual explanation (1–2 short paragraphs)
        2. Quoted specification evidence (if applicable)
        3. Final in depth answer                
    """
    }


build_qa_messages = {
    "gpt": lambda chunk, x : [
            {
        "role": "system",
        "content": (
            "You are a synthetic question generator for a product knowledge base focused on sevensix products. "
            "Input: You will be given a chunk of product-related text, such as product descriptions, technical specifications, wavelength ranges, features, applications, and product names."
            "Task: Generate %s realistic, human-like user questions that could be naturally asked by customers, researchers, or engineers and that can be answered directly using ONLY the information in the provided text."
            """Guidelines:
                - Write questions as a real human would ask them in sales, support, or research contexts.
                - Vary the intent and phrasing of the questions, including:
                - General product inquiries (e.g., “Can you tell me about …”)
                - Specification-driven questions (e.g., wavelength range, beam quality, output)
                - Use-case or application questions (e.g., imaging, spectroscopy, OCT, FLIM)
                - Comparison or selection-oriented questions (without requiring external knowledge)
                - Use natural language, not keyword lists or documentation-style phrasing.
                - Do NOT invent specifications, applications, or product names.
                - Do NOT ask questions that require information outside the given text.
                - Avoid repetitive wording; each question should feel distinct.
                
                Examples of desired question styles:
                - “I’m looking for a broadband laser source—what options are available here?”
                - “Can you tell me about the SuperK FIANIUM?”
                - “What laser light sources cover the 400–2400 nm wavelength range?”
                - “Is this product suitable for OCT or fluorescence imaging?”
                - “Recommend some laser product?”

                Output:
                - Return only the questions.
                - Do not include explanations, answers, or numbering unless explicitly requested.
                """
            
        ) % (x)
            },
            {"role": "system", "content": "The questions must be concise, factual, and focused on products, specifications, or usage. Include only the questions in your response."},
            {"role": "user", "content": str(chunk)}
        ]
}