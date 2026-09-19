import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_c import Gate
print(json.dumps(Gate('stopped').attempt('stopped')))
