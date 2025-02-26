import json
import os, argparse
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    ServiceContext,
)
from llama_index.core.retrievers import (
    BaseRetriever,
    VectorIndexRetriever,
    KeywordTableSimpleRetriever,
)
from collections import defaultdict
from llama_index.core import get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI
from llama_index.core import StorageContext
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import PromptTemplate
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.core.query_engine import TransformQueryEngine
from llama_index.core.postprocessor import LLMRerank
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.packs.raptor import RaptorRetriever
from llama_index.core.query_engine import MultiStepQueryEngine
from llama_index.core.indices.query.query_transform.base import (
    StepDecomposeQueryTransform,
)
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

import nest_asyncio
nest_asyncio.apply()

class CustomRetriever(BaseRetriever):
    """Custom retriever that performs both semantic search and hybrid search."""

    def __init__(
        self,
        vector_retriever,
        raptor_retriever,
        mode="OR",
    ) -> None:
        """Init params."""

        self._vector_retriever = vector_retriever
        self._raptor_retriever = raptor_retriever
        if mode not in ("AND", "OR"):
            raise ValueError("Invalid mode.")
        self._mode = mode
        super().__init__()
    def _retrieve(self, query_bundle):
        """Retrieve nodes given query."""

        vector_nodes = self._vector_retriever.retrieve(query_bundle)
        raptor_nodes = self._raptor_retriever.retrieve(query_bundle)

        vector_ids = {n.node.node_id for n in vector_nodes}
        raptor_ids = {n.node.node_id for n in raptor_nodes}

        combined_dict = {n.node.node_id: n for n in vector_nodes}
        combined_dict.update({n.node.node_id: n for n in raptor_nodes})

        if self._mode == "AND":
            retrieve_ids = vector_ids.intersection(raptor_ids)
        else:
            retrieve_ids = vector_ids.union(raptor_ids)

        retrieve_nodes = [combined_dict[rid] for rid in retrieve_ids]

        return retrieve_nodes

class MyRAG:
    def __init__(
        self,
        folder,
        load_index_path,
        save_index_path,
        model_name,
        retriever_type=None,
        reranker_type=None,
        rewriting=None,
        retriever_load_path=None,
        retriever_save_path=None,
        embed_model="openai",
    ):
        self.folder = folder
        self.load_index_path = load_index_path
        self.save_index_path = save_index_path
        self.model_name = model_name
        self.rewriting = rewriting
        self.retriever_type = retriever_type
        self.retriever_load_path = retriever_load_path
        self.retriever_save_path = retriever_save_path
        self.llm = OpenAI(temperature=0.0000000000001, model=model_name)
        self.embed_model = self.load_embed_model(embed_model)
        self.service_context = ServiceContext.from_defaults(
            llm=self.llm, chunk_size=1024, chunk_overlap=24
        )
        self.reranker = self.build_reranker(reranker_type)

        self.documents = SimpleDirectoryReader(folder).load_data()

        self.storage_context, self.vector_index = self.build_index()

        self.rag_query_engine, self.rag_query_engine_rewrite, self.retriever = self.build_engine()

    def load_embed_model(self, embed_model):
        if embed_model == "bge":
            print("BGE embedding is used")
            embed_model = HuggingFaceEmbedding(
                model_name="BAAI/bge-large-en-v1.5"
            )
            Settings.embed_model = embed_model
            return embed_model

        if embed_model == "cohere":
            print("Cohere embedding is used")
            embed_model = CohereEmbedding(
            api_key=os.environ["COHERE_API_KEY"],
            model_name="embed-english-v3.0",
            input_type="search_query",
        )
            Settings.embed_model = embed_model
            return embed_model

        print("OpenAI embedding is used")
        embed_model = OpenAIEmbedding(
                        model="text-embedding-3-small"
                    )
        Settings.embed_model = embed_model
        return embed_model

    def build_reranker(self, reranker_type=None):
        reranker = None
        if not reranker_type:
            return None

        if reranker_type == "llm":
            reranker = LLMRerank(
                choice_batch_size=5,
                top_n=5,
            )

        if reranker_type == "cohere":
            api_key = os.environ["COHERE_API_KEY"]
            reranker = CohereRerank(api_key=api_key, top_n=5)

        return reranker

    def build_index(self):
        if (
            not self.load_index_path
        ):  # generate and store the index if it doesn't exist, but load it if it does
            parser = SentenceSplitter()
            nodes = parser.get_nodes_from_documents(self.documents)

            # create storage context using default stores
            storage_context = StorageContext.from_defaults(
                docstore=SimpleDocumentStore(),
                vector_store=SimpleVectorStore(),
                index_store=SimpleIndexStore(),
            )

            # create (or load) docstore and add nodes
            storage_context.docstore.add_documents(nodes)

            # build index

            vector_index = VectorStoreIndex(nodes, storage_context=storage_context,embed_model=self.embed_model)
            vector_index.storage_context.persist(persist_dir=self.save_index_path)

        else:
            storage_context = StorageContext.from_defaults(
                persist_dir=self.load_index_path
            )
            vector_index = load_index_from_storage(storage_context)

        return storage_context, vector_index

    def build_retriever(self):
        similarity_top_k = 5
        if self.retriever_type:
            similarity_top_k = 10

        if self.retriever_type == "bm25":
            retriever = BM25Retriever.from_defaults(
                docstore=self.storage_context.docstore,
                similarity_top_k=similarity_top_k,
            )
        elif self.retriever_type == "raptor" or self.retriever_type == "ensemble":
            if self.retriever_load_path:
                retriever = RaptorRetriever.from_persist_dir(
                    persist_dir=self.retriever_load_path,
                )
            else:
                retriever = RaptorRetriever(
                    self.documents,
                    embed_model=self.embed_model,
                    tree_depth=2,
                    llm=self.llm,  # used for generating summaries
                    similarity_top_k=2,  # top k for each layer, or overall top-k for collapsed
                    mode="tree_traversal",  # sets default mode
                )
                retriever.persist(self.retriever_save_path)
        else:
            retriever = VectorIndexRetriever(
                index=self.vector_index, similarity_top_k=similarity_top_k
            )

        if self.retriever_type == "ensemble":
            vector_retriever = VectorIndexRetriever(
                index=self.vector_index, similarity_top_k=similarity_top_k
            )
            retriever = CustomRetriever(vector_retriever, retriever)

        return retriever

    def build_engine(self):
        retriever = self.build_retriever()
        response_synthesizer = get_response_synthesizer(
            service_context=self.service_context,
            response_mode="tree_summarize",
        )
        if self.reranker:
            rag_query_engine = RetrieverQueryEngine(
                retriever=retriever,
                response_synthesizer=response_synthesizer,
                node_postprocessors=[self.reranker],
            )
        else:
            rag_query_engine = RetrieverQueryEngine(
                retriever=retriever,
                response_synthesizer=response_synthesizer,
            )

        rag_query_engine_rewrite = None
        if self.rewriting and self.rewriting == "hyde":
            hyde = HyDEQueryTransform(include_original=True)
            rag_query_engine_rewrite = TransformQueryEngine(rag_query_engine, hyde)
        if self.rewriting and self.rewriting == "multi-step":
            step_decompose_transform = StepDecomposeQueryTransform(
                llm=self.llm, verbose=True
            )
            index_summary = "used for answer questions"
            rag_query_engine_rewrite = MultiStepQueryEngine(
                query_engine=rag_query_engine,
                query_transform=step_decompose_transform,
                index_summary=index_summary,
            )
        return rag_query_engine, rag_query_engine_rewrite, retriever

    def update_template(self, template_usage=None):
        if template_usage:
            new_summary_tmpl = PromptTemplate(template_usage)
            self.rag_query_engine.update_prompts(
                {"response_synthesizer:summary_template": new_summary_tmpl}
            )

    def get_response_dataset(self, qa_set_path, qa_set_response_path, test_size, retrival_only=False):
        questions = dict()
        with open(qa_set_path, "r") as f:
            data = json.load(f)
        if "question" in data:
            questions["answerable"] = data["question"]
        else:
            for key in data:
                questions[key] = data[key]
        questions_save = []
        answers_save = []
        count = 0
        for key in questions:
            for q in questions[key]:
                if type(q) == str:
                    if not retrival_only:
                        try:
                            answer = self.rag_query_engine_rewrite.query(q)
                            if answer.strip() == "Empty Response":
                                answer = self.rag_query_engine.query(q)
                        except:
                            try:
                                answer = self.rag_query_engine.query(q)
                            except:
                                answer = "No answer."
                        questions_save.append(q)
                        answers_save.append(str(answer).strip())
                    else:
                        retrieve_nodes = self.retriever._retrieve(q)
                        nodes = [node.text for node in retrieve_nodes]
                        questions_save.append(q)
                        answers_save.append(nodes)
                    count += 1
                    if count >= test_size:
                        break
            if count >= test_size:
                break

        with open(qa_set_response_path, "w") as f:
            json.dump({"answer": answers_save, "question": questions_save}, f)