from ragas.llms.prompt import Prompt

keyphrase_extraction_prompt_rewrite = Prompt(
    name="keyphrase_extraction",
    instruction="Extract the top 3 to 5 keyphrases from the provided text, focusing on the most significant and distinctive aspects. The extracted keyphrases must be relevant with the given topic",
    examples=[
        {
            "text": "A black hole is a region of spacetime where gravity is so strong that nothing, including light and other electromagnetic waves, has enough energy to escape it. The theory of general relativity predicts that a sufficiently compact mass can deform spacetime to form a black hole.",
            "topic": "aerospace",
            "output": {
                "keyphrases": [
                    "Black hole",
                    "Region of spacetime",
                    "Strong gravity",
                    "Light and electromagnetic waves",
                    "Theory of general relativity",
                ]
            },
        },
        {
            "text": "The Great Wall of China is an ancient series of walls and fortifications located in northern China, built around 500 years ago. This immense wall stretches over 13,000 miles and is a testament to the skill and persistence of ancient Chinese engineers.",
            "topic": "China",
            "output": {
                "keyphrases": [
                    "Great Wall of China",
                    "Ancient fortifications",
                    "Northern China",
                ]
            },
        },
    ],
    input_keys=["text", "topic"],
    output_key="output",
    output_type="json",
)

keyphrases_extraction_prompt = Prompt(
    name="key_phrase_extraction",
    instruction="Extract the top 1 to 3 keyphrases from the provided text, focusing on the most significant and distinctive aspects.",
    examples=[
        {
            "text": "A black hole is a region of spacetime where gravity is so strong that nothing, including light and other electromagnetic waves, has enough energy to escape it. The theory of general relativity predicts that a sufficiently compact mass can deform spacetime to form a black hole.",
            "output": {
                "keyphrases": [
                    "Black hole",
                    "Region of spacetime",
                    "Strong gravity",
                ]
            },
        },
        {
            "text": "The Great Wall of China is an ancient series of walls and fortifications located in northern China, built around 500 years ago. This immense wall stretches over 13,000 miles and is a testament to the skill and persistence of ancient Chinese engineers.",
            "output": {
                "keyphrases": [
                    "Great Wall of China",
                    "Ancient fortifications",
                    "Northern China",
                ]
            },
        },
    ],
    input_keys=["text"],
    output_key="output",
    output_type="json",
)

topic_extraction_prompt_rewrite = Prompt(
    name="topic_extraction",
    instruction="Extract the main topic from the provided text, focusing on the most significant aspects. The extracted topic must be a single phrase.",
    examples=[
        {
            "text": "A black hole is a region of spacetime where gravity is so strong that nothing, including light and other electromagnetic waves, has enough energy to escape it. The theory of general relativity predicts that a sufficiently compact mass can deform spacetime to form a black hole.",
            "output": {
                "topic":
                    "Black hole"
            },
        },
        {
            "text": "The Great Wall of China is an ancient series of walls and fortifications located in northern China, built around 500 years ago. This immense wall stretches over 13,000 miles and is a testament to the skill and persistence of ancient Chinese engineers.",
            "output": {
                "topic":
                    "Great Wall of China"
            },
        },
    ],
    input_keys=["text",],
    output_key="output",
    output_type="json",
)


seed_question_prompt_rewrite = Prompt(
    name="seed_question",
    instruction="Generate a question that can be fully answered from given context. The question should be formed using topic",
    examples=[
        {
            "context": "Photosynthesis in plants involves converting light energy into chemical energy, using chlorophyll and other pigments to absorb light. This process is crucial for plant growth and the production of oxygen.",
            "keyphrase": "Photosynthesis, plant",
            "question": "What is the role of photosynthesis in plant growth?",
        },
        {
            "context": "The Industrial Revolution, starting in the 18th century, marked a major turning point in history as it led to the development of factories and urbanization.",
            "keyphrase": "Industrial Revolution, major turning point",
            "question": "How did the Industrial Revolution mark a major turning point in history?",
        },
        {
            "context": "The process of evaporation plays a crucial role in the water cycle, converting water from liquid to vapor and allowing it to rise into the atmosphere.",
            "keyphrase": "Evaporation, water",
            "question": "Why is evaporation important in the water cycle?",
        },
    ],
    input_keys=["context", "keyphrase"],
    output_key="question",
    output_type="str",
)

question_answer_prompt_rewrite = Prompt(
    name="answer_formulate",
    instruction="""Answer the question using the information from the given context. Output verdict as '1' if answer is present '-1' if answer is not present in the context.""",
    examples=[
        {
            "context": """Climate change is significantly influenced by human activities, notably the emission of greenhouse gases from burning fossil fuels. The increased greenhouse gas concentration in the atmosphere traps more heat, leading to global warming and changes in weather patterns.""",
            "question": "How do human activities contribute to climate change?",
            "answer": {
                "answer": "Human activities contribute to climate change primarily through the emission of greenhouse gases from burning fossil fuels. These emissions increase the concentration of greenhouse gases in the atmosphere, which traps more heat and leads to global warming and altered weather patterns.",
                "verdict": "1",
            },
        },
        {
            "context": """The concept of artificial intelligence (AI) has evolved over time, but it fundamentally refers to machines designed to mimic human cognitive functions. AI can learn, reason, perceive, and, in some instances, react like humans, making it pivotal in fields ranging from healthcare to autonomous vehicles.""",
            "question": "What are the key capabilities of artificial intelligence?",
            "answer": {
                "answer": "Artificial intelligence is designed to mimic human cognitive functions, with key capabilities including learning, reasoning, perception, and reacting to the environment in a manner similar to humans. These capabilities make AI pivotal in various fields, including healthcare and autonomous driving.",
                "verdict": "1",
            },
        },
        {
            "context": """The novel "Pride and Prejudice" by Jane Austen revolves around the character Elizabeth Bennet and her family. The story is set in the 19th century in rural England and deals with issues of marriage, morality, and misconceptions.""",
            "question": "What year was 'Pride and Prejudice' published?",
            "answer": {
                "answer": "The answer to given question is not present in context",
                "verdict": "-1",
            },
        },
    ],
    input_keys=["context", "question"],
    output_key="answer",
    output_type="json",
    language="english",
)

answer_verification_prompt = Prompt(
    name="answer_verification",
    instruction="""Check the answer is correct or not given the ground truth. Output verdict as '1' if answer is correct. Output verdict as '-1' if the answer is incorrect or if it indicates a lack of knowledge regarding the answer.""",
    examples=[
        {
            "answer": """The United States Securities and Exchange Commission report provides information about Disney's fiscal year ending on October 2, 2021.""",
            "ground_truth": "The United States Securities and Exchange Commission report provides information about Disney's fiscal year ending on October 12, 2023.",
            "output": {
                "reason": "The date in the answer is wrong compared to the ground_truth.",
                "verdict": "-1",
            },
        },
        {
            "answer": """Disney has implemented several key programs and initiatives for human capital management. These include Diversity, Equity, and Inclusion (DE&I) initiatives, health, wellness, family resources, and other benefits, a continued response to COVID-19, the Disney Aspire education investment program, Talent Development programs, and a focus on Social Responsibility and Community. They also have environmental and sustainability goals.""",
            "ground_truth": "Diversity, Equity, and Inclusion (DE&I) initiatives, health, wellness, family resources.",
            "output": {
                "reason": "The answer covers all the information in the ground_truth.",
                "verdict": "1",
            },
        },
        {
            "answer": """I don't know.""",
            "ground_truth": "Diversity, Equity, and Inclusion (DE&I) initiatives, health, wellness, family resources.",
            "output": {
                "reason": "The answer indicates a lack of knowledge regarding the answer.",
                "verdict": "-1",
            },
        }
    ],
    input_keys=["answer", "ground_truth"],
    output_key="output",
    output_type="json",
    language="english",
)

unknown_verification_prompt = Prompt(
    name="unknown_verification",
    instruction="""Check the model's answer indicates the model cannot answer the question or the model needs more information to answer the question. Output verdict as '1' if the model successfully answer the question, '-1' if the model cannot answer the question.""",
    examples=[
        {
            "answer": """I don't know.""",
            "output": {
                "reason": "The answer indicates the model cannot answer the question.",
                "verdict": "-1",
            },
        },
        {
            "answer": """Based on the information provided in the context, it is not possible to determine how long it will take for Chicago to average 50,000 drones flying overhead on a daily basis.""",
            "output": {
                "reason": "The model requires more information to answer the question.",
                "verdict": "-1",
            },
        },
{
            "answer": """To define ourselves and our lives, both individually and collectively, in the absence of a single fixed truth or reality, we navigate the complexities by embracing diversity and multiple perspectives.""",
            "output": {
                "reason": "The model tries to answer the question.",
                "verdict": "1",
            },
        }
    ],
    input_keys=["answer"],
    output_key="output",
    output_type="json",
    language="english",
)