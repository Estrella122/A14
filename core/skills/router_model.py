"""Trained character TF-IDF / linear classifier. Inference needs only stdlib.

The JSON artifact is data, never pickle. Probability and lexical coverage are
reported separately: a closed-set score is not a guarantee of correctness.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path(__file__).parent / 'models' / 'skill_router.json.gz'

def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text).lower()).strip()

def char_features(text: str) -> Counter:
    text = normalize(text)
    return Counter(text[i:i+n] for n in (2,3,4) for i in range(max(0,len(text)-n+1)))

@lru_cache(maxsize=4)
def _load(path: str, modified: int) -> dict:
    with gzip.open(path, 'rt', encoding='utf8') as f:
        model=json.load(f)
    if model.get('schema_version') != 1:
        raise ValueError('Unsupported skill router model schema')
    if len(model['weights']) != len(model['classes']):
        raise ValueError('Invalid skill router class weights')
    return model

def load_model(path=MODEL_PATH):
    path=Path(path)
    return _load(str(path.resolve()),path.stat().st_mtime_ns)

def predict(text: str, model: dict | None = None) -> dict:
    model=load_model() if model is None else model
    counts=char_features(text)
    known={model['vocabulary'][term]: (1+math.log(count))*model['idf'][model['vocabulary'][term]]
           for term,count in counts.items() if term in model['vocabulary']}
    norm=math.sqrt(sum(x*x for x in known.values())) or 1
    vector={i:x/norm for i,x in known.items()}
    logits=[b+sum(w[i]*v for i,v in vector.items()) for w,b in zip(model['weights'],model['intercept'])]
    maximum=max(logits)
    exps=[math.exp(x-maximum) for x in logits]
    denom=sum(exps)
    ranked=sorted(zip(model['classes'],[x/denom for x in exps]),key=lambda x:(-x[1],x[0]))
    label,score=ranked[0]
    margin=score-ranked[1][1]
    bigrams={term for term in counts if len(term)==2}
    coverage=sum(term in model['vocabulary'] for term in bigrams)/max(1,len(bigrams))
    gate=model['thresholds']
    accepted=label!='__none__' and score>=gate['probability'] and margin>=gate['margin'] and coverage>=gate['coverage']
    return {'skill_id':label if accepted else None,'top_label':label,'score':round(score,6),
            'margin':round(margin,6),'coverage':round(coverage,6),'accepted':accepted,
            'reason':'accepted' if accepted else 'out_of_scope' if label=='__none__' else 'low_confidence',
            'candidates':[{'skill_id':k,'score':round(v,6)} for k,v in ranked[:3]],
            'model_version':model['version'],'score_type':'softmax_probability_uncalibrated'}
