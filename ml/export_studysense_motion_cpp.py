"""Export an ACTUALLY trained StudySense sklearn tree to STM32-compatible C++.

This script NEVER trains on pilot data or generates fabricated training samples.
It checks real split counts before export, and refuses absent/unsupported models.

After 30+ training and 10+ held-out test trials PER CLASS:
  .\\.venv\\Scripts\\python.exe ml\\train_studysense_motion.py
  .\\.venv\\Scripts\\python.exe ml\\export_studysense_motion_cpp.py --output C:\\Users\\Yena\\rt-spark-studysense-logger\\include\\studysense_model_generated.h

Class ID order: 0=STUDY_READY, 1=IMPROVE_LIGHTING, 2=DESK_DISTURBANCE.
Inputs are the FIVE feature columns from the real trial builder, in exact order.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'data' / 'studysense_motion_windows.csv'
MODEL = ROOT / 'models' / 'studysense_motion_tree.joblib'
FEATURES = ['als_mean', 'motion_mean_delta_mean', 'motion_peak_delta_max', 'temperature_c', 'humidity_pct']
LABELS = ['STUDY_READY', 'IMPROVE_LIGHTING', 'DESK_DISTURBANCE']
LABEL_IDS = {name: i for i, name in enumerate(LABELS)}


def require_training_counts(path: Path = DATASET) -> dict[str, int]:
    if not path.is_file():
        raise ValueError(f'Real dataset missing: {path}')
    df = pd.read_csv(path)
    required = {'split', 'label', 'trial_id', 'session_id', *FEATURES}
    missing = required.difference(df.columns)
    if missing or df.empty:
        raise ValueError(f'Dataset empty or missing columns {sorted(missing)}')
    if df[list(required)].isnull().any().any() or df.duplicated(['session_id', 'trial_id']).any():
        raise ValueError('Dataset has missing metadata or repeated physical trial IDs')
    if not df['split'].isin(['train', 'test', 'final']).all() or not df['label'].isin(LABELS).all():
        raise ValueError('Unexpected split or class label')
    if (df.groupby('session_id')['split'].nunique() > 1).any():
        raise ValueError('Same physical session appears in more than one split')
    for name in FEATURES:
        if not np.isfinite(pd.to_numeric(df[name], errors='coerce').to_numpy(dtype=float)).all():
            raise ValueError(f'Nonfinite feature in dataset: {name}')
    counts = {}
    for label in LABELS:
        for split, minimum in [('train', 30), ('test', 10)]:
            count = int(((df['split'] == split) & (df['label'] == label)).sum())
            counts[f'{split}/{label}'] = count
            if count < minimum:
                raise ValueError(f'{label}: {split} {count}/{minimum} independent trials. Export blocked.')
    return counts


def load_checked_model(path: Path = MODEL) -> DecisionTreeClassifier:
    if not path.is_file():
        raise ValueError(f'Trained model missing: {path}; pilot data alone is not enough to train it.')
    # joblib/pickle loads code: use only a file YOU created with the local training script.
    payload = joblib.load(path)
    if not isinstance(payload, dict) or payload.get('features') != FEATURES or payload.get('labels') != LABELS:
        raise ValueError('Model metadata/feature order/labels do not match StudySense Stage 2')
    if payload.get('sensor_window_count') != 5:
        raise ValueError('Model window size must be five consecutive 2-second snapshots')
    model = payload.get('model')
    if not isinstance(model, DecisionTreeClassifier) or not hasattr(model, 'tree_'):
        raise ValueError('Expected a fitted sklearn DecisionTreeClassifier')
    if model.n_features_in_ != 5 or len(model.classes_) != 3 or set(model.classes_) != set(LABELS):
        raise ValueError('Unexpected decision-tree input dimension or output classes')
    if model.get_depth() > 12 or model.tree_.node_count > 1024:
        raise ValueError('Tree too large for the bounded MCU evaluator')
    return model


def extract_nodes(model: DecisionTreeClassifier) -> list[tuple[int, float, int, int, int]]:
    tree = model.tree_
    class_to_id = [LABEL_IDS[str(label)] for label in model.classes_]
    nodes = []
    for i in range(tree.node_count):
        feature = int(tree.feature[i]); left = int(tree.children_left[i]); right = int(tree.children_right[i])
        if feature < 0:
            if left != -1 or right != -1:
                raise ValueError(f'Invalid leaf pointers at node {i}')
            best = int(np.argmax(tree.value[i].reshape(-1)))
            nodes.append((-1, 0.0, -1, -1, class_to_id[best]))
        else:
            threshold = float(tree.threshold[i])
            if not (0 <= feature < len(FEATURES) and np.isfinite(threshold)):
                raise ValueError(f'Invalid feature/threshold at node {i}')
            if not (0 <= left < tree.node_count and 0 <= right < tree.node_count):
                raise ValueError(f'Invalid child index at node {i}')
            nodes.append((feature, threshold, left, right, 255))
    return nodes


def render_header(model: DecisionTreeClassifier) -> str:
    nodes = extract_nodes(model)
    rows = []
    for feature, threshold, left, right, class_id in nodes:
        double_text = f'{threshold:.17g}'
        if '.' not in double_text and 'e' not in double_text:
            double_text += '.0'
        rows.append(f'    {{{feature}, {left}, {right}, {double_text}, {class_id}u}},')
    return '\n'.join([
        '#pragma once',
        '#include <stdint.h>',
        '// GENERATED from a real trained sklearn DecisionTreeClassifier.',
        '// Treat as CANDIDATE until tested on held-out trials and on the STM32.',
        '// Feature order: ALS mean, motion mean delta mean, motion peak delta max,',
        '// temperature C, relative humidity percent. FIVE 2-s snapshots each.',
        '// Class IDs: 0=STUDY_READY, 1=IMPROVE_LIGHTING, 2=DESK_DISTURBANCE.',
        'namespace studysense_ml {',
        'static const bool kTrained = true;',
        'static const char kModelDescription[] = "SKLEARN_TREE_CANDIDATE";',
        'struct Node { int16_t feature; int16_t left; int16_t right; double threshold; uint8_t class_id; };',
        f'static const Node kNodes[{len(nodes)}] = {{',
        *rows,
        '};',
        'inline uint8_t Predict(const float features[5]) {',
        '    int node = 0;',
        f'    for (unsigned depth = 0; depth < {len(nodes)}u; ++depth) {{',
        '        if (node < 0 || node >= static_cast<int>(sizeof(kNodes) / sizeof(kNodes[0]))) return 255u;',
        '        const Node &current = kNodes[node];',
        '        if (current.feature < 0) return current.class_id;',
        '        const double value = static_cast<double>(features[current.feature]);',
        '        node = (value <= current.threshold) ? current.left : current.right;',
        '    }',
        '    return 255u;',
        '}',
        '}',
        '',
    ])


def predict_exported_nodes(nodes: list[tuple[int, float, int, int, int]], values: np.ndarray) -> int:
    """Software test oracle mirroring generated C++ evaluator; NOT product inference."""
    features = np.asarray(values, dtype=np.float32)
    node = 0
    for _ in range(len(nodes)):
        feature, threshold, left, right, cls = nodes[node]
        if feature < 0:
            return cls
        node = left if float(features[feature]) <= threshold else right
    raise AssertionError('Invalid/cyclic generated tree')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='Target firmware/include/studysense_model_generated.h')
    parser.add_argument('--force', action='store_true', help='Replace an already trained exported header')
    args = parser.parse_args()
    try:
        counts = require_training_counts()
        model = load_checked_model()
        # Validate the generated evaluator on actual examples; this does NOT replace MCU tests.
        df = pd.read_csv(DATASET)
        # Leave the final evaluation split untouched until final product trials.
        df = df[df["split"].isin(["train", "test"])]
        X = df[FEATURES].to_numpy(dtype=np.float32)
        expected = model.predict(X)
        nodes = extract_nodes(model)
        actual = [LABELS[predict_exported_nodes(nodes, row)] for row in X]
        if list(expected) != actual:
            raise ValueError('Export prediction mismatch on real dataset; refusing to write header')
        target = args.output.resolve()
        if target.name != 'studysense_model_generated.h' or target.parent.name != 'include':
            raise ValueError('Output must be firmware/include/studysense_model_generated.h')
        if target.is_file() and not args.force:
            contents = target.read_text(encoding='utf-8')
            if 'UNTRAINED_PLACEHOLDER' not in contents:
                raise ValueError('Output already contains a model; use --force deliberately after reviewing the diff')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_header(model), encoding='utf-8', newline='\n')
        print('Exported C++ candidate model:', target)
        print('Training/test counts:', counts)
        print('Host prediction parity on recorded dataset: PASS')
        print('NOT YET VERIFIED: live STM32 output, >=50 MCU latency measurements, final product trials.')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        sys.exit('EXPORT BLOCKED: ' + str(exc))


if __name__ == '__main__':
    main()
