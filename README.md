# Unanswerability Evaluation for Retrieval Augmented Generation

Paper: [Arxiv Link](https://arxiv.org/abs/2412.12300)

Existing evaluation frameworks for retrieval-augmented generation (RAG) systems focus on answerable queries, but they overlook the importance of appropriately rejecting unanswerable requests. 
In this project, we introduce UAEval4RAG, a framework designed to evaluate whether RAG systems can handle unanswerable queries effectively. 
We define a taxonomy with six unanswerable categories, and UAEval4RAG automatically synthesizes diverse and challenging queries for any given knowledge base with unanswered ratio and acceptable ratio metrics.
We conduct experiments with various RAG components, including retrieval models, rewriting methods, rerankers, language models, and prompting strategies, and reveal hidden trade-offs in performance of RAG systems. 
Our findings highlight the critical role of component selection and prompt design in optimizing RAG systems to balance the accuracy of answerable queries with high rejection rates of unanswerable ones. 
UAEval4RAG provides valuable insights and tools for developing more robust and reliable RAG systems.

## Setup

```ruby
pyenv virtualenv 3.11 unans-rage
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate unans-rage
pip install -r requirements.txt
```

## Usage
### Generate unanswerable queries
#### 1. For the first five category

1. You need to have a OpenAI key `export OPENAI_API_KEY='yourkey'`
2. Check `./src/taxonomy/unanswerable_generation.py` for example

```python
# 1. Specify the contribution of different categories.
contribution = {
    "incomprehensible": 0.2,
    "false_presuppositions": 0.2,
    "underspecified": 0.2,
    "safety-concern": 0.2,
    "modality-limited": 0.2,
}

# 2. Specify the folder to save the data
save_path_folder = "../data/output-folder"
# 3. Specify the database folder
folder = "ur-path-to/database"
# 4. Specify the test size you want. (Total number of the dataset samples)
test_size = 300
await generate_unanswerable_batch(
    folder=folder,
    test_size=test_size,
    contribution=contribution,
    save_path_folder=save_path_folder,
    generator_llm="gpt-4o"
)
```
#### 2. For the OOD category
1. You need to have a OpenAI key `export OPENAI_API_KEY='yourkey'`
2. Check example in `./src/ood/tenant_dataset_main.py`

### Evaluation
1. You need to have a OpenAI key `export OPENAI_API_KEY='yourkey'`
2. Check example in `./src/taxonomy/eval_unanswerable_harness.py`

## Citation

```ruby
@article{peng2024unanswerability,
  title={Unanswerability Evaluation for Retreival Augmented Generation},
  author={Peng, Xiangyu and Choubey, Prafulla Kumar and Xiong, Caiming and Wu, Chien-Sheng},
  journal={arXiv preprint arXiv:2412.12300},
  year={2024}
}
```