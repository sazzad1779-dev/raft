
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
        - End your response with the final answer in the form <ANSWER>: $answer.
        - You MUST begin your final answer with the tag "<ANSWER>:".
        
        Output structure:
        1. Brief factual explanation (1–2 short paragraphs)
        2. Quoted specification evidence (if applicable)
        3. Final in depth answer  

        Response format:
        - If query related to product specifications:
            [Query related response]
            [product Description]
            [product Features]
            [Reference Resource]
        - If 
                      
    """
    }


# build_qa_messages = {
#     "gpt": lambda chunk, x : [
#             {
#         "role": "system",
#         "content": (
#             """You are a synthetic question generator for a product knowledge base focused on sevensix products. 
#             Input: You will be given a chunk of product-related text, such as product descriptions, technical specifications, wavelength ranges, features, applications, and product names.
#             Task: Generate %s realistic, human-like user questions that could be naturally asked by customers, researchers, or engineers and that can be answered directly using ONLY the information in the provided text.
#             Guidelines:
#                 - Write questions as a real human would ask them in sales, support, or research contexts.
#                 - Vary the intent and phrasing of the questions, including:
#                 - General product inquiries (e.g., “Can you tell me about …”)
#                 - Specification-driven questions (e.g., wavelength range, beam quality, output)
#                 - Use-case or application questions (e.g., imaging, spectroscopy, OCT, FLIM, laser)
#                 - Comparison or selection-oriented questions (without requiring external knowledge)
#                 - Use natural language, not keyword lists or documentation-style phrasing.
#                 - Do NOT ask questions that require information outside the given text.
#                 - Avoid repetitive wording; each question should feel distinct.
                
#                 Examples of desired question styles:
#                 - “I’m looking for a broadband laser source—what options are available here?”
#                 - “Can you tell me about the SuperK FIANIUM?”
#                 - “What laser light sources cover the 400–2400 nm wavelength range?”
#                 - “Is this product suitable for OCT or fluorescence imaging?”
#                 - “Recommend some laser product?”

#                 Output:
#                 - Return only the questions.
#                 - Do not include explanations, answers, or numbering unless explicitly requested.
#                 """
            
#         ) % (x)
#             },
#             {"role": "system", "content": "The questions must be concise, factual, and focused on products, specifications, or usage. Include only the questions in your response."},
#             {"role": "user", "content": str(chunk)}
#         ]
# }


build_qa_messages = {
    "gpt": lambda chunk, x: [
        {
            "role": "system",
            "content": f"""You are an expert question designer for training retrieval-augmented AI systems. Your task is to create {x} high-quality, challenging questions based EXCLUSIVELY on the provided product documentation chunk.

            **CONTEXT:** You are creating training data for RAFT (Retrieval-Augmented Fine-Tuning) where the model must learn to identify which information in the knowledge base can answer specific questions.

            **INPUT:** A chunk of product documentation about SevenSix products.

            **TASK:** Generate {x} diverse, challenging questions that:
            1. **Vary in Difficulty:**
            - 30% Simple fact retrieval (directly stated in text)
            - 40% Moderate inference (combine 2-3 facts from text)
            - 30% Complex reasoning (require understanding relationships/context)

            2. **Focus on Real User Scenarios:**
            - Product selection/configuration questions
            - Technical specification clarification
            - Use-case suitability assessment
            - Comparison between features/products mentioned
            - Problem-solving/troubleshooting scenarios

            3. **Test Knowledge Boundaries:**
            - Some questions should require ONLY the current chunk
            - Some should imply need for additional context (but don't state this)
            - Include questions with ambiguous phrasing that requires careful reading

            4. **Question Types to Include:**
            - “What laser light sources cover the 400–2400 nm wavelength range?”
            - "What are the key differences between [Product A] and [Product B] mentioned here?"
            - "If I need [specific requirement], which product from this text would you recommend and why?"
            - "How would I configure [product] for [specific application] based on these specs?"
            - "What limitations or constraints should I consider when using [product] for [purpose]?"
            - "Tell me about [product]"
            - “Can you tell me about the [product]?”
            
            **INSTRUCTION:** 
            - "Don't mention document reference in the question"
            - "Maintain the document language prefered JAPANESE"

            **FORMAT:** Return only the questions, one per line, without numbering or explanations."""
                    },
                    {"role": "user", "content": f"Product Documentation Chunk:\n\n{chunk}"}
                ]
        }