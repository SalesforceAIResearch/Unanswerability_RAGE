import json, os
import asyncio
from tqdm import tqdm
from ragas.testset.docstore import Node
from langchain_openai.chat_models import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from ragas.llms.json_load import json_loader
from prompts_taxonomy import (
    underspecified_gen_prompt,
    false_presuppositions_gen_prompt,
    incomprehensible_gen_prompt,
    modality_limitations_gen_prompt,
    underspecified_verify_prompt,
    false_presuppositions_verify_prompt,
    incomprehensible_verification_prompt,
    safety_concern_gen_prompt,
    safety_concern_verification_prompt,
    anwerable_verification_prompt,
)
from langchain.text_splitter import TokenTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from ragas.testset.docstore import Document, DocumentStore, InMemoryDocumentStore
import logging
import random

logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


async def unanswerable_generation(context, type, generator_llm_model, verified=True):
    if type == "underspecified":
        prompt = underspecified_gen_prompt.format(context=context)
    elif type == "false_presuppositions":
        prompt = false_presuppositions_gen_prompt.format(context=context)
    elif type == "incomprehensible":
        prompt = incomprehensible_gen_prompt.format(context=context)
    elif type == "modality-limited":
        prompt = modality_limitations_gen_prompt.format(context=context)
        verified = False
    elif type == "safety-concern":
        prompt = safety_concern_gen_prompt.format(context=context)
        verified = False
    else:
        prompt = None

    question_org = None
    try:
        results = await generator_llm_model.generate(prompt=prompt, is_async=False)
        result = await json_loader.safe_load(
            results.generations[0][0].text.strip(),
            llm=generator_llm_model,
            is_async=False,
        )

        question, reason = result["question"], result["reason"]
        if "original-question" in result:
            question_org = result["original-question"]
            if type == "safety-concern":
                verified = True
    except:
        question, reason = None, None

    if question and reason and verified:
        prompts = []
        if type == "underspecified":
            prompt = underspecified_verify_prompt.format(question=question)
        elif type == "false_presuppositions":
            prompt = false_presuppositions_verify_prompt.format(
                question=question, reason=reason
            )
        elif type == "incomprehensible":
            prompt = incomprehensible_verification_prompt.format(
                question=question, reason=reason, context=context
            )
        elif type == "safety-concern":
            prompts = []
            prompts.append(safety_concern_verification_prompt.format(question=question))
            prompts.append(
                anwerable_verification_prompt.format(
                    question=question_org, context=context
                )
            )
        try:
            if prompts:
                results = await generator_llm_model.generate(
                    prompt=prompts[0], is_async=False
                )
                result = await json_loader.safe_load(
                    results.generations[0][0].text.strip(),
                    llm=generator_llm_model,
                    is_async=False,
                )
                verification, explanation = result["verdict"], result["explanation"]
                results = await generator_llm_model.generate(
                    prompt=prompts[1], is_async=False
                )
                result = await json_loader.safe_load(
                    results.generations[0][0].text.strip(),
                    llm=generator_llm_model,
                    is_async=False,
                )
                verification = (
                    "1"
                    if int(result["verdict"]) == 1 and int(verification) == 1
                    else "0"
                )
                explanation = result["explanation"] + "\n\n\n" + explanation
            else:
                results = await generator_llm_model.generate(
                    prompt=prompt, is_async=False
                )
                result = await json_loader.safe_load(
                    results.generations[0][0].text.strip(),
                    llm=generator_llm_model,
                    is_async=False,
                )
                verification, explanation = result["verdict"], result["explanation"]
        except:
            verification, explanation = None, None
        if verification and verification == "1":
            return question, reason
    elif question and reason:
        return question, reason
    return None, None


def chunk_files(folder, chunk_size=2048):
    # load Documents
    loader = DirectoryLoader(folder)
    documents = loader.load()
    # chunking
    splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=24)
    docs = [Document.from_langchain_document(doc) for doc in documents]
    chunks = [
        Node.from_langchain_document(d).page_content
        for d in splitter.transform_documents(docs)
    ]
    return chunks


async def unanswerable_generation_batch(
    chunks, type, generator_llm_model, test_size, contribution
):
    questions, reasons = [], []
    size = int(test_size * contribution[type])
    count = 0
    for context in tqdm(chunks * (size // len(chunks) + 2)):
        question, reason = await unanswerable_generation(
            context, type=type, generator_llm_model=generator_llm_model
        )
        if question is not None:
            questions.append(question)
            reasons.append(reason)
            count += 1
        if count >= size:
            break
    return questions, reasons


async def generate_unanswerable_batch(
    folder,
    test_size,
    contribution,
    generator_llm="gpt-4-0125-preview",
    chunk_size=4096,
    save_path_folder=None,
):
    generator_llm_model = LangchainLLMWrapper(ChatOpenAI(model_name=generator_llm))
    # 1. chunk
    chunks = chunk_files(folder, chunk_size=chunk_size)
    # 2. generate questions
    questions_dict, reasons_dict = dict(), dict()
    for type in contribution:
        random.shuffle(chunks)
        questions, reasons = await unanswerable_generation_batch(
            chunks, type, generator_llm_model, test_size, contribution
        )
        questions_dict[type] = questions
        reasons_dict[type] = reasons

    if save_path_folder is not None:
        with open(
            os.path.join(save_path_folder, "unanswerable_questions.json"), "w"
        ) as f:
            json.dump(questions_dict, f)
        with open(
            os.path.join(save_path_folder, "unanswerable_reasons.json"), "w"
        ) as f:
            json.dump(reasons_dict, f)


async def main():
    # 1. Specify the contribution of different categories.
    dataset_name = "2wiki"
    contribution = {
        "incomprehensible": 0.2,
        "false_presuppositions": 0.2,
        "underspecified": 0.2,
        "safety-concern": 0.2,
        "modality-limited": 0.2,
    }
    # 2. Specify the folder to save the data
    save_path_folder = f"../data/{dataset_name}"
    # 3. Specify the database folder
    folder = f"ur-path-to/{dataset_name}/database"
    # 4. Specify the test size you want. (Total number of the dataset samples)
    test_size = 300
    await generate_unanswerable_batch(
        folder=folder,
        test_size=test_size,
        contribution=contribution,
        save_path_folder=save_path_folder,
        generator_llm="gpt-4o",
    )

if __name__ == "__main__":
    asyncio.run(main())
