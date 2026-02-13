### QIMG-QTXT PROMPTS : 

def get_qimg_qtxt_sentiment_prompt(query_image, query_caption):
    sentiment = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "You are an AI assistant skilled in analyzing and comparing the sentiment of text and images."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": query_image},
                    {
                        "type": "text",
                        "text": f"""
                        Headline/Text: '{query_caption}'
                        Image: [Provided]

                        Analyze the sentiment conveyed by the text and the image.

                        1. Assess Text Sentiment 
                        - Determine the emotional tone of the text (e.g., positive, negative, neutral, specific emotion) based on its wording and context.

                        2. Assess Image Sentiment:
                        - Determine the emotional tone conveyed by the image (e.g., happy, sad, tense, calm, neutral) based on visual cues.

                        3. Compare & Classify:
                        - Compare the sentiments. Output ONE classification:
                            - `Sentiment Aligned`: Text and image share a similar emotional tone.
                            - `Sentiment Mismatch`: Text and image have conflicting emotional tones.
                            - `Sentiment Ambiguous/Neutral`: Sentiment is unclear, neutral, or subjective in one or both.

                        4. Reasoning: 
                        - Briefly explain your classification, referencing the key sentiment indicators in both the text and the image.
                        DO NOT HALLUCINATE OR MAKE ASSUMPTIONS.
                        Output: 
                        - Classification: [Your Classification]  
                        - Reasoning: [Your brief explanation]  
                        """
                    }
                ]
            }
        ]
    return sentiment

def get_qimg_qtxt_entities_prompt(query_image, query_caption):
    entities = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are an AI assistant skilled in analyzing text and images for entity consistency (people, places, organizations)."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": query_image},
                {
                    "type": "text",
                    "text": f"""
                    Headline/Text: '{query_caption}'
                    Image: [Provided]

                    Analyze the consistency of named entities between the text and the image.

                    1. Identify Entities in Text:
                    - List the key named entities (specific people, organizations, well-known places) mentioned in the text.

                    2. Analyze Image for Entities:
                    - Examine the image for visual representations of these specific entities.

                    3. Compare & Classify:
                    - Compare the text entities with the visual content. Output ONE classification:
                        - `Entities Aligned`: Key entities mentioned in the text are visually identifiable in the image.
                        - `Entities Mismatch`: Key entities mentioned are clearly absent, or different recognizable entities are shown.
                        - `Entities Ambiguous/Unverifiable`: The image is too generic, unclear, or lacks visual details to confirm or deny the presence of the specific entities mentioned. A definite conclusion cannot be reached based on the visual evidence.

                    4. Reasoning:
                    - Briefly explain your classification. Mention the key entities checked and why the image aligns, mismatches, or is unverifiable regarding their presence.
                    DO NOT HALLUCINATE OR MAKE ASSUMPTIONS.
                    Output:
                    - Classification:[Your Classification]
                    - Reasoning: [Your brief explanation]
                    """
                }
            ]
        }
    ]
    return entities

def get_qimg_qtxt_event_prompt(query_image, query_caption):
    event = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are an AI assistant skilled in analyzing text and images for event/action consistency."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": query_image},
                {
                    "type": "text",
                    "text": f"""
                    Headline/Text: '{query_caption}'
                    Image: [Provided]

                    Analyze whether the image visually depicts the specific event or action described in the text.

                    1. Identify Event/Action in Text:
                    - Describe the main event or action reported in the text.

                    2. Analyze Image Content:
                    - Examine what event, action, or scene is visually shown in the image.

                    3. Compare & Classify:
                    - Compare the described event/action with the depicted scene. Output ONE classification:
                        - `Event/Action Aligned`: The image clearly shows the specific event or action described in the text.
                        - `Event/Action Mismatch`: The image clearly shows a different event/action, or a scene unrelated to the text's description.
                        - `Event/Action Ambiguous/Unverifiable`: The image is too generic (e.g., stock photo, portrait unrelated to action), abstract, or unclear to confirm or deny if it depicts the specific event/action mentioned. A definite conclusion cannot be reached.

                    4. Reasoning:
                    - Briefly explain your classification. Describe the event from the text and what the image shows, explaining why they align, mismatch, or why verification isn't possible.
                    DO NOT HALLUCINATE OR MAKE ASSUMPTIONS.
                    Output:
                    - Classification:[Your Classification]
                    - Reasoning: [Your brief explanation]
                    """
                }
            ]
        }
    ]
    return event

def get_qimg_qtxt_colab_prompt(sentiment, entities, event):
    # colab = [
    #     {"role": "system", "content": [{"type": "text", "text": "You are a helpful assistant."}]},
    #     {"role": "user", "content": [
    #         {"type": "text", "text": f"Here are three analyses:\n"
    #                                 f"- sentiment match/mismatch Analysis 1: {sentiment}\n"
    #                                 f"- entities match/mismatch Analysis 2: {entities}\n"
    #                                 f"- event/action match/mismatch Analysis 3: {event}\n\n"
    #                                 # "Based on these 3 different type of analysis on the given image and caption for a particular news sample, Give output as True Or Fake and also a confidence score for the judgment.\n"
    #                                 "Using these 3 different type of analysis on the given image and caption for a particular news sample, Give output as True Or Fake and also a confidence score for the judgment.\n"
    #                                 "If you think the news sample is fake, Output:\n FAKE\n"
    #                                 "Else if you think the news sample is True, Output:\n TRUE"}
    #     ]}
    # ]
    # return colab
    colab = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "You are a strict assistant for fake news detection based ONLY on the provided sentiment, entity, and event/action analyses. "
                        "Do not use any background knowledge or assumptions beyond the input."
                    )
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Here are three analyses:\n"
                        f"- Sentiment match/mismatch Analysis 1: {sentiment}\n"
                        f"- Entities match/mismatch Analysis 2: {entities}\n"
                        f"- Event/action match/mismatch Analysis 3: {event}\n\n"
                        "Using ONLY these three analyses, determine if the news is FAKE or TRUE.\n\n"
                        "**Rules for Decision:**\n"
                        "- If two or more analyses show mismatch → Label: FAKE\n"
                        "- If all three analyses show match → Label: TRUE\n"
                        "- If only one analysis shows mismatch → Label: TRUE\n\n"
                        "**Confidence Level:**\n"
                        "- High → all analyses agree (either all match or all mismatch)\n"
                        "- Medium → two agree, one differs\n"
                        "- Low → when uncertain, but still follow the rule strictly\n\n"
                        "**Format of Output:**\n"
                        "Label: TRUE or FAKE\n"
                        "Confidence: High / Medium / Low\n"
                        "Reasoning: [A brief explanation referring ONLY to the match/mismatch outcomes above]\n\n"
                        "Make sure your reasoning is consistent with the label and confidence."
                    )
                }
            ]
        }
    ]

    return colab

### text-text prompts 


def get_claims(query_caption):
    prompt = f"""Given the input content below, please extract distinct key claims. Each extracted claim must adhere to the following strict guidelines:

1.  **Verifiability:** Each claim must capture  factual statements that can be verified as true or false. Exclude subjective interpretations, opinions, or unverifiable statements.
    * **Incorrect Example:** From "Addressing emerging market challenges will require comprehensive strategies that consider economic stability, food security, and public health," claims like "Addressing emerging market challenges requires comprehensive strategies" are incorrect because they are opinions, not verifiable facts.

2.  **Entailment and Completeness:** Each claim must be fully supported and directly entailed by the source text, capturing all verifiable content without omission. Do not make inferences or generalizations not explicitly stated.
    * **Incorrect Example 1 (Incomplete):** From "Argentina’s rampant inflation, with monthly rates reaching as high as 25.5%, has made many goods unobtainable and plunged the value of the currency, causing severe economic hardship. Some experts estimate that the annual inflation rate could potentially double to 300%, while others predict even higher rates."
        * Claims like "Argentina has a monthly inflation rate as high as 25.5%," "Argentina’s inflation has made many goods unobtainable," "Argentina’s currency value has plunged," and "Some experts estimate Argentina’s annual inflation rate could reach 300%" are incomplete because they omit "causing severe economic hardship" and "others predict even higher rates," and the third claim omits that inflation caused the currency depreciation.
    * **Incorrect Example 2 (Inaccurate):** From "The U.N. found that the resulting contaminated water caused many residents to fall ill, highlighting the need for improved water management."
        * The claim "The U.N. found contaminated water in Derna, Libya" is inaccurate because the U.N. found the link between contaminated water and illness, not the contaminated water itself. Also, "Contaminated water in Derna, Libya, caused many residents to fall ill" shifts the meaning from a viewpoint of a specific entity (the U.N.) to a general assertion.

3.  **Self-Contained and Contextual:** Each claim must be understandable on its own, without requiring additional context from the original input. Ensure all necessary entities and references are clearly defined within the claim. Avoid using pronouns or vague terms without their clear antecedents.
    * **Incorrect Example:** From "Countries like Afghanistan and Sudan have experienced similar challenges to those of Libya."
        * Claims like "Afghanistan has experienced challenges similar to those in Libya" and "Sudan has experienced challenges similar to those in Libya" are incorrect because "those" is not defined and the claim cannot be understood without external context.

4.  **Ambiguity Handling:** If a sentence or phrase has multiple, mutually exclusive interpretations and the context does not clearly resolve the ambiguity, you must explicitly flag the ambiguity within the claim or provide both interpretations as separate claims with a clear note about the ambiguity. *For this task, if ambiguity cannot be resolved, state the ambiguous part clearly within the claim.*

Input content: {query_caption}

Please output with the following JSON format. Each 'claim' field should be a single, self-contained, and verifiable statement. If a claim contains unresolved ambiguity, clearly indicate this within the claim text.
{{"key_claims": [{{"claim": "XXX"}}, {{"claim": "YYY"}}, ...]}}

Please output now:"""

    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        }
    ]
    return messages

def get_response_txttxt(search_result, claim):
    prompt_text = f"""
You are a **factual consistency evaluator**. Your task is to determine whether two sentences describe the **same real-world facts**, or if they are unrelated or explicitly contradictory. If a reputable fact-checking source debunks a claim, mark it as misinformation.

---

### 🔢 Scoring Rules (Use only these values):

- `1` → The sentences describe the **same real-world situation**, with perfect alignment in **entities, actions, timeframes, and context**. No additions or omissions.
- `0` → The sentences refer to **different facts**, even if in the same topic/domain (e.g., both about politics or infrastructure).
- `-1` → Only assign `-1` if Sentence B is from a **reputable fact-checking organization** (e.g., Alt News, Boom Live, Factly, India Today Fact Check) and **explicitly debunks or proves false the exact claim** made in Sentence A.

---

### 📌 Evaluation Criteria:

1. Focus **only on factual content**. Ignore emotional tone, wording, or opinions.
2. **Do not infer or assume** facts not explicitly stated in either sentence.
3. **Only assign 1** if Sentence B supports the **exact same facts** as Sentence A. This includes:
   - Same named **entities**
   - Same **actions/events**
   - Same **location**, **timeframe**, or **context**
   - No **missing or extra** factual claims
4. Assign **0** if:
   - The two sentences mention different events or topics.
   - One sentence is **too vague or incomplete** to verify factual match.
   - The facts are only **loosely related** but not referring to the same real-world event.
5. Assign **-1 only** if:
   - Sentence B is from a fact-checking website, and
   - It **explicitly states that the claim in Sentence A is false**, and
   - The claim being debunked is **clearly the same** as the one in Sentence A.

---

### 🏷️ Special Flags:

- If Sentence B is from a **fact-checking website** and is used for the `-1` score, also set:
  `"FactCheckVerdictUsed": true`
- If Sentence B is from a **trusted news source** (e.g., The Hindu, Times of India, Indian Express, Hindustan Times) and clearly supports the same claim, set:
  `"TrustedNewsSourceVerified": true`

---

### Input:

**Sentence A (Claim)**:  
{claim}

**Sentence B (Search Result)**:  
{search_result}

---

### Output Format (JSON only):

```json
{{
  "FactualAlignmentScore": <score: -1, 0, or 1>,
  "rationale": "<strict justification based ONLY on stated facts>",
  "FactCheckVerdictUsed": <true or false>,
  "TrustedNewsSourceVerified": <true or false>
}}"""

    messages = [
        {
            "role": "system",
            "content": [{
                "type": "text",
                "text": "You are a factual content alignment evaluator. Given two sentences, assess how much of the same objective, factual information they convey, regardless of emotional tone, opinion, or framing."
            }]
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt_text}]
        }
    ]
    return messages
### QUERY IMAGE - EVIDENCE IMAGE SECTION 

def get_img_img_sentiment(query_image, evidence_image): 
    sentiment_prompt = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "You are an AI assistant skilled in analyzing and comparing the sentiment of visual content in images."
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {"type": "image", "image": query_image},
            {"type": "image", "image": evidence_image},
            {
                "type": "text",
                "text": f"""
                You are given two images:

                - Image 1: [Query Image]
                - Image 2: [Evidence Image]

                Analyze the emotional or expressive tone conveyed by each image and compare them.

                1. Assess Sentiment of Each Image:
                - Determine the emotional tone conveyed by each image (e.g., happy, sad, tense, calm, neutral) based on visual cues such as expressions, scene context, composition, and colors.

                2. Compare & Classify:
                - Compare the sentiments. Output ONE classification:
                    - `Sentiment Aligned`: Both images convey a similar emotional tone.
                    - `Sentiment Mismatch`: The images convey conflicting emotional tones.
                    - `Sentiment Ambiguous/Neutral`: Sentiment is unclear, neutral, or subjective in one or both.

                3. Reasoning:
                - Briefly explain your classification, referencing key visual sentiment indicators observed in both images.

                DO NOT HALLUCINATE OR MAKE ASSUMPTIONS.
                Output:
                - Classification: [Your Classification]  
                - Reasoning: [Your brief explanation]  
                """
                            }
                        ]
                    }
                ]
    return sentiment_prompt

def get_img_img_entities(query_image, evidence_image) : 
    entities_prompt = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "You are an AI assistant skilled in analyzing images for entity consistency (people, places, organizations)."
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {"type": "image", "image": query_image},
            {"type": "image", "image": evidence_image},
            {
                "type": "text",
                "text": f"""
                You are given two images:

                - Image 1: [Query Image]  
                - Image 2: [Evidence Image]

                Analyze the consistency of named entities (people, places, organizations) visually represented in both images.

                1. Identify Entities in Image 1:  
                - Describe the key named entities (specific people, recognizable places, organizations) you can identify in Image 1.

                2. Identify Entities in Image 2:  
                - Describe the key named entities you can identify in Image 2.

                3. Compare & Classify:  
                - Compare the entities found in both images. Output ONE classification:  
                    - `Entities Aligned`: The key entities visible in Image 1 are also clearly identifiable in Image 2.  
                    - `Entities Mismatch`: The entities visible in Image 2 are clearly absent or different from those in Image 1.  
                    - `Entities Ambiguous/Unverifiable`: One or both images lack sufficient detail or are too generic to confirm entity consistency.

                4. Reasoning:  
                - Briefly explain your classification, mentioning the key entities checked and why you determined alignment, mismatch, or ambiguity.  
                DO NOT HALLUCINATE OR MAKE ASSUMPTIONS.  

                Output:  
                - Classification: [Your Classification]  
                - Reasoning: [Your brief explanation]  
                """
                            }
                        ]
                    }
                ]
    return entities_prompt

def get_img_img_events(query_image, evidence_image) : 
    entities_prompt = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "You are an AI assistant skilled in analyzing images for event/action consistency."
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {"type": "image", "image": query_image},
            {"type": "image", "image": evidence_image},
            {
                "type": "text",
                "text": f"""
                You are given two images:

                - Image 1: [Query Image]  
                - Image 2: [Evidence Image]

                Analyze whether both images visually depict the same specific event or action.

                1. Identify Event/Action in Image 1:  
                - Describe the main event, action, or scene visually shown in Image 1.

                2. Identify Event/Action in Image 2:  
                - Describe the main event, action, or scene visually shown in Image 2.

                3. Compare & Classify:  
                - Compare the events/actions depicted in both images. Output ONE classification:  
                    - `Event/Action Aligned`: Both images clearly depict the same specific event or action.  
                    - `Event/Action Mismatch`: The images depict different events, actions, or unrelated scenes.  
                    - `Event/Action Ambiguous/Unverifiable`: One or both images are too generic, abstract, or unclear to confirm if they depict the same event or action.

                4. Reasoning:  
                - Briefly explain your classification, describing the events or actions visible in both images and why you determined alignment, mismatch, or ambiguity.  
                DO NOT HALLUCINATE OR MAKE ASSUMPTIONS.  

                Output:  
                - Classification: [Your Classification]  
                - Reasoning: [Your brief explanation]  
                """
                            }
                        ]
                    }
                ]
    return entities_prompt

def get_img_img_colab_prompt(sentiment, entities, event) : 
    colab_prompt = [
        {"role": "system", "content": [{"type": "text", "text": "You are a helpful assistant."}]},
        {"role": "user", "content": [
            {"type": "text", "text": f"Here are three analyses:\n"
                                    f"- sentiment match/mismatch Analysis 1: {sentiment}\n"
                                    f"- entities match/mismatch Analysis 2: {entities}\n"
                                    f"- event/action match/mismatch Analysis 4: {event}\n\n"
                                    "Based on these 3 different type of analysis on the given image and its evidence image for a particular news sample, Give output as True Or Fake and also a confidence score for the judgment.\n"
                                    "If you think the news sample is fake with evidence image not supporting the given sample then  , Output:\n FAKE\n"
                                    "Else if you think the news sample is True  with evidence image supporting the given sample then , Output:\n TRUE"}
        ]}]
    return colab_prompt

def get_qimg_qtxt_unified_prompt(query_image, query_caption):
    unified_prompt = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are a multi-task AI assistant skilled in analyzing and comparing the relationship between images and text across different dimensions such as sentiment, named entities, and actions/events."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": query_image},
                {
                    "type": "text",
                    "text": f"""
Given the following news sample:

Headline/Text: '{query_caption}'
Image: [Provided]

Please perform the following **4-step analysis** carefully and independently.

---

### STEP 1: Sentiment Alignment

1. **Text Sentiment**: Determine the emotional tone of the text (e.g., positive, negative, neutral, or specific emotions like anger, hope, sadness).
2. **Image Sentiment**: Assess the emotional tone conveyed by the image using visual cues.
3. **Comparison**: Output ONE classification:
    - `Sentiment Aligned`: Text and image share a similar emotional tone.
    - `Sentiment Mismatch`: Text and image have conflicting emotional tones.
    - `Sentiment Ambiguous/Neutral`: Sentiment is unclear, neutral, or subjective in one or both.

**Output 1:**
- Classification: [Your Classification]  
- Reasoning: [Your brief explanation]

---

### STEP 2: Entity Consistency

1. **Text Entities**: List any specific named people, organizations, or well-known locations mentioned in the text.
2. **Image Entities**: Identify whether those entities (or their visual representation) appear in the image.
3. **Comparison**: Output ONE classification:
    - `Entities Aligned`
    - `Entities Mismatch`
    - `Entities Ambiguous/Unverifiable`

**Output 2:**
- Classification: [Your Classification]  
- Reasoning: [Your brief explanation]

---

### STEP 3: Event/Action Consistency

1. **Text Event/Action**: Identify the main event or action described in the text.
2. **Image Depiction**: Determine what event or action (if any) is visually shown in the image.
3. **Comparison**: Output ONE classification:
    - `Event/Action Aligned`
    - `Event/Action Mismatch`
    - `Event/Action Ambiguous/Unverifiable`

**Output 3:**
- Classification: [Your Classification]  
- Reasoning: [Your brief explanation]

---

### STEP 4: Final Judgment

Using the three analyses above, determine whether the image and text are consistent and truthful in their pairing.

**Final Output 4:**
- Judgment: TRUE or FAKE  
- Brief Reasoning: Reference which analyses most contributed to your judgment and why.
                    """
                }
            ]
        }
    ]
    return unified_prompt

def get_img_img_unified_prompt(query_image, evidence_image):
    img_img_combined_prompt = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "You are a multi-task AI assistant skilled in analyzing and comparing the relationship between two images across different dimensions such as sentiment, named entities, and actions/events."
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {"type": "image", "image": query_image},
            {"type": "image", "image": evidence_image},
            {
                "type": "text",
                "text": f"""
You are given two images related to a news sample:

- **Image 1**: [Query Image]  
- **Image 2**: [Evidence Image]

Please perform the following **4-step analysis** carefully and independently.

---

### STEP 1: Sentiment Alignment

1. **Image 1 Sentiment**: Determine the emotional tone conveyed by the query image (e.g., positive, negative, neutral, or emotions like anger, hope, sadness).
2. **Image 2 Sentiment**: Assess the emotional tone of the evidence image using visual cues such as expressions, composition, and context.
3. **Comparison**: Output ONE classification:
    - `Sentiment Aligned`: Both images convey a similar emotional tone.
    - `Sentiment Mismatch`: The images convey conflicting emotional tones.
    - `Sentiment Ambiguous/Neutral`: Sentiment is unclear, neutral, or subjective in one or both images.

**Output 1:**
- Classification: [Your Classification]  
- Reasoning: [Your brief explanation]

---

### STEP 2: Entity Consistency

1. **Entities in Image 1**: Identify any named or visually recognizable people, organizations, or locations in the query image.
2. **Entities in Image 2**: Identify whether those same entities are also present in the evidence image.
3. **Comparison**: Output ONE classification:
    - `Entities Aligned`
    - `Entities Mismatch`
    - `Entities Ambiguous/Unverifiable`

**Output 2:**
- Classification: [Your Classification]  
- Reasoning: [Your brief explanation]

---

### STEP 3: Event/Action Consistency

1. **Event/Action in Image 1**: Describe the main event, action, or scene depicted in the query image.
2. **Event/Action in Image 2**: Describe the event or action shown in the evidence image.
3. **Comparison**: Output ONE classification:
    - `Event/Action Aligned`
    - `Event/Action Mismatch`
    - `Event/Action Ambiguous/Unverifiable`

**Output 3:**
- Classification: [Your Classification]  
- Reasoning: [Your brief explanation]

---

### STEP 4: Final Judgment

Using the three analyses above, determine whether the **query image and evidence image** together appear to support a truthful claim or if the pairing is misleading or manipulated.

**Final Output 4:**
- Judgment: TRUE or FAKE  
- Brief Reasoning: Reference which analyses most contributed to your judgment and why.
"""
            }
        ]
    }
]    
    return img_img_combined_prompt

### COLLABORATOR PROMPT
def unified_prompt_v2(
    query_image,
    query_text,
    img_txt_response: str,
    img_img_response: str,
    claim_verification_str: str,
):
    """
    Constructs a unified prompt that merges image-text analysis, image-image analysis,
    and claim verification to produce a final classification.

    Args:
        query_image: Image input
        query_text (str): Text accompanying the image (headline/caption)
        img_txt_response (str): Output from image-text alignment prompt
        img_img_response (str): Output from image-image alignment prompt
        claim_verification_str (str): Summary of web-based claim verification
        rationales (str): Summary of the List of rationale strings from individual web search comparisons

    Returns:
        list: Prompt for final decision making, formatted for a multimodal assistant
    """
    
    return [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "You are a multimodal verification assistant. Your role is to analyze and reason over multiple sources "
                        "of evidence related to a news post (an image-text pair) to determine its authenticity."
                    )
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": query_image},
                {
                    "type": "text",
                    "text": f"""
You are given a news post containing the following:

- **Image**: [Shown above]
- **Text**: "{query_text}"

Your task is to integrate the three evidence sources below and make a final judgment on whether the news is **REAL**, **FAKE**.

---

### 🧩 Evidence 1: Image-Text Consistency Analysis (Query Image vs Query Text)

{img_txt_response.strip()}

---

### 🧩 Evidence 2: Image-Image Consistency Analysis (Query Image vs Retrieved Evidence Image)

{img_img_response.strip()}

---

### 🧩 Evidence 3: Claim Verification via Web Search

**Summary Score**:  
{claim_verification_str.strip()}
score classification Logic:
if score is High Support score(20.0) shows strong SUPPORT so TRUE,
if score is Low Support score(-20.0) shows Low SUPPORT so False.

---

### 📝 Instructions

Please analyze all the above evidence carefully and do the following:

1. **Give high weightage to Evidence 3 (Web-based claim verification)**, which is a score derived from factual comparisons between the query text and multiple real news headlines to judge whether the textual claims are supported, refuted, or unverifiable.
2. Consider **Evidence 2 (Image-Image)** as moderately important, to check if the visual context supports or contradicts the web based claim verification result.
3. Use **Evidence 1 (Image-Text)** for minor cues based on alignment of the caption and image.
4. Give a **final classification** and rate your confidence: `Low`, `Medium`, or `High`.
5. Provide analysis of Evidence 1, 2, 3 in detail and how they contribute to the final classification.
6. Provide **balanced reasoning**: briefly state arguments *FOR* and *AGAINST* the Final Classification based on all evidence, with emphasis on the stronger ones.
---


### 🔚 Final Output Format

**Final Classification**: [REAL / FAKE]  
**Detailed Reasoning**:  
[Your comprehensive reasoning that discusses all three evidence types and how they contributed to your final decision.]

Now begin your reasoning.
"""
                }
            ]
        }
    ]



#### RATIONAL SUMMARY 

def rationale_summary_prompt(rationales: list[str], query_caption: str) -> str:
    joined_rationales = "\n".join([f"- {r.strip()}" for r in rationales])
    return f"""You are given a news query caption (referred to as Sentence A) and a list of rationales that compare it with multiple evidence captions (referred to as Sentence B). Each rationale evaluates whether the information in an evidence caption supports, contradicts, or is unrelated to Sentence A (which is the original news headline/Query Caption).

### Sentence A (Query Caption):
"{query_caption}"

### Rationales (comparisons between Sentence A and various Sentence Bs):
{joined_rationales}

### Task:
Analyze the rationales and identify which Sentence Bs are **factually aligned**, **contradictory**, or **unrelated** to Sentence A. Group them accordingly and summarize the general patterns of factual agreement and disagreement.

Focus on:
- Common themes or facts consistently supported across multiple Sentence Bs
- Contradictions or mismatches (especially factual or contextual)
- Any uncertainties or weak alignments that need caution

Provide a concise 2–4 sentence summary explaining the extent to which the evidence supports or disputes Sentence A.

### Summary:"""



if __name__ == "__main__":
    # Example usage

    query_image = "/data/image.jpg"  # Replace with actual image path
    query_caption = "This is a sample caption for the news article."

    sentiment_prompt = get_qimg_qtxt_sentiment_prompt(query_image, query_caption)
    entities_prompt = get_qimg_qtxt_entities_prompt(query_image, query_caption)
    event_prompt = get_qimg_qtxt_event_prompt(query_image, query_caption)
    colab_prompt = get_qimg_qtxt_colab_prompt(sentiment_prompt, entities_prompt, event_prompt)

