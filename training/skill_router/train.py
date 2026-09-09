"""Fit on train only; choose C and rejection thresholds on validation only."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('router_model_standalone', ROOT/'core/skills/router_model.py')
router=importlib.util.module_from_spec(spec);spec.loader.exec_module(router)
catalog_spec=importlib.util.spec_from_file_location('router_training_catalog', ROOT/'core/skills/catalog.py')
catalog=importlib.util.module_from_spec(catalog_spec)
sys.modules[catalog_spec.name]=catalog
catalog_spec.loader.exec_module(catalog)
ALLOWED_LABELS={s.id for s in catalog.SKILLS if s.category!='orchestration'}


def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]
def label(row):
    labels=row.get('labels')
    if not isinstance(labels,list) or len(labels)>1 or any(not isinstance(x,str) or not x for x in labels):
        raise ValueError(f"Sample {row.get('id')}: labels must contain one atomic skill ID or be empty; split compound examples first")
    if any(x not in ALLOWED_LABELS for x in labels):
        raise ValueError(f"Sample {row.get('id')}: unknown or runtime-managed skill ID")
    if not row.get('text') or not row.get('group'):
        raise ValueError(f"Sample {row.get('id')}: text and group are required")
    return labels[0] if labels else '__none__' 
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=Path(__file__).parent/'data')
    parser.add_argument('--output',type=Path,default=ROOT/'core/skills/models/skill_router.json.gz')
    args=parser.parse_args()
    train=read(args.data/'train.jsonl'); val=read(args.data/'validation.jsonl')
    assert not {r['group'] for r in train}&{r['group'] for r in val}
    assert not {router.normalize(r['text']) for r in train}&{router.normalize(r['text']) for r in val}
    y=[label(r) for r in train]; vy=[label(r) for r in val]
    vectorizer=TfidfVectorizer(analyzer='char',ngram_range=(2,4),preprocessor=router.normalize,lowercase=False,sublinear_tf=True)
    x=vectorizer.fit_transform([r['text'] for r in train]); vx=vectorizer.transform([r['text'] for r in val])
    trials=[];best=None
    for c in (2.,5.,10.,20.):
        clf=LogisticRegression(C=c,max_iter=500,random_state=42,solver='lbfgs').fit(x,y)
        pred=clf.predict(vx)
        score=f1_score(vy,pred,average='macro',zero_division=0)
        # Select regularization and rejection jointly, using validation only.
        probas=clf.predict_proba(vx)
        sorted_probs=np.sort(probas,axis=1)
        margins=sorted_probs[:,-1]-sorted_probs[:,-2]
        coverages=[]
        for row in val:
            grams={t for t in router.char_features(row['text']) if len(t)==2}
            coverages.append(sum(t in vectorizer.vocabulary_ for t in grams)/max(1,len(grams)))
        local_best=None
        for prob in (0.08,0.12,0.18,0.25,0.35):
            for margin in (0.01,0.03,0.06,0.10):
                for coverage in (0.20,0.30,0.40):
                    output=[p if max(ps)>=prob and m>=margin and cov>=coverage else '__none__' for p,ps,m,cov in zip(pred,probas,margins,coverages)]
                    f1=f1_score(vy,output,average='macro',zero_division=0)
                    rank=(f1,prob,margin,coverage)
                    if local_best is None or rank>local_best[0]:local_best=(rank,output)
        trials.append({'C':c,'validation_top1_accuracy':accuracy_score(vy,pred),'validation_macro_f1':score,'gated_macro_f1':local_best[0][0]})
        if best is None or local_best[0]>best[0]:best=(local_best[0],clf,c,local_best[1])
    clf=best[1]
    model={'schema_version':1,'version':'a14-router-1.0','algorithm':'char_tfidf_multinomial_logistic_regression',
           'classes':clf.classes_.tolist(),'vocabulary':{k:int(v) for k,v in vectorizer.vocabulary_.items()},
           'idf':vectorizer.idf_.tolist(),'weights':clf.coef_.tolist(),'intercept':clf.intercept_.tolist(),
           'thresholds':{'probability':0.,'margin':0.,'coverage':0.},
           'training':{'seed':42,'C':best[2],'train_count':len(train),'validation_count':len(val),
           'train_sha256':hashlib.sha256((args.data/'train.jsonl').read_bytes()).hexdigest(),
           'validation_sha256':hashlib.sha256((args.data/'validation.jsonl').read_bytes()).hexdigest(),
           'data_source':'assistant_authored_synthetic','test_used_for_training':False}}
    raw=[router.predict(r['text'],model) for r in val]
    # Verify exported inference against sklearn before selecting gates.
    proba=clf.predict_proba(vx)
    for i,p in enumerate(raw):
        assert abs(p['score']-max(proba[i]))<2e-6
        assert p['top_label']==clf.classes_[np.argmax(proba[i])]
    chosen=(best[0],best[3])
    model['thresholds']=dict(zip(('probability','margin','coverage'),chosen[0][1:]))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(model,ensure_ascii=False,separators=(',',':')).encode()
    temporary=args.output.with_name(args.output.name+".tmp")
    temporary.write_bytes(gzip.compress(payload,mtime=0))
    os.replace(temporary,args.output)
    report={'algorithm':model['algorithm'],'training':model['training'],'hyperparameter_trials':trials,
            'thresholds':model['thresholds'],'validation_accuracy_after_rejection':accuracy_score(vy,chosen[1]),
            'validation_macro_f1_after_rejection':chosen[0][0],
            'validation_errors':[{'text':r['text'],'expected':truth,'predicted':pred,'detail':p} for r,truth,pred,p in zip(val,vy,chosen[1],raw) if truth!=pred],
            'inference_parity':'passed within 2e-6','model_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}
    dest=Path(__file__).parent/'reports/training.json';dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
