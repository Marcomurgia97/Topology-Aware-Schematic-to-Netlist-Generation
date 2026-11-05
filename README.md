# Topology-Aware Schematic-to-Netlist Generation

Code, data and model outputs for the paper:

> **Topology-Aware Schematic-to-Netlist Generation: A Comparative Study of Single-Stage and Two-Stage Vision–Language Pipelines**
> Marco Murgia, Alberto Pes, Diego Reforgiato Recupero, Giuseppe Scarpi
> University of Cagliari · R2M Solution s.r.l.

The paper studies how to turn circuit schematic images into SPICE netlists with Vision-Language Models (VLMs) and Large Language Models (LLMs). It compares two zero-shot paradigms:

- **Single-Stage (VLM only):** a VLM reads the schematic image and writes the SPICE netlist directly.
- **Two-Stage (VLM + LLM):** a VLM first writes a structured plain-text description of the circuit topology (*Phase 1: Visual Description*). An LLM then turns that description into a valid SPICE netlist (*Phase 2: Syntactic Refinement*).

Generated netlists are scored with a **topology-aware metric based on Graph Edit Distance (GED)**. Each netlist becomes a bipartite component–net graph with pin-labelled edges, so the score does not depend on how components and nets are named.

---

## Repository structure

```
.
├── annotated_dataset/
│   ├── images/          # 50 schematic images (.jpg / .png)
│   └── netlists/        # 50 manually verified ground-truth SPICE netlists (.cir)
├── single_stage/
│   ├── gemini_generator.py      # Single-stage generation with Gemini (gemini-3-pro-preview)
│   └── chatGPT_generator.py     # Single-stage generation with ChatGPT (gpt-5)
├── double_stage/
│   ├── description/
│   │   └── gemini_generator_description.py   # Phase 1: image -> textual description (Gemini)
│   └── chatGPT_generator_description.py      # Phase 2: description -> SPICE netlist (gpt-5)
├── open_weight_notebooks/                    # Google Colab notebooks for the open-weight models
│   ├── single_stage/
│   │   └── GLM_single_stage.ipynb            # Single-stage generation with GLM-4.6V-Flash
│   └── double_stage/
│       ├── GLM_phase1_description.ipynb      # Phase 1: image -> textual description (GLM-4.6V-Flash)
│       └── Qwen3_phase2_netlist.ipynb        # Phase 2: description -> SPICE netlist (Qwen3-8B)
└── evaluation/
    ├── evaluation_graph.py   # Netlist-to-graph parser + GED comparator (NetworkX)
    ├── create_results.py     # Scores one output folder against the ground truth -> results/*.json
    ├── dev_standard.py       # Aggregate statistics, std, perfect matches, Z-score outlier analysis
    ├── outputs/              # Raw outputs of every pipeline (descriptions and netlists)
    └── results/              # Per-circuit GED / similarity results for each pipeline
```

### Dataset

`annotated_dataset/` holds the curated test set used in the paper: **50 circuits**, taken mostly from [AMSNet](https://arxiv.org/abs/2405.09045). They were chosen for visual clarity, component coverage and structural consistency. A domain expert in electronic circuit design **checked every netlist by hand** against its schematic and fixed problems in the original annotations, such as swapped source/drain terminals or missing bulk connections.

The circuits range from fully passive networks to topologies with up to 13 active devices. Most use MOSFETs, a few use BJTs or vacuum tubes, and many include resistors, capacitors and inductors. Each image `images/<id>.<ext>` has a matching netlist `netlists/<id>.cir`.

### Pipeline outputs

`evaluation/outputs/` contains the raw outputs behind the paper's results:

| Folder | Paradigm | Phase 1 (VLM) | Phase 2 (LLM) |
|---|---|---|---|
| `gemini_single_stage` | Single-Stage | Gemini 3 Pro | – |
| `gpt_5_single_stage` | Single-Stage | GPT-5 | – |
| `GLM_single_stage` | Single-Stage | GLM-4.6V-Flash | – |
| `gemini_description` | Two-Stage, Phase 1 | Gemini 3 Pro | – |
| `GLM_description` | Two-Stage, Phase 1 | GLM-4.6V-Flash | – |
| `gemini_gpt_5_two_stage` | Two-Stage | Gemini 3 Pro | GPT-5 |
| `gemini_qwen__double_stage` | Two-Stage | Gemini 3 Pro | Qwen3-8B |
| `GLM_gpt_5_two_stage` | Two-Stage | GLM-4.6V-Flash | GPT-5 |
| `GLM_qwen_double_stage` | Two-Stage | GLM-4.6V-Flash | Qwen3-8B |

GLM-4.6V-Flash and Qwen3-8B ran on an NVIDIA L4 GPU in Google Colab with greedy decoding and up to 8192 new tokens. The notebooks are in `open_weight_notebooks/` (see [Open-weight models](#open-weight-models-colab)).

---

## Installation

Requires Python 3.9+.

```bash
git clone https://github.com/Marcomurgia97/Topology-Aware-Schematic-to-Netlist-Generation.git
cd Topology-Aware-Schematic-to-Netlist-Generation
pip install openai google-genai networkx numpy pandas
```

The generation scripts read API keys from environment variables:

```bash
export OPEN_API_KEY="..."     # OpenAI (note: OPEN_API_KEY, not OPENAI_API_KEY)
export GEMINI_API_KEY="..."   # Google Gemini
```

## Usage

The scripts use relative paths, so **run each one from inside its own folder**. Input and output folders, plus the model or experiment name, are set as variables at the top of each script. Output folders are created automatically.

### 1. Single-Stage generation

```bash
cd single_stage
python gemini_generator.py      # -> ../output_gemini_netlist/
python chatGPT_generator.py     # -> ../output_gpt_5_single_stage/
```

Every image in `annotated_dataset/images/` produces one netlist `.txt` file.

### 2. Two-Stage generation

**Phase 1:** image to textual description:

```bash
cd double_stage/description
python gemini_generator_description.py   # -> double_stage/descriptions/gemini/
```

**Phase 2:** description to SPICE netlist. The script reads `double_stage/descriptions/<model>/`. `model` defaults to `gemini`. To refine descriptions from another VLM, put them in `descriptions/<name>/` and change `model` at the top of the script. For example, copy `evaluation/outputs/GLM_description/` to `descriptions/GLM/` and set `model = 'GLM'`.

```bash
cd double_stage
python chatGPT_generator_description.py  # -> ../output_<model>_gpt_5_two_stage/
```

All API calls use deterministic decoding (temperature 0), so one run per circuit is enough.

### Open-weight models (Colab)

The open-weight pipelines are Google Colab notebooks in `open_weight_notebooks/`. They were run on an NVIDIA L4 GPU. Each notebook installs its dependencies, mounts Google Drive, loads the model from Hugging Face and processes every file in an input folder:

| Notebook | Model | Input | Output |
|---|---|---|---|
| `single_stage/GLM_single_stage.ipynb` | `zai-org/GLM-4.6V-Flash` | schematic images | SPICE netlists |
| `double_stage/GLM_phase1_description.ipynb` | `zai-org/GLM-4.6V-Flash` | schematic images | textual descriptions |
| `double_stage/Qwen3_phase2_netlist.ipynb` | `Qwen/Qwen3-8B` | textual descriptions | SPICE netlists |

To run one:
1. Upload `annotated_dataset/images/` to your Google Drive, or for Phase 2 the descriptions folder.
2. Set `image_directory` (or `files_directory`) in the last cell to that Drive path.
3. Run all cells. Outputs go to `results/` in the Colab runtime.

The notebooks generate with a **thinking budget**: greedy decoding, 6000 tokens for reasoning and 8192 new tokens in total. If the model hits the budget before closing its `</think>` block, the notebook appends a short instruction that ends the reasoning and asks for the final answer only. This keeps the model from looping.

### 3. Evaluation

```bash
cd evaluation
```

**Score one pipeline.** Set `entity` (the name of the results file) and `path` (the output folder to score, for example `outputs/gemini_single_stage`) in `create_results.py`, then run:

```bash
python create_results.py        # -> results/<entity>.json
```

Each entry in the results file holds the GED, a text report of the errors found, and the topological similarity (`sim`).

**Aggregate statistics** over all pipelines:

```bash
python dev_standard.py
```

It prints the mean similarity, NGED, similarity standard deviation and number of perfect matches for each pipeline. It does this on all 50 circuits and again after removing outliers with |Z| > 3.

---

## Evaluation metric

`evaluation/evaluation_graph.py` turns each netlist into an undirected bipartite graph *G = (V<sub>c</sub>, V<sub>n</sub>, E)*:

- **Component nodes** keep the device type (M, R, C, L, Q, D, …).
- **Net nodes** are the electrical nodes. Their names are ignored.
- **Edges** link components to nets and carry a pin label (for example `d`/`g`/`s`/`b` for MOSFETs and `c`/`b`/`e` for BJTs), so a swapped drain and source counts as an error.
- Independent voltage and current sources (`V`, `I`) and device parameters (W, L, values) are left out, so the score covers only the circuit's active and passive core.

GED uses these edit costs:

| Operation | Cost |
|---|---|
| Component insertion / deletion | 10 |
| Component type substitution | 10 |
| Edge insertion / deletion | 10 |
| Component renaming (RefDes) | 0 |
| Net insertion / deletion | 0.1 |

The raw GED is then normalised into a scale-invariant similarity:

$$
\text{Similarity}(G_{gt}, G_{gen}) = 1 - \frac{\text{GED}(G_{gt}, G_{gen})}{C_{max}}, \qquad
C_{max} = \text{Cost}(G_{gen} \to \emptyset) + \text{Cost}(\emptyset \to G_{gt})
$$

NGED = 1 − Similarity.

---

## Citation

If you use this code or dataset, please cite:

```bibtex
@article{murgia2026topology,
  title   = {Topology-Aware Schematic-to-Netlist Generation: A Comparative Study of Single-Stage and Two-Stage Vision--Language Pipelines},
  author  = {Murgia, Marco and Pes, Alberto and Reforgiato Recupero, Diego and Scarpi, Giuseppe},
  year    = {2026},
  note    = {Under review}
}
```

## Acknowledgements

The schematics and reference netlists come mostly from the [AMSNet](https://arxiv.org/abs/2405.09045) dataset and were then verified and corrected by hand.

## Contact

- Diego Reforgiato Recupero (corresponding author): diego.reforgiato@unica.it
- Marco Murgia: marco.murgia3@unica.it
- Alberto Pes: alberto.pes@r2msolution.com
- Giuseppe Scarpi: giuseppe.scarpi@r2msolution.com
