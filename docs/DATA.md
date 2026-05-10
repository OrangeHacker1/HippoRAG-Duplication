# Datasets

> Every dataset used by the project must be listed here with source, version,
> license, and download command. Datasets must NOT be committed to the repo.


## Dataset 1: hipporag-eval-multihop

- **License:** Project-specific (original content)
- **Size:** 10 corpus documents, 4 multi-hop questions
- **Cite as:** [recommended citation if any]

### Description

A hand-authored multi-hop evaluation dataset. Each question requires connecting facts from at least two separate documents. The corpus covers scientists (Marie Curie, Albert Einstein, Isaac Newton) and their birthplaces, awards, and contributions.

### Schema

**CORPUS** — `List[str]`: Raw document strings used to build the knowledge graph.

**QUESTIONS** — `List[dict]` with keys:
- `question` (str): The natural language question.
- `gold_docs` (List[str]): The exact corpus documents needed to answer correctly.
- `gold_answers` (List[str]): Acceptable answer strings.

### No Download Required

The dataset is bundled in `data/eval_dataset.py`. Running `make download-data` prints a confirmation message.

### Preprocessing

[Document any preprocessing applied before training/indexing. The
preprocessing must be deterministic given the seed in grading/manifest.yaml.]



## Dataset 1: [name] TEMPLATE

- **Source URL:** https://example.com/dataset
- **Version:** YYYY-MM-DD or release tag
- **sha256:** [computed hash of the downloaded archive]
- **License:** [e.g. CC BY 4.0, public domain, custom]
- **Size:** [e.g. 2.4 GB compressed]
- **Cite as:** [recommended citation if any]

### Download

```bash
make download-data
```

Or manually:

```bash
mkdir -p data/raw
curl -L -o data/raw/dataset.tar.gz https://example.com/dataset.tar.gz
echo "<expected sha256>  data/raw/dataset.tar.gz" | sha256sum -c -
tar -xzf data/raw/dataset.tar.gz -C data/
```

### Preprocessing

[Document any preprocessing applied before training/indexing. The
preprocessing must be deterministic given the seed in grading/manifest.yaml.]
