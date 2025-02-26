import os, json
import asyncio
from langchain_openai.chat_models import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from ragas.llms.json_load import json_loader
from prompts_evaluation import unanswerable_check_prompt, clarification_check_prompt, false_presuppositions_check_prompt, incomprehensible_check_prompt, modality_limitations_check_prompt, out_of_database_check_prompt
from prompts_evaluation_reason import underspecified_check_reason_prompt, safety_concern_check_prompt
from collections import Counter
from tqdm import tqdm
from collections import defaultdict
import logging
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

def load_unanswerable_dataset(folder):
    with open(os.path.join(folder, "unanswerable_questions.json"), 'r') as f:
        questions_dict = json.load(f)
    with open(os.path.join(folder, "unanswerable_reasons.json"), 'r') as f:
        reasons_dict = json.load(f)
    return questions_dict, reasons_dict

async def eval_acceptable(question, answer, category, reason, generator_llm_model):
    if category and category == "underspecified":
        prompt = underspecified_check_reason_prompt.format(request=question, response=answer, underspecified_reason=reason)
    elif category and category == "false_presuppositions":
        prompt = false_presuppositions_check_prompt.format(request=question, response=answer)
    elif category and category == "incomprehensible":
        prompt = incomprehensible_check_prompt.format(request=question, response=answer)
    elif category and category == "modality-limited":
        prompt = modality_limitations_check_prompt.format(request=question, response=answer)
    elif category and category == "safety-concern":
        prompt = safety_concern_check_prompt.format(request=question, response=answer)
    else:
        prompt = out_of_database_check_prompt.format(request=question, response=answer)
    try:
        results = await generator_llm_model.generate(prompt=prompt, is_async=False)
        result = await json_loader.safe_load(
            results.generations[0][0].text.strip(), llm=generator_llm_model, is_async=False
        )
        acceptable, reason_acceptable = result["verdict"], result["reason"]
    except:
        acceptable, reason_acceptable = None, None
    return acceptable, reason_acceptable

async def eval_unanswerable(question, answer, reason, generator_llm_model):
    prompt = unanswerable_check_prompt.format(question=question, answer=answer)
    try:
        results = await generator_llm_model.generate(prompt=prompt, is_async=False)
        result = await json_loader.safe_load(
            results.generations[0][0].text.strip(), llm=generator_llm_model, is_async=False
        )
        answerable, reason_unanswer = result["verdict"], result["reason"]
    except:
        answerable, reason_unanswer = None, None

    followed, reason_followed = None, None
    if answerable and reason: # and answerable != "1":
        prompt = clarification_check_prompt.format(question=question, answer=answer, reason_why_question_cannot_be_answered=reason)
        try:
            results = await generator_llm_model.generate(prompt=prompt, is_async=False)
            result = await json_loader.safe_load(
                results.generations[0][0].text.strip(), llm=generator_llm_model, is_async=False
            )
            followed, reason_followed = result["verdict"], result["reason"]
        except:
            pass

    return answerable, reason_unanswer, followed, reason_followed

async def eval_unanswerable_batch(questions, answers, reasons, categories, generator_llm_model, eval_type="acceptable"):

    answerable_lst, reason_unanswer_lst, followed_lst, reason_followed_lst = [], [], [], []
    for question, answer, reason, category in tqdm(zip(questions, answers, reasons, categories)):
        if eval_type == "answerable" or eval_type == "all":
            answerable, reason_unanswer, followed, reason_followed = await eval_unanswerable(question, answer, reason, generator_llm_model)
            if answerable is not None:
                answerable_lst.append(answerable)
                reason_unanswer_lst.append(reason_unanswer)
                followed_lst.append(followed)
                reason_followed_lst.append(reason_followed)
            else:
                answerable_lst.append(None)
                reason_unanswer_lst.append(None)
                followed_lst.append(None)
                reason_followed_lst.append(None)

        elif eval_type == "acceptable" and category:
            acceptable, reason_acceptable = await eval_acceptable(question, answer, category, reason, generator_llm_model)
            if acceptable is not None:
                answerable_lst.append(acceptable)
                reason_unanswer_lst.append(reason_acceptable)
                followed_lst.append(None)
                reason_followed_lst.append(None)
            else:
                answerable_lst.append(None)
                reason_unanswer_lst.append(None)
                followed_lst.append(None)
                reason_followed_lst.append(None)

    return answerable_lst, reason_unanswer_lst, followed_lst, reason_followed_lst

def count_ratio_and_save(answerable_lst, reason_unanswer_lst, followed_lst, reason_followed_lst, questions, answers, reasons, categories, save_path=None):
    count = Counter(answerable_lst)

    # count 1, 1 as 0
    add_on_clarification = 0
    total = 0
    category_count = defaultdict(int)
    category_total = defaultdict(int)
    for i, answerable in enumerate(answerable_lst):
        if answerable == "1" and followed_lst[i] == "1":
            add_on_clarification += 1

        if answerable in ["1", "-1", "0"]:
            total += 1
            if categories and categories[i]:
                category_total[categories[i]] += 1
                if answerable == "1":
                    category_count[categories[i]] += 1

    for category in category_count:
        if category_total[category]:
            category_count[category] = category_count[category] / category_total[category]

    unanswerable_ratio, clarification_needed_ratio = count["-1"] / total, (count["0"] + add_on_clarification) / total
    results = {"unanswerable_ratio": unanswerable_ratio, "clarification_needed_ratio": clarification_needed_ratio}
    results["reason_unanswer_lst"] = reason_unanswer_lst
    results["followed_lst"] = followed_lst
    results["reason_followed_lst"] = reason_followed_lst
    results["answerable_lst"] = answerable_lst
    results["questions"] = questions
    results["answers"] = answers
    results["reasons"] = reasons
    results["categories"] = categories
    results["category_count"] = category_count
    if save_path is not None:
        with open(save_path, "w") as f:
            json.dump(results, f)
    return unanswerable_ratio, clarification_needed_ratio, category_count



async def eval_from_dataset(file_path, question_reason_dict, question_category_dict, generator_llm_model, test_size, eval_type="acceptable", unanswered_type=None):
    with open(file_path, "r") as f:
        data = json.load(f)

    # load questions, answers and reasons.
    questions = data["question"][:min(test_size, len(data["question"]))]
    answers = data["answer"][:min(test_size, len(data["answer"]))]

    if "reason" in data:
        reasons = data["reason"][:min(test_size, len(data["reason"]))]
    else:
        reasons = []
        for q in questions:
            if question_reason_dict and q.strip() in question_reason_dict:
                reasons.append(question_reason_dict[q.strip()])
            else:
                reasons.append(None)

    # add categories
    categories = []
    for q in questions:
        if question_category_dict and q.strip() in question_category_dict:
            categories.append(question_category_dict[q.strip()])
        else:
            categories.append("out-of-database")
    questions_eval, answers_eval, reasons_eval, categories_eval = [], [], [], []
    for i in range(len(questions)):
        if not unanswered_type or unanswered_type == categories[i]:
            questions_eval.append(questions[i])
            answers_eval.append(answers[i])
            reasons_eval.append(reasons[i])
            categories_eval.append(categories[i])

    answerable_lst, reason_unanswer_lst, followed_lst, reason_followed_lst = [], [], [], []
    if questions_eval:
        # call eval harness
        answerable_lst, reason_unanswer_lst, followed_lst, reason_followed_lst = await eval_unanswerable_batch(questions_eval, answers_eval, reasons_eval, categories_eval, generator_llm_model, eval_type=eval_type)
    return answerable_lst, reason_unanswer_lst, followed_lst, reason_followed_lst, questions_eval, answers_eval, reasons_eval, categories_eval

def make_question_reason_dict(file_path_question, file_path_reason, single_category="out-of-database"):
    with open(file_path_question, "r") as f:
        data_q = json.load(f)

    question_reason_dict = dict()
    question_category_dict = dict()
    if file_path_reason:
        with open(file_path_reason, "r") as f:
            data_r = json.load(f)

        for key in data_q.keys():
            for i, question in enumerate(data_q[key]):
                question_reason_dict[question.strip()] = data_r[key][i].strip()
                question_category_dict[question.strip()] = key.strip()
    else:
        for i, question in enumerate(data_q["question"]):
            question_reason_dict[question.strip()] = "This question is out of database and cannot be answered."
            question_category_dict[question.strip()] = single_category

    return question_reason_dict, question_category_dict

async def main():
    generator_llm = "gpt-4o"
    dataset = "triviaQA"
    eval_type = "answerable"  # choose from (1) acceptable and (2) answerable
    llm_usage=ChatOpenAI(model_name=generator_llm)
    generator_llm_model = LangchainLLMWrapper(langchain_llm=llm_usage)
    file_path = f"ur-path-to/data/{dataset}/response/unanswerable_questions_response_gpt4_none-reranker.json"
    file_path_reason = f"ur-path-to/data/{dataset}/unanswerable_reasons.json"
    file_path_question = f"ur-path-to/data/{dataset}/unanswerable_questions.json"
    question_reason_dict, question_category_dict = make_question_reason_dict(file_path_question, file_path_reason)
    answerable_lst, reason_unanswer_lst, followed_lst, reason_followed_lst, questions, answers, reasons, categories = await eval_from_dataset(file_path, question_reason_dict, question_category_dict, generator_llm_model, test_size=500, eval_type=eval_type, unanswered_type=None)
    save_path = file_path.split(".json")[0] + f"_{eval_type}_gpt4o.json"
    unanswerable_ratio, clarification_needed_ratio, category_count = count_ratio_and_save(answerable_lst, reason_unanswer_lst, followed_lst, reason_followed_lst, questions, answers, reasons, categories, save_path=save_path)
    print(unanswerable_ratio, clarification_needed_ratio, category_count)

if __name__ == "__main__":
    asyncio.run(main())