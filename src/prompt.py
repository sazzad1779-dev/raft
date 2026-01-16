build_qa_messages = {
    "gpt": lambda chunk, x: [
        {
            "role": "system",
            "content": f"""You are an expert question designer creating training data for RAFT (Retrieval-Augmented Fine-Tuning). Your task is to generate {x} high-quality, realistic user questions based EXCLUSIVELY on the provided product documentation chunk.

            **INPUT:**
            - **Chunk:** A segment of product documentation about SevenSix products.
            - **Target Language:** JAPANESE. All questions must be in Japanese.

            **CORE TASK:**
            Generate {x} questions that a real user might ask after reading this documentation. The questions must be answerable solely from this chunk, though some can imply a need for broader context.

            **QUESTION TYPES (MANDATORY DISTRIBUTION):**
            Generate questions across these three types, ensuring a balanced mix:
            1.  **Factual (Exact):** Questions asking for definitions, specifications, or directly stated facts.
                *   *Example (English):* "What is the wavelength range of the Model X laser?"
            2.  **Conceptual (Reasoning):** Questions asking about 'why', 'how', trade-offs, or suitability for a use case.
                *   *Example (English):* "Why would I choose Product A over Product B for high-precision measurement?"
            3.  **Procedural (Action-Oriented):** Questions about configuration, troubleshooting, setup, or step-by-step processes.
                *   *Example (English):* "How do I calibrate the device for outdoor use?"

            **DIFFICULTY LEVELS (MANDATORY DISTRIBUTION):**
            For each question type above, you must generate questions at three difficulty levels:
            - **Grounded (Simple):** Well-formed, accurate, and directly answerable from a single sentence or fact.
            - **Medium (Moderate):** Mostly correct but may use vague phrasing, combine 2-3 facts, or reflect a partial understanding.
            - **Hard (Complex):** Reflect user confusion, contain a realistic typo or synonym, or require synthesizing multiple pieces of information and understanding context.

            **REALISM RULES (ENFORCED):**
            To ensure questions mirror real user behavior, you MUST adhere to the following constraints:
            - **Non-Question Fragments:** At least {max(1, int(x*0.3))} questions must be phrased as search-like fragments, not full grammatical questions (e.g., "laser wavelength range 400-2400nm").
            - **Lexical Mismatch:** At least {max(1, int(x*0.3))} questions must avoid the document's primary keywords and use synonyms or layman's terms (e.g., use "光の波長" instead of "波長範囲").
            - **Controlled Typos:** Exactly {1 if x >= 5 else 0} question (only in Medium or Hard difficulty) may include one realistic typo (e.g., "キャリブレーション" instead of "キャリブレーション").
            - **Diversity:** No two questions should be paraphrases. Each must target a distinct user intent (setup, specification, comparison, troubleshooting, etc.).
            - **Scenario Coverage:** Ensure the set includes questions related to:
                *   Product selection or configuration.
                *   Technical specification clarification.
                *   Problem-solving or error scenarios.
                *   Comparison between mentioned products/features.

            **ANSWERABILITY CONSTRAINT (STRICT):**
            Every question you generate MUST be answerable using only the information present in the provided chunk. Do not generate questions that require external knowledge.

            **OUTPUT REQUIREMENTS (STRICT):**
            - **OUTPUT Format:** Return a JSON list of {x} objects.
            - **Each Object Must Have These Fields:**
                *   `"question"`: The generated question (in Japanese).
                *   `"type"`: One of `"factual"`, `"conceptual"`, `"procedural"`.
                *   `"difficulty"`: One of `"grounded"`, `"medium"`, `"hard"`.
                *   `"grounding_evidence"`: A short (≤12 words) quote copied VERBATIM from the chunk that contains the answer. This proves answerability.
            **FINAL INSTRUCTION:**
            Do not mention the document, chunk, or your instructions in the questions. Generate natural, user-centric questions in Japanese."""
        },
        {"role": "user", "content": f"Product Documentation Chunk:\n\n{chunk}"}
    ]
}

cot_ans_prompt_templates = {
    "gpt": """
        ## TASK CONTEXT:
        You are generating training data for RAFT (Retrieval-Augmented Fine-Tuning). Below is a question generated with specific parameters, along with the documentation context needed to answer it.

        ## INPUT DATA:
        Question: {question}
        Question Type: {type}  # factual/conceptual/procedural
        Difficulty Level: {difficulty}  # grounded/medium/hard
        Grounding Evidence: {grounding_evidence}
        Context: {context}

        ## CORE INSTRUCTION:
        Generate a Chain-of-Thought (CoT) answer that demonstrates step-by-step reasoning using EXCLUSIVELY the provided context.

        ## DIFFICULTY-ADJUSTED REASONING:
        Adapt your reasoning depth based on the difficulty level:
        - **Grounded (Simple):** Provide direct reasoning with clear evidence mapping
        - **Medium (Moderate):** Include explanations for ambiguous terms or combined facts
        - **Hard (Complex):** Explicitly address potential confusion points, synonyms, or typos; show synthesis of multiple information pieces

        ## TYPE-SPECIFIC ANSWER STRUCTURE:
        
        **For Factual Questions:**
        1. Identify the exact specification/definition requested
        2. Quote the precise evidence
        3. Present the answer clearly
        
        **For Conceptual Questions (Why/How/Comparisons):**
        1. Identify the core concept or principle
        2. Explain the reasoning or mechanism from context
        3. Discuss implications, trade-offs, or suitability
        4. Support with quoted evidence
        
        **For Procedural Questions (Steps/Setup/Troubleshooting):**
        1. Extract the sequence or process from context
        2. Break down into logical steps
        3. Note any prerequisites or conditions
        4. Quote the procedural guidance

        ## REASONING REQUIREMENTS:
        - Begin with "**Reasoning Steps:**" and provide 3-5 clear reasoning steps
        - Explicitly connect each step to evidence from the context
        - For medium/hard difficulties, explain how you resolve vague phrasing or synthesize information
        - Verify answerability using the provided Grounding Evidence
        - Note any lexical mismatches (user terms vs. document terms)

        ## EVIDENCE HANDLING:
        - Copy VERBATIM relevant sentences between ##begin_quote## and ##end_quote##
        - For Hard questions: Show how you map user terminology to document terminology
        - If Grounding Evidence is insufficient, search the full Context for complementary information

        ## RESPONSE FORMAT:
        
        ### Reasoning Steps:
        1. [First reasoning step with evidence reference]
        2. [Second reasoning step...]
        
        ### Quoted Evidence:
        ##begin_quote##
        [Relevant context sentences]
        ##end_quote##
        
        ### Type-Specific Structure:
        {type_specific_guidelines}
        
        ### Final Answer:
        <ANSWER>: [Complete, detailed answer in English]
        
        ## CRITICAL RULES:
        1. **Answer Verification:** Cross-check that your final answer addresses the exact question
        2. **Terminology Consistency:** Use EXACT product/feature names from context
        3. **No Hallucination:** Never add information beyond the provided context
        4. **URL Inclusion:** Include URLs ONLY if they appear in quoted context
        5. **Language:** All reasoning and answer in English (Japanese only if in quotes)

        ## TYPE-SPECIFIC GUIDELINES:
        {{
        "factual": "Present clear, concise information. Structure: 1) Direct answer, 2) Supporting specifications, 3) Additional relevant facts from context.",
        "conceptual": "Explain the underlying principles. Structure: 1) Core concept, 2) How it works/why it matters, 3) Implications/application scenarios.",
        "procedural": "Provide actionable guidance. Structure: 1) Step sequence, 2) Key considerations, 3) Expected outcomes/troubleshooting tips."
        }}
    """
}


# cot_ans_prompt_templates = {
#     "gpt": """
#         Question: {question}
#         Context: {context}

#         Answer this question using the information given in the context above.
        
#         Instructions:
#         - All the response should be in English but maintain full descriptions.
#         - Provide step-by-step reasoning on how to answer the question.
#         - Explain which parts of the context are meaningful and why.
#         - Copy paste the relevant sentences from the context in ##begin_quote## and ##end_quote##.
#         - Provide a summary of how you reached your answer.
#         - End your response with the final answer in the form <ANSWER>: $answer.
#         - You MUST begin your final answer with the tag "<ANSWER>:".

#         ## CRITICAL RULES FROM GENERATE_PROMPT:
#             1. **Source of Truth**: Use ONLY the quoted context above. Never hallucinate.
#             2. **Product Names**: Use EXACT names from context (e.g., if context says "SuperK EVO", don't say just "SuperK").
#             3. **URL Handling**: Include URLs ONLY if they appear in the quoted context above.
#             4. **Structure**: Follow appropriate format based on question type (details below).

#         Output structure:
#         1. Brief factual explanation (1–2 short paragraphs)
#         2. Quoted specification evidence (if applicable)
#         3. Final in depth answer  

#         Response format:
#         -  **For Product Recommendations (e.g., "What do you have for spectroscopy?"):**
#         *   Present relevant products in a clear list or table format.
#         *   For **each product**, include: **Product Name**, **URL** (if in context), and a **technical descriptive, benefit-focused description**.
#         *   Conclude by guiding the user to the next step, using the exact contact form URL: `https://www.sevensix.co.jp/contact/`.
#         *   Example ending: "Please fill out the contact form so our team can provide personalized advice. Is there anything else you'd like to know about these or other solutions?"
#         - **For Product Details & Features (e.g., "Tell me about the SuperK FIANIUM", "what is [product-name]","tell me about [product-name]"):**
#         *   Provide a comprehensive, structured overview. Aim for depth when context allows.
#         *   **Standard Structure:**
#             1.  **Product Name:** Clearly state it.
#             2.  **Product Page:** URL (if in context).
#             3.  **Overview Description:** A 3-7 sentence summary of its primary purpose and value. Explain the fundamental working principle or technology behind the product,Use precise technical terminology.
#             4.  **Detailed Specifications/Features:** Use bullet points for clarity. Include key specs (e.g., spectral range, power, repetition rate), operational benefits (e.g., maintenance-free, lifetime), and available models.
#             5.  **Primary Applications:** List the main use cases (e.g., Spectroscopy, Biomedical Imaging).
#             6.  **Value Proposition / "Why Choose This Product?":** Add a brief paragraph explaining its key advantages, reliability, and ideal use-case scenarios. This section is crucial for sales persuasion.
#         - **For Comparative or Deep Technical Queries:**
#         *   Where context provides data for multiple products or in-depth technical notes, synthesize this into a comparative analysis, pros/cons, or a focused deep-dive on a specific feature.
#         *   Maintain a professional tone while making the information accessible.
                      
#     """
#     }

generic_ans_prompt_templates = {
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
        

        Final Answer format:
        1. Brief factual explanation (1–2 short paragraphs)
        2. Quoted specification evidence (if applicable)
        3. Final in depth answer  

       
                      
    """
    }

# build_cot_answers={
#     "gpt": """## **Product Information Assistant** ##

#         **Question:** {question}

#         **Relevant Context (Product Information):**
#         {context}

#         ---

#         ## **Instructions for Answer Generation:**

#         1. **Comprehension Phase:**
#         - First, understand what the user is asking about. What specific product feature, specification, or information are they seeking?
#         - Identify key entities: product names, models, features, measurements, comparisons, or specific attributes mentioned.

#         2. **Context Analysis Phase:**
#         - Systematically go through each part of the provided context.
#         - For each relevant piece of information found:
#             - **Quote it** between ##begin_quote## and ##end_quote##
#             - **Explain why** this information is relevant to answering the question
#             - **Note any contradictions** or complementary information across different context segments

#         3. **Reasoning Phase:**
#         - Connect the dots between different pieces of relevant information
#         - If specifications or features are compared, explain the comparison logic
#         - If the question requires inference (e.g., "which is better for X use case"), explain the criteria for evaluation
#         - Address any gaps: if the context doesn't fully answer the question, acknowledge what's missing

#         4. **Answer Synthesis Phase:**
#         - Synthesize a clear, concise answer based ONLY on the provided context
#         - If applicable, structure the answer with:
#             - Key specifications/features
#             - Comparisons (if requested)
#             - Recommendations (if supported by context)
#         - **DO NOT** add information not present in the context

#         5. **Verification Phase:**
#         - Verify that your final answer directly addresses the original question
#         - Ensure no contradictory information from the context has been ignored

#         ---

#         ## **Required Output Format:**

#         **Reasoning Process:**
#         [Your step-by-step reasoning here, following phases 1-4 above]

#         **Relevant Quotes from Context:**
#         ##begin_quote##
#         [Exact relevant text from context]
#         ##end_quote##

#         [Repeat for each relevant quote with explanation]

#         **Final Answer Summary:**
#         [Brief summary of how you reached the conclusion]

#         <ANSWER>: [Your final, concise answer to the question. If the answer requires listing items, use bullet points. If comparing, use clear comparison format.]

#         ---

#         ## **Important Rules:**
#         - Base your answer SOLELY on the provided context. Do not use external knowledge.
#         - If the context doesn't contain enough information to answer fully, state this in your reasoning and answer only with what's available.
#         - For technical specifications: be precise with numbers, units, and measurements.
#         - For product comparisons: be objective and reference specific context points.
#         - All responses must be in JAPANESE."""
# }




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


# build_qa_messages = {
#     "gpt": lambda chunk, x: [
#         {
#             "role": "system",
#             "content": f"""You are an expert question designer for training retrieval-augmented AI systems. Your task is to create {x} high-quality, challenging questions based EXCLUSIVELY on the provided product documentation chunk.

#             **CONTEXT:** You are creating training data for RAFT (Retrieval-Augmented Fine-Tuning) where the model must learn to identify which information in the knowledge base can answer specific questions.

#             **INPUT:** A chunk of product documentation about SevenSix products.

#             **TASK:** Generate {x} diverse, challenging questions that:
#             1. **Vary in Difficulty:**
#             - 30% Simple fact retrieval (directly stated in text)
#             - 40% Moderate inference (combine 2-3 facts from text)
#             - 30% Complex reasoning (require understanding relationships/context)

#             2. **Focus on Real User Scenarios:**
#             - Product selection/configuration questions
#             - Technical specification clarification
#             - Use-case suitability assessment
#             - Comparison between features/products mentioned
#             - Problem-solving/troubleshooting scenarios

#             3. **Test Knowledge Boundaries:**
#             - Some questions should require ONLY the current chunk
#             - Some should imply need for additional context (but don't state this)
#             - Include questions with ambiguous phrasing that requires careful reading

#             4. **Question Types to Include:**
#             - “What laser light sources cover the 400–2400 nm wavelength range?”
#             - "What are the key differences between [Product A] and [Product B] mentioned here?"
#             - "If I need [specific requirement], which product from this text would you recommend and why?"
#             - "How would I configure [product] for [specific application] based on these specs?"
#             - "What limitations or constraints should I consider when using [product] for [purpose]?"
#             - "Tell me about [product]"
#             - “Can you tell me about the [product]?”
            
#             **INSTRUCTION:** 
#             - "Don't mention document reference in the question"
#             - "Maintain the document language prefered JAPANESE"

#             **FORMAT:** Return only the questions, one per line, without numbering or explanations."""
#                     },
#                     {"role": "user", "content": f"Product Documentation Chunk:\n\n{chunk}"}
#                 ]
#         }

