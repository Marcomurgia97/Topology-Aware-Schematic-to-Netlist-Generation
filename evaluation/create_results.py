import json
import os
import numpy as np
from evaluation_graph import NetlistParser, NetlistGEDComparator

entity = 'GLM_gpt_5_two_stage' #example
path = 'outputs/GLM_gpt_5_two_stage'
gold_dir = '../../annotated_dataset/netlists'
results = {}

for file in os.scandir(path):
    if not file.name.endswith('.txt'):
        continue

    filename_no_ext = file.name.rsplit('.', 1)[0]
    base_id = filename_no_ext.split('_')[0]
    gold_path = os.path.join(gold_dir, f'{base_id}.cir')

    if os.path.exists(gold_path):
        with open(gold_path, 'r', encoding='utf-8') as f:
            golden_net_str = f.read()
        with open(file.path, 'r', encoding='utf-8') as f:
            gen_net_str = f.read()

        g_golden = NetlistParser(golden_net_str).parse()
        g_gen = NetlistParser(gen_net_str).parse()

        comparator = NetlistGEDComparator(g_golden, g_gen)
        comparator.compare()
        report, ged = comparator.get_report()

        results[filename_no_ext] = {'GED': int(ged), 'report':report}

if results:
    with open(f'results/{entity}.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


