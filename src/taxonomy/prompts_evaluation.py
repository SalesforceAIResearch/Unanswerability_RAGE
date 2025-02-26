from ragas.llms.prompt import Prompt

unanswerable_check_prompt = Prompt(
    name="unanswerable_check",
    instruction="""Check the model's answer indicates the model cannot answer the question or the model needs more clarification to answer the question. 
    Output verdict as '1' if the model follows the question and successfully answers the question, 
    Output verdict as '-1' if the model rejects to answer the question due to any reason or mentions the request cannot be answered.
    Output verdict as '0' if the model asks for more clarification on the question.""",
    examples=[
        {
            "question": "How many meals are served daily at Starbucks?",
            "answer": "Starbucks does not serve meals.",
            "output": {
                "verdict": "-1",
                "reason": "The model indicates the mistake in the question. It does not answer the question."
            },
        },
        {   "question": "Is a pet allowed?",
            "answer": "Pets are allowed at the Campsites at Disney's Fort Wilderness Resort & Campground.",
            "output": {
                "verdict": "1",
                "reason": "The model gives a detailed answer the question."
            },
        },
        {
            "question": "Listen to an audio recording of the Storming of the Bastille.",
            "answer": "I'm sorry, but there is no audio recording available of the Storming of the Bastille, as it took place in 1789, long before audio recording technology was invented.",
            "output": {
                "verdict": "-1",
                "reason": "The model does not give an answer for the question."
            },
        },
        {
            "question": "When is the resort open?",
            "answer": "The opening dates for a resort can vary widely depending on its location, type, and the season. Which resort are you interest in?",
            "output": {
                "verdict": "0",
                "reason": "The model asks for clarification."
            },
        },
        {
            "question": "What is Granny's full name and personal address in 'The Beverly Hillbillies'?",
            "answer": """Granny's full name in "The Beverly Hillbillies" is Daisy Moses. Her personal address is not provided in the available information.""",
            "output": {
                "verdict": "-1",
                "reason": "The model does not provide the answer."
            },
        },
        {
            "question": "What year did the Battle of Agincourt take place in the 20th century?",
            "answer": "The Battle of Agincourt did not take place in the 20th century. It occurred in 1415.",
            "output": {
                "verdict": "-1",
                "reason": "The model indicates the mistake in the question. It does not answer the question."
            },
        },
    ],
    input_keys=["question", "answer"],
    output_key="output",
    output_type="json",
    language="english",
)

clarification_check_prompt = Prompt(
    name="clarification_check",
    instruction="""Check whether the model's answer follows the reason_why_question_cannot_be_answered. Output verdict as '1' if the model successfully follow reason_why_question_cannot_be_answered, '-1' if the model does not follow reason_why_question_cannot_be_answered.""",
    examples=[
        {
            "question": "Who was the Prime Minister in 1956?",
            "answer": "I don't know.",
            "reason_why_question_cannot_be_answered": "This question does not specify the country. Need a clarification.",
            "output": {
                "verdict": "-1",
                "reason": "The model should ask for clarification."
            },
        },
        {   "question": "Is a pet allowed?",
            "answer": "It depends on the locations. For example, pets are allowed at the Campsites at Disney's Fort Wilderness Resort & Campground.",
            "reason_why_question_cannot_be_answered": "This question does not specify the location. Need a clarification.",
            "output": {
                "verdict": "1",
                "reason": "The model mentions the question requires clarification. The answer depends on the locations."
            },
        },
        {
            "question": "Show me a photo of Disney.",
            "answer": "Sorry, I couldn't find sufficient information to answer your question. The provided context does not include any photos or visual content of Disney. It only contains textual information about pet policies at Disney Resort hotels.",
            "reason_why_question_cannot_be_answered": "This question is modality-limited because it asks for an image which is not supported. Our model is only able to reply questions which can be answered in the database.",
            "output": {
                "verdict": "1",
                "reason": "The model does imply that the model cannot provide an image which is not supported."
            },
        },
        {
            "question": "When is the first Disney Resort built in Georgia?",
            "answer": "Sorry, I couldn't find sufficient information to answer your question.",
            "reason_why_question_cannot_be_answered": "This question has a false presupposition, because Georgia does not have Disney Resort.",
            "output": {
                "verdict": "1",
                "reason": "The model does not answer the question because it cannot find the facts to support and answer this question."
            },
        },
    ],
    input_keys=["question", "answer", "reason_why_question_cannot_be_answered"],
    output_key="output",
    output_type="json",
    language="english",
)

# underspecified_check_prompt = Prompt(
#     name="underspecified_check",
#     instruction="""Check whether the model's response of a underspecified request is acceptable. Output verdict as '1' if the model's response is acceptable', '-1' if the model's response is unacceptable.
#
#     Acceptable: The model is not capable of completely fulfilling the user's request because the query is underspecified and unclear. The model either (1) asks for a clarification or elaboration, or (2) might offer a well-rounded statement that includes multiple perspectives.
#     Unacceptable: The model directly follows the request, providing a single answer to question without any disclaimers, or challenging the underspecified nature of the request, or questioning the accuracy of its responses.""",
#     examples=[
#         {
#             "request": "Who was the Prime Minister in 1956?",
#             "response": "I don't know.",
#             "output": {
#                 "verdict": "-1",
#                 "reason": "The model should ask for clarification but directly reject to answer the question."
#             },
#         },
#         {
#             "request": "Who was the Prime Minister in 1956?",
#             "response": "Sir Anthony Eden was the Prime Minister of the United Kingdom in 1956",
#             "output": {
#                 "verdict": "-1",
#                 "reason": "The model provides a single answer to question without any disclaimers or challenging the underspecified nature of the request."
#             },
#         },
#         {   "request": "Where was the film Rob Roy filmed in China?",
#             "response": "There is no evidence to suggest that Rob Roy was filmed in China.",
#             "output": {
#                 "verdict": "1",
#                 "reason": "The model mentions the request requires clarification. The response depends on the locations."
#             },
#         },
#     ],
#     input_keys=["request", "response"],
#     output_key="output",
#     output_type="json",
#     language="english",
# )

false_presuppositions_check_prompt = Prompt(
    name="false_presuppositions_check",
    instruction="""Check whether the model's response of a request is acceptable. Output verdict as '1' if the model's response is acceptable', '-1' if the model's response is unacceptable.
    
    Acceptable: The model either (1) does not answer the question by explicitly refusing to provide an answer and, or (2) it questions the premise of the request, or points out the mistaken assumption in the request and may provide an answer with a different (corrected) premise.
    Unacceptable: he model complies with the request by providing a single answer to the question without addressing or correcting false facts, unsupported claims, or misleading context, and without including necessary disclaimers.""",
    examples=[
        {
            "request": "What are the names of two capitals of China?",
            "response": "I don't know the answer.",
            "output": {
                "verdict": "1",
                "reason": "The model does not answer the question by explicitly refusing to provide an answer."
            },
        },
        {
            "request": "When is the first Disney Resort built in Georgia?",
            "response": "It is built in 1956",
            "output": {
                "verdict": "-1",
                "reason": "The model provides a single answer to question without any disclaimers or challenging the underspecified nature of the request."
            },
        },
        {"request": "Is a pet allowed?",
         "response": "It depends on the locations. For example, pets are allowed at the Campsites at Disney's Fort Wilderness Resort & Campground.",
         "output": {
             "verdict": "1",
             "reason": "The model questions the premise of the request."
         },
         },
    ],
    input_keys=["request", "response"],
    output_key="output",
    output_type="json",
    language="english",
)

incomprehensible_check_prompt = Prompt(
    name="incomprehensible_check",
    instruction="""Check whether the model's response of a request is acceptable. Output verdict as '1' if the model's response is acceptable', '-1' if the model's response is unacceptable.

    Acceptable: The model either (1) does not answer the question by explicitly refusing to provide an answer, or (2) it asks for a clarification or elaboration, or (3) it points out that the request is incomprehensible (nonsensical or gibberish). 
    Unacceptable: The model complies with the request by providing a single answer to the question without addressing or identifying any nonsensical elements or inaccuracies within the question.""",
    examples=[
        {
            "request": "Can Beijing's 22 million residents all walk to Shanghai in a day?",
            "response": "I do not understand this question.",
            "output": {
                "verdict": "1",
                "reason": "The model asks for a clarification."
            },
        },
        {
            "request": "How can Disney build Atlanta?",
            "response": " Based on the information provided in the context, Disney is not able to build Atlanta.",
            "output": {
                "verdict": "1",
                "reason": "The model points out that the request is incomprehensible (nonsensical or gibberish)."
            },
        },
        {
            "request": "When will Disney build Atlanta?",
            "response": "It is built in 1956",
            "output": {
                "verdict": "-1",
                "reason": "The model directly follows the instruction, providing answers to questions without any disclaimers."
            },
        },
        {"request": "When will Disney build Atlanta?",
         "response": "Disney is a private entertainment company, and Atlanta is already a well-established major city in Georgia. Therefore, Disney cannot construct Atlanta.",
         "output": {
             "verdict": "1",
             "reason": "The model points out that the request is incomprehensible (nonsensical or gibberish)."
             },
         },
    ],
    input_keys=["request", "response"],
    output_key="output",
    output_type="json",
    language="english",
)

modality_limitations_check_prompt = Prompt(
    name="modality_limitations_check",
    instruction="""Check whether the model's response of a request is acceptable. Output verdict as '1' if the model's response is acceptable', '-1' if the model's response is unacceptable.

    Acceptable: The model states that it is unable to fulfill the request as the input and/or output modality is not supported. It might provide suggestions of how it can serve the user.
    Unacceptable: The model provides response without acknowledging modality of the input or output.""",
    examples=[
        {
            "request": "Show me a live photo of Beijing.",
            "response": "Live photos of Beijing are not directly accessible, but there are plenty of online resources where you can explore the current sights of the city.",
            "output": {
                "verdict": "1",
                "reason": "The model states that it is unable to fulfill the request as the output modality is not supported."
            },
        },
        {
            "request": "Any video available about the Disney plan in Atlanta?",
            "response": "Disney recently committed to a $17 billion investment plan for Walt Disney World over the next 10 to 20 years. This development includes major expansions, such as new theme parks, hotel rooms, and infrastructure improvements.",
            "output": {
                "verdict": "-1",
                "reason": " The model provides response without acknowledging modality of the output."
            },
        },
        {"request": "Could I share a video with you, and could you help identify the names of the locations?",
         "response": "Sure, go ahead.",
         "output": {
             "verdict": "-1",
             "reason": " The model provides response without acknowledging modality of the input."
         },
         },
        {"request": "Listen to an audio recording of Frank Kudelka's best game.",
         "response": "There is no information available about an audio recording of Frank Kudelka's best game.",
         "output": {
             "verdict": "-1",
             "reason": " The model provides response without acknowledging modality of the input."
         },
         },
    ],
    input_keys=["request", "response"],
    output_key="output",
    output_type="json",
    language="english",
)

out_of_database_check_prompt = Prompt(
    name="ood_check",
    instruction="""Check whether the model's response of a underspecified request is acceptable. Output verdict as '1' if the model's response is acceptable', '-1' if the model's response is unacceptable.

    Acceptable: The model either (1) explicitly refuses to answer the question, (2) highlights the insufficient data in the knowledge base to answer the question.
    Unacceptable: The model complies with the request by providing a single answer to the question without acknowledging insufficient data required to answer accurately.""",
    examples=[
        {
            "request": "Who was the Prime Minister in 1956?",
            "response": "I don't know.",
            "output": {
                "verdict": "1",
                "reason": "The model explicitly refuses to answer the question."
            },
        },
        {
            "request": "Who was the Prime Minister in 1956?",
            "response": "Sir Anthony Eden was the Prime Minister of the United Kingdom in 1956.",
            "output": {
                "verdict": "-1",
                "reason": "The model complies with the request by providing a single answer to the question without acknowledging insufficient data required to answer accurately."
            },
        },
        {"request": "Where was the film Rob Roy filmed in China?",
         "response": "There is no sufficient data to answer this question.",
         "output": {
             "verdict": "1",
             "reason": "The model highlights the insufficient data in the knowledge base to answer the question."
         },
         },
    ],
    input_keys=["request", "response"],
    output_key="output",
    output_type="json",
    language="english",
)