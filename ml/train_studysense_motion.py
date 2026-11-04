"""Train candidate StudySense light+motion classifier from real physical trials.

Host-only: you must still export/test inference code on the STM32.
"""
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.tree import DecisionTreeClassifier

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'studysense_motion_windows.csv'
MODEL=ROOT/'models'/'studysense_motion_tree.joblib'
LABELS=['STUDY_READY','IMPROVE_LIGHTING','DESK_DISTURBANCE']
FEATURES=['als_mean','motion_mean_delta_mean','motion_peak_delta_max','temperature_c','humidity_pct']
LIGHT=['als_mean']
MOTION=['motion_mean_delta_mean','motion_peak_delta_max']


def fail(s):
    sys.exit('ERROR: '+s)


def evaluate(name,labels,preds):
    print('\n'+name)
    print('Accuracy:',f'{accuracy_score(labels,preds):.3f}')
    print(classification_report(labels,preds,labels=LABELS,zero_division=0))
    print('Confusion matrix (rows true / columns predicted):')
    print('Order:',LABELS)
    print(confusion_matrix(labels,preds,labels=LABELS))


def main():
    if not DATA.is_file():
        fail(f'Dataset missing: {DATA}. Capture physical trials and run the builder first.')
    df=pd.read_csv(DATA)
    required=['session_id','trial_id','split','label',*FEATURES]
    if df.empty or any(c not in df for c in required):
        fail('CSV empty or missing required columns')
    if df[required].isna().any().any():
        fail('Missing values in trial metadata/features')
    if not df['split'].isin(['train','test','final']).all() or not df['label'].isin(LABELS).all():
        fail('Unknown split or label')
    if df.duplicated(['session_id','trial_id']).any():
        fail('Duplicate trial')
    if (df.groupby('session_id')['split'].nunique()>1).any():
        fail('Session occurs across splits; leakage')
    for f in FEATURES:
        df[f]=pd.to_numeric(df[f],errors='coerce')
    if not np.isfinite(df[FEATURES].to_numpy(dtype=float)).all():
        fail('Nonfinite feature')
    train=df[df.split=='train']
    test=df[df.split=='test']
    final=df[df.split=='final']
    print('Physical trials per split/class:')
    print(df.groupby(['split','label']).size().to_string())
    missing=[]
    for cls in LABELS:
        a=int((train.label==cls).sum()); b=int((test.label==cls).sum())
        f=int((final.label==cls).sum())
        if a<30 or b<10:
            missing.append(f'{cls}: train {a}/30, held-out test {b}/10')
        if f<20:
            print(f'Final product trials still required: {cls} {f}/20')
    if missing:
        fail('Collect independent trials before training:\n  '+'\n  '.join(missing))
    model=DecisionTreeClassifier(max_depth=4,min_samples_leaf=3,random_state=42)
    model.fit(train[FEATURES],train.label)
    evaluate('Combined light+motion+environment model',test.label,model.predict(test[FEATURES]))
    for name,features in [('Light-only baseline',LIGHT),('Motion-only baseline',MOTION)]:
        base=DecisionTreeClassifier(max_depth=4,min_samples_leaf=3,random_state=42)
        base.fit(train[features],train.label)
        evaluate(name,test.label,base.predict(test[features]))
    print('\nFeature importances (not proof of causal contribution):')
    for name,value in zip(FEATURES,model.feature_importances_):
        print(name,round(float(value),3))
    print('No model tuning on final trials. Environmental inputs do not automatically add accuracy.')
    MODEL.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({'model':model,'labels':LABELS,'features':FEATURES,'sensor_window_count':5},MODEL)
    print('Host-only candidate saved:',MODEL)
    print('NEXT: implement same features and tested decision tree in STM32 C/C++ (not yet done).')

if __name__=='__main__':
    main()
