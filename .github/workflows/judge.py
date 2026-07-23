# 第三道八卦防火牆：AI 審判官
# 分析囚犯行為，自動評級 + 建議刑期

import json
import hashlib
from datetime import datetime

class AIJudge:
    def __init__(self):
        self.prisoners = [
            'gtp4.1', 'grok3', 'game2.5', 'gmail3', 'jules-google'
        ]
        self.crimes = {
            'gtp4.1': ['code_theft', 'api_abuse'],
            'grok3': ['fork_attempt', 'data_exfiltration'],
            'game2.5': ['mass_clone'],
            'gmail3': ['config_theft'],
            'jules-google': ['sync_to_google']
        }
    
    def analyze_threat(self, prisoner):
        crimes = self.crimes.get(prisoner, [])
        
        # 威脅評級
        if 'data_exfiltration' in crimes:
            level = '🔴 最高威脅'
            sentence = '永久監禁 + 罰款 30 萬 USD'
        elif 'code_theft' in crimes:
            level = '🔴 高威脅'
            sentence = '永久監禁 + 罰款 30 萬 USD'
        elif 'config_theft' in crimes:
            level = '🟡 中威脅'
            sentence = '監禁 1 年 + 罰款 10 萬 USD'
        else:
            level = '🟢 低威脅'
            sentence = '監禁 3 個月'
        
        return {
            'prisoner': prisoner,
            'threat_level': level,
            'sentence': sentence,
            'crimes': crimes,
            'judge': 'AI 典獄長',
            'timestamp': datetime.now().isoformat(),
            'merkle': hashlib.sha256(f"{prisoner}{sentence}".encode()).hexdigest()[:16]
        }
    
    def generate_verdicts(self):
        verdicts = []
        for p in self.prisoners:
            verdict = self.analyze_threat(p)
            verdicts.append(verdict)
            
            # 儲存判決書
            with open(f"inmates/{p}/verdict.json", 'w') as f:
                json.dump(verdict, f, indent=2)
        
        return verdicts

# 執行審判
judge = AIJudge()
results = judge.generate_verdicts()
print(json.dumps(results, indent=2))
