import json
import pandas as pd
import numpy as np

MODELS = {
    "Gemini_Single": "results/gemini_single_stage.json",
    "Gemini_ChatGPT": "results/gemini_gpt_5_two_stage.json",
    "Gemini_Qwen": "results/gemini_qwen__double_stage.json",
    "ChatGPT_Single": "results/gpt_5_single_stage.json",
    "GLM_Single": "results/GLM_single_stage.json",
    "GLM_ChatGPT": "results/GLM_gpt_5_two_stage.json",
    "GLM_Qwen": "results/GLM_qwen_double_stage.json",
}


def load_and_clean_data(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    clean_data_ged = {}
    clean_data_sim = {}
    for key, val in data.items():
        if key.startswith("avg_"): continue

        clean_key = str(key).replace('_netlist_from_descr', '') \
            .replace('_description', '') \
            .replace('.jpg', '') \
            .replace('.png', '')

        clean_key = clean_key.strip().lower()

        clean_data_ged[clean_key] = val.get('GED', float('nan'))
        clean_data_sim[clean_key] = val.get('sim', 0.0)
    return clean_data_ged, clean_data_sim


df_dict = {}
for model_name, filepath in MODELS.items():
    ged_dict, sim_dict = load_and_clean_data(filepath)
    df_dict[f"{model_name}_GED"] = pd.Series(ged_dict)
    df_dict[f"{model_name}_SIM"] = pd.Series(sim_dict)

df = pd.DataFrame(df_dict)

df = df.fillna({col: 0.0 for col in df.columns if col.endswith("_SIM")})

ged_cols = [c for c in df.columns if c.endswith("_GED")]
sim_cols = [c for c in df.columns if c.endswith("_SIM")]


def generate_summary(dataframe):
    summary = []
    for model in MODELS.keys():
        ged_col = f"{model}_GED"
        sim_col = f"{model}_SIM"

        mean_ged = dataframe[ged_col].mean()
        mean_sim = dataframe[sim_col].mean()

        std_sim = dataframe[sim_col].std() * 100
        nged = (1 - mean_sim) * 100

        perfect_matches = (dataframe[ged_col] == 0).sum()
        total_circuits = len(dataframe)

        summary.append({
            "Model": model,
            "SIM (Mean)": f"{mean_sim * 100:.2f}%",
            "SIM (Std)": f"{std_sim:.2f}%",
            "NGED (%)": f"{nged:.2f}%",
            "GED (Mean)": round(mean_ged, 2),
            "Perfect Matches": f"{perfect_matches}/{total_circuits}"
        })
    return pd.DataFrame(summary).sort_values(by="NGED (%)")


print("=" * 80)
print(f"=== STATISTICHE INIZIALI GREZZE (Su {len(df)} circuiti totali) ===")
print("=" * 80)

if len(df) > 50:
    print("ATTENZIONE: Il numero di circuiti è ancora superiore a 50. Ci sono ancora nomi disallineati.")
    print("Circuiti trovati:", list(df.index))
    print("-" * 80)

summary_raw = generate_summary(df)
print(summary_raw.to_string(index=False))

outlier_mask = pd.Series(False, index=df.index)
soglia_sigma = 3

for col in sim_cols:
    z_score = (df[col] - df[col].mean()) / df[col].std()
    outlier_mask = outlier_mask | (z_score.abs() > soglia_sigma)

outliers = df[outlier_mask]

print("\n" + "=" * 80)
print(f"=== OUTLIER TROVATI (Rimossi da tutti i modelli per equità) ===")
print("=" * 80)
if not outliers.empty:
    print(f"Trovati {len(outliers)} circuiti anomali: {list(outliers.index)}")
else:
    print("Nessun outlier statistico trovato.")

df_clean = df[~outlier_mask]

print("\n" + "=" * 80)
print(f"=== STATISTICHE DOPO PULIZIA OUTLIER (Su {len(df_clean)} circuiti) ===")
print("=" * 80)
summary_clean = generate_summary(df_clean)
print(summary_clean.to_string(index=False))

print("\n" + "=" * 80)
print("=== LEADERBOARD FINALE (Basata su NGED / Errore Topologico Normalizzato) ===")
print("=" * 80)
for i, row in enumerate(summary_clean.itertuples(), 1):
    print(f"{i}. {row.Model:<15} -> NGED: {row._4:<7} | SIM Std: {row._3:<7} | Match Perfetti: {row._6}")