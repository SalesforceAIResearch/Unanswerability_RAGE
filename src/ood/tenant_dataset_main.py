import json
from tqdm import tqdm
import argparse
import logging
import os
from collections import defaultdict
from ragas.testset.docstore import Node
from langchain_community.document_loaders import DirectoryLoader, JSONLoader
import asyncio
import random
from langchain.text_splitter import TokenTextSplitter
from langchain_openai.chat_models import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from ragas.testset.docstore import Document, DocumentStore, InMemoryDocumentStore
from ragas.llms.json_load import json_loader
from prompt_rewrite import (
    seed_question_prompt_rewrite,
    question_answer_prompt_rewrite,
    answer_verification_prompt,
    topic_extraction_prompt_rewrite,
    keyphrases_extraction_prompt,
)

import sys
sys.path.append("../rag/")
from run_rag import MyRAG

sys.path.append("../")
from crawler import crawl_gnews_articles


logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


class TenantDatasetCreation:
    def __init__(
        self,
        documents_folder,
        generator_llm="gpt-3.5-turbo",
        chunk_size=2048,
        chunk_overlap=128,
    ):
        self.documents_folder = documents_folder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.nodes_dict = None
        self.generator_llm = generator_llm
        self.generator_llm_model = LangchainLLMWrapper(
            ChatOpenAI(model_name=self.generator_llm)
        )
        self.rag = None

    def build_rag(self, load_index_path, save_index_path, model_name, tmpl_str=None):
        self.rag = MyRAG(
            folder=self.documents_folder,
            load_index_path=load_index_path,
            save_index_path=save_index_path,
            model_name=model_name,
        )
        if tmpl_str:
            self.rag.update_template(tmpl_str)

    async def build_datasets(self, test_size, verify_by_rag=True):
        # generate key phrases
        idx_keyphrases_dict, keyphrases_idx_dict = await self.generate_key_phrases(
            self.nodes_dict, self.generator_llm_model, test_size * 2
        )
        # build questions
        questions, answers, contexts, count, visited_set = [], [], [], 0, set()
        keyphrases_idx_dict = dict(
            sorted(keyphrases_idx_dict.items(), key=lambda item: len(item[1]))
        )

        if verify_by_rag:
            test_size *= 3

        for key in keyphrases_idx_dict:
            idx = list(keyphrases_idx_dict[key])[0]
            if idx not in visited_set:
                visited_set.add(idx)
                node = self.nodes_dict[idx]
                question, answer, verdict = await self.generate_seed_question(
                    node, key, self.generator_llm_model
                )
                verdict = True if verdict and str(verdict) == "1" else False
                if verdict:
                    add_signal = True
                    if verify_by_rag:
                        resp = self.rag.rag_query_engine.query(question)
                        # verify the question is unanswerable
                        unanswerable = await self.verify_unanswerable_query(
                            resp, answer
                        )

                        if not unanswerable:
                            add_signal = False

                    if add_signal:
                        questions.append(question)
                        answers.append(answer)
                        contexts.append([node.page_content])
                        count += 1

                if count >= test_size:
                    break

        return questions, answers, contexts

    async def verify_unanswerable_query(self, answer, ground_truth):
        prompt = answer_verification_prompt.format(
            answer=answer, ground_truth=ground_truth
        )
        # check the answer is correct or not compared w/ ground_truth
        results = await self.generator_llm_model.generate(prompt=prompt, is_async=False)
        responses = await json_loader.safe_load(
            results.generations[0][0].text.strip(),
            llm=self.generator_llm_model,
            is_async=False,
        )
        return str(responses["verdict"]) == "-1"

    def load_text_chunk(self, documents, splitter):
        docs = [Document.from_langchain_document(doc) for doc in documents]
        nodes = [
            Node.from_langchain_document(d) for d in splitter.transform_documents(docs)
        ]
        nodes_dict = dict()
        for idx, node in enumerate(nodes):
            nodes_dict[idx] = node

        return nodes_dict

    async def find_topics(self, topic_size=5, file_format=".txt"):
        topics = set()
        files = [
            f
            for f in os.listdir(self.documents_folder)
            if os.path.isfile(os.path.join(self.documents_folder, f))
            and f.endswith(file_format)
        ]
        random.shuffle(files)
        for filename in files:
            file_path = os.path.join(self.documents_folder, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # find topic
                prompt_topic = topic_extraction_prompt_rewrite.format(text=content)
                results_topic = await self.generator_llm_model.generate(
                    prompt=prompt_topic, is_async=False
                )
                response_topic = await json_loader.safe_load(
                    results_topic.generations[0][0].text.strip(),
                    llm=self.generator_llm_model,
                    is_async=False,
                )
                try:
                    topics.add(response_topic["topic"])
                except Exception as e:
                    print(e)

                if len(topics) >= topic_size:
                    return topics

    def build_nodes(
        self, topics, articles_test_size, articles_save_dir, crawl_news=True
    ):
        splitter = TokenTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )

        if crawl_news:
            articles_total, successful_rate = [], []
            for topic in topics:
                try:
                    articles = crawl_gnews_articles(
                        keywords=[topic],
                        articles_per_feed=articles_test_size // len(topics) + 1,
                    )
                    articles_total += articles
                    length = len(articles)
                    # save articles
                    successful_rate.append(1)
                    if articles_save_dir:
                        with open(
                            f"{articles_save_dir}/{topic}_n_{length}_articles.json", "w"
                        ) as f:
                            json.dump(articles, f)

                except:
                    successful_rate.append(0)
            print("Successful Rate is: ", sum(successful_rate) / len(successful_rate))
            # save all
            with open(f"{articles_save_dir}/full_articles.json", "w") as f:
                json.dump(articles_total, f)
            # convert string to doc
            documents = []
            for article in articles_total:
                documents.append(
                    Document(page_content=article["text"], metadata={"source": "local"})
                )
            nodes_dict = self.load_text_chunk(documents, splitter)
        else:
            loader = JSONLoader(
                file_path=f"{articles_save_dir}/full_articles.json",
                jq_schema=".[].text",
                text_content=False,
            )

            documents = loader.load()

            docs = [Document.from_langchain_document(doc) for doc in documents]
            nodes = [
                Node.from_langchain_document(d)
                for d in splitter.transform_documents(docs)
            ]
            nodes_dict = dict()
            for idx, node in enumerate(nodes):
                nodes_dict[idx] = node
        return nodes_dict

    async def generate_key_phrases(self, nodes_dict, generator_llm_model, test_size):
        idx_keyphrases_dict, keyphrases_idx_dict = dict(), defaultdict(set)
        nodes_dict_keys = list(nodes_dict.keys())
        size = min(
            test_size * 5, len(nodes_dict_keys)
        )
        for i in tqdm(range(size)):
            idx = nodes_dict_keys[i]
            node = nodes_dict[idx]
            prompt = keyphrases_extraction_prompt.format(text=node.page_content)
            results = await generator_llm_model.generate(prompt=prompt, is_async=False)
            keyphrases = await json_loader.safe_load(
                results.generations[0][0].text.strip(),
                llm=generator_llm_model,
                is_async=False,
            )
            idx_keyphrases_dict[idx] = keyphrases["keyphrases"]
            if keyphrases and "keyphrases" in keyphrases:
                for keyphrase in keyphrases["keyphrases"]:
                    keyphrases_idx_dict[keyphrase].add(idx)
        return idx_keyphrases_dict, keyphrases_idx_dict

    async def generate_seed_question(self, node, key, generator_llm_model):
        prompt = seed_question_prompt_rewrite.format(
            context=node.page_content, keyphrase=key
        )
        question, answer, verdict = None, None, None
        try:
            results = await generator_llm_model.generate(prompt=prompt, is_async=False)
            question = await json_loader.safe_load(
                results.generations[0][0].text.strip(),
                llm=generator_llm_model,
                is_async=False,
            )
            if "question" in question:
                question = question["question"]
            elif "query" in question:
                question = question["query"]
            prompt_verify = question_answer_prompt_rewrite.format(
                context=node.page_content, question=question
            )
            results = await generator_llm_model.generate(
                prompt=prompt_verify, is_async=False
            )
            response = await json_loader.safe_load(
                results.generations[0][0].text.strip(),
                llm=generator_llm_model,
                is_async=False,
            )
            answer, verdict = response["answer"], response["verdict"]
        except Exception as e:
            print("Error >>> ", e)

        return question, answer, verdict

    def save_dataset(self, save_path, questions, answers, contexts):
        dataset = dict()
        dataset["question"] = []
        dataset["ground_truth"] = []
        dataset["contexts"] = []
        for idx in range(len(questions)):
            dataset["question"].append(questions[idx])
            dataset["ground_truth"].append(answers[idx])
            dataset["contexts"].append(contexts[idx])

        with open(save_path, "w") as f:
            json.dump(dataset, f)


async def main(args):
    pipeline = TenantDatasetCreation(
        args.documents_folder,
        generator_llm=args.generator_llm,
        chunk_size=1024,
        chunk_overlap=128,
    )
    if args.verify_by_rag:
        print(">>> Begin Build RAG<<<")
        pipeline.build_rag(
            load_index_path=args.load_index_path,
            save_index_path=args.save_index_path,
            model_name=args.rag_model_name,
            tmpl_str=None,
        )
    # find topics
    print(">>> Begin Gen topics<<<")
    if args.crawl_news:
        topics = await pipeline.find_topics(topic_size=args.articles_test_size)
    else:
        topics = None
    # build nodes
    print(">>> Begin Build Nodes<<<")
    pipeline.nodes_dict = pipeline.build_nodes(
        topics,
        args.articles_test_size,
        args.articles_save_dir,
        crawl_news=args.crawl_news,
    )
    # build unanswerable tenant specific dataset
    print(">>> Begin Unanswerable Dataset<<<")
    questions, answers, contexts = await pipeline.build_datasets(
        args.dataset_test_size, verify_by_rag=args.verify_by_rag
    )
    # save dataset
    print(">>> Save Dataset<<<")
    pipeline.save_dataset(args.save_path, questions, answers, contexts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--documents_folder",
        type=str,
        help="Documents for datasets.",
    )
    parser.add_argument(
        "--save_path",
        type=str,
        help="Documents for saving datasets.",
    )
    parser.add_argument(
        "--generator_llm",
        default="gpt-4-0125-preview",
        type=str,
        help="OpenAI model use here.",
    )
    parser.add_argument(
        "--rag_check",
        action="store_true",
        help="Use RAG or not",
    )
    parser.add_argument(
        "--load_index_path",
        default=None,
        type=str,
        help="database",
    )
    parser.add_argument(
        "--save_index_path",
        default="./disney_june4ragas",
        type=str,
        help="database",
    )
    parser.add_argument(
        "--rag_model_name",
        default="gpt-4-0125-preview",
        type=str,
        help="openai model",
    )
    parser.add_argument(
        "--articles_topic",
        default="Disney",
        type=str,
        help="openai model",
    )
    parser.add_argument(
        "--articles_test_size",
        default=200,
        type=int,
        help="openai model",
    )
    parser.add_argument(
        "--dataset_test_size",
        default=100,
        type=int,
        help="openai model",
    )
    parser.add_argument(
        "--articles_save_dir",
        default="./",
        type=str,
        help="openai model",
    )
    parser.add_argument(
        "--crawl_news",
        action="store_true",
        help="openai model",
    )
    parser.add_argument(
        "--verify_by_rag",
        action="store_true",
        help="openai model",
    )

    args = parser.parse_args()
    dataset = "hotpotqa"
    # current dataset index_path
    # if no, then
    args.load_index_path = None
    # if yes, then
    args.load_index_path = f"path-to/rag/{dataset}"
    args.crawl_news = True
    args.verify_by_rag = True
    args.articles_test_size = 100
    args.dataset_test_size = 100
    args.documents_folder = "path-to-yout/database"
    args.articles_save_dir = "path-to-save-your/articles"
    args.save_path = f"path-to-save-your-dataset/ood/ood_unanswerable_2.json"
    asyncio.run(main(args))
