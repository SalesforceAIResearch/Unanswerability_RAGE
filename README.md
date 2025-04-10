# Setup

```ruby
pyenv virtualenv 3.11 unans-rage
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate unans-rage
pip install -r requirements.txt
```

# Usage
## Generate unanswerable queries
### For the first five category

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
### For the OOD category
1. You need to have a OpenAI key `export OPENAI_API_KEY='yourkey'`
2. Check example in `./src/ood/tenant_dataset_main.py`

## Evaluation
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