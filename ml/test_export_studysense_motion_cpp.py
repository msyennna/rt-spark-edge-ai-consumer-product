"""Unit-test the C++ tree-export algorithm with toy SOFTWARE fixtures ONLY.

The toy values are *not* real readings and NEVER become a StudySense model,
training set, reported test accuracy, or embedded firmware artifact.
"""
from __future__ import annotations
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from export_studysense_motion_cpp import LABELS, extract_nodes, predict_exported_nodes, render_header


def main():
    # Intentionally artificial test fixture for code correctness, not model training.
    X = np.array([
        [100, 65, 150, 30.0, 70], [120, 70, 200, 30.1, 70],
        [430, 70, 145, 31.0, 69], [490, 90, 180, 32.0, 68],
        [430, 160, 750, 32.0, 68], [490, 280, 1200, 32.0, 69],
    ], dtype=np.float32)
    y = np.array(['IMPROVE_LIGHTING', 'IMPROVE_LIGHTING',
                  'STUDY_READY', 'STUDY_READY',
                  'DESK_DISTURBANCE', 'DESK_DISTURBANCE'])
    candidate = DecisionTreeClassifier(max_depth=4, random_state=42).fit(X, y)
    nodes = extract_nodes(candidate)
    assert 'kTrained = true' in render_header(candidate)
    rng = np.random.default_rng(4)
    random_cases = rng.uniform(low=[0, 0, 0, 15, 20], high=[700, 400, 4000, 45, 90], size=(256, 5)).astype(np.float32)
    all_cases = np.vstack([X, random_cases])
    predicted = candidate.predict(all_cases)
    exported = [LABELS[predict_exported_nodes(nodes, row)] for row in all_cases]
    assert list(predicted) == exported, 'Python model/exported tree parity FAILED'
    print('PASS: 262 toy fixture cases match the exported-tree evaluator.')
    print('No real StudySense model was trained or deployed; current data remains untouched.')


if __name__ == '__main__':
    main()
