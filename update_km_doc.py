"""
通过 CatDesk 浏览器 JS 注入，用新文档内容替换旧文档编辑器内容
"""
import sys
import json
import subprocess
sys.path.insert(0, '/Users/wanglongchong/.meituan-local-tools/packages/meituan-local-km/src')
sys.path.insert(0, '/Users/wanglongchong/.meituan-local-tools/packages/meituan-local-utils/src')

from meituan.km.km_utils import get_km_doc_by_id

NEW_DOC_ID = 2752367796

# 1. 读取新文档的完整 ProseMirror JSON
new_doc = get_km_doc_by_id(str(NEW_DOC_ID))
new_body = new_doc.get('data', {}).get('body', '')
new_pm = json.loads(new_body)
new_content = new_pm.get('content', [])

# 只取正文节点（去掉 title，保留 catalog 和其他内容）
new_body_nodes = [n for n in new_content if n.get('type') != 'title']
print(f"新文档正文节点数: {len(new_body_nodes)}")

# 2. 构造 JS 脚本：通过 ProseMirror API 替换内容
new_nodes_json = json.dumps(new_body_nodes, ensure_ascii=False)

js_script = f"""
(function() {{
  const editorInst = window.editorInst;
  const view = editorInst.view;
  if (!view) return 'ERROR: no view found';
  
  const state = view.state;
  const schema = state.schema;
  
  // 解析新内容
  const newNodesData = {new_nodes_json};
  
  // 找到 title 节点结束位置（正文开始位置）
  let fromPos = 1;
  state.doc.forEach((node, offset) => {{
    if (node.type.name === 'title') {{
      fromPos = offset + node.nodeSize;
    }}
  }});
  
  const toPos = state.doc.content.size - 1;
  
  // 用 schema.nodeFromJSON 解析新节点
  const newNodes = newNodesData.map(n => schema.nodeFromJSON(n));
  
  // 创建事务并替换内容
  const tr = state.tr.replaceWith(fromPos, toPos, newNodes);
  view.dispatch(tr);
  
  return 'SUCCESS: replaced from=' + fromPos + ' to=' + toPos + ' with ' + newNodes.length + ' nodes';
}})()
"""

# 3. 通过 catdesk browser-action evaluate 执行
action_json = json.dumps({"action": "evaluate", "script": js_script})
result = subprocess.run(
    ['/Users/wanglongchong/.catpaw/bin/catdesk', 'browser-action', action_json],
    capture_output=True, text=True
)
print("stdout:", result.stdout)
print("stderr:", result.stderr)
