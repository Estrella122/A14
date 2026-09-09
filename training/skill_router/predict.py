"""Inspect a routing plan without executing any domain skill."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from django.conf import settings
if not settings.configured:settings.configure(BASE_DIR=ROOT)
from core.skills.runtime import plan_skills
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python training/skill_router/predict.py "your request"')
    print(json.dumps(plan_skills(sys.argv[1]),ensure_ascii=False,indent=2))
