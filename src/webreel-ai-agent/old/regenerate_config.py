import json
import sys
sys.path.insert(0, '/app/webreel-ai-agent')
from src.bu_to_webreel import convert_to_webreel_config

with open('/app/output/docker-test4/browser_use_history.json', 'r', encoding='utf-8') as f:
    history = json.load(f)

config = convert_to_webreel_config(history, video_name='docker-test4')

with open('/app/output/docker-test4/webreel_pipeline_v2.config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print('Config regenerated successfully!')
print(f'Steps count: {len(config["videos"]["docker-test4"]["steps"])}')
