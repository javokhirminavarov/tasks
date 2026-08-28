# Embedding-Only Commodity Grouping Experiment

`commodity_grouping_embedding_only.ipynb` tests whether the pre-computed Qdrant dense
embeddings (`dense__dense`, 1024-dim, L2-normalized) can group similar goods
descriptions **within each HS10 code**, and whether those description groups make
`PRICE_KG` comparison populations more homogeneous than the current
`HS10 + origin + transport` approach.

The experiment is embedding-only by design: no new embeddings are generated, no
TF-IDF/SVD/lexical features are used, and price/country/transport never enter the
clustering — price is evaluated only after the groups exist.

## Setup

```bash
pip install -r requirements.txt
```

## Data

Place the Qdrant parquet exports (columns `point_id`, `payload_json`, `dense__dense`)
in `data/` next to the notebook, or edit `DATA_DIR` in the configuration cell.
`data/`, `cache/`, and `outputs/` are gitignored.

## Run

Open the notebook in Jupyter and run it cell by cell. The configuration cell at the
top controls the HS10 selection, the k-sweep range, the evaluation thresholds, and
caching. Expensive steps (hierarchy building, k-sweeps) are cached under `cache/`
per HS10 and configuration fingerprint.

## Outputs

- `outputs/commodity_groups_embedding_only.parquet` — row-level group assignments
- `outputs/hs10_grouping_evaluation.csv` — per-HS10 evaluation summary
