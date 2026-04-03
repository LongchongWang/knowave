import sys, json
sys.path.insert(0, '/Users/wanglongchong/.meituan-local-tools/packages/meituan-local-km/src')
sys.path.insert(0, '/Users/wanglongchong/.meituan-local-tools/packages/meituan-local-utils/src')
from meituan.km.km_utils import meituan_requests

doc_id = 2752585051
url = f"https://km.sankuai.com/api/pages/new/{doc_id}?queryType=0"
resp = meituan_requests.get(url)
data = resp.json().get('data', {})

body = data.get('body', '')
pm = json.loads(body)

# 找 trVersion
body_str = json.dumps(pm)
import re
tr_versions = re.findall(r'"trVersion"\s*:\s*"([^"]+)"', body_str)
print("trVersions found:", set(tr_versions))

# 打印 pm 顶层 attrs
print("pm top keys:", list(pm.keys()))
print("pm attrs:", pm.get('attrs', {}))
