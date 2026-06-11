import os
import glob
import json
import asyncio
import aiohttp
import argparse
from aiohttp import web
import aiosqlite
import agent_steps_pb2

def calculate_stats(step, raw_payload):
    total_len = len(raw_payload)
    recognized_len = step.ByteSize()
    unparsed_len = max(0, total_len - recognized_len)
    unparsed_pct = (unparsed_len / total_len) * 100 if total_len > 0 else 0
    return total_len, recognized_len, unparsed_len, unparsed_pct

async def get_messages(db_path):
    messages = []
    async with aiosqlite.connect(db_path) as db:
        async with db.execute('SELECT idx, step_type, step_payload FROM steps ORDER BY idx') as cursor:
            async for idx, step_type, payload in cursor:
                step = agent_steps_pb2.Step()
                try:
                    step.ParseFromString(payload)
                except Exception:
                    continue
                
                msg = {'idx': idx, 'type': step_type}
                
                if step.HasField('user_message'):
                    content = step.user_message.text_content_2 or step.user_message.nested_content_3.raw_text
                    msg['role'] = 'USER'
                    msg['content'] = content
                    messages.append(msg)
                    
                elif step.HasField('assistant_message'):
                    msg['role'] = 'ASSISTANT'
                    content = ""
                    if step.assistant_message.text_content:
                        content += step.assistant_message.text_content
                    
                    if step.assistant_message.HasField('tool_directive'):
                        td = step.assistant_message.tool_directive
                        tool_call = f"\n\n**PLANNING ACTION**: `{td.tool_name}`\n"
                        try:
                            args = json.loads(td.args_json)
                            tool_call += f"```json\n{json.dumps(args, indent=2)}\n```"
                        except:
                            tool_call += f"Arguments: {td.args_json}"
                        content += tool_call
                    
                    msg['content'] = content
                    messages.append(msg)
                        
                elif step.HasField('tool_output'):
                    msg['role'] = 'OBSERVATION'
                    msg['content'] = f"(Key: `{step.tool_output.key}`)\n```text\n{step.tool_output.content}\n```"
                    messages.append(msg)
    return messages

def get_artifacts(brain_dir, db_uuid):
    brain_path = os.path.join(brain_dir, db_uuid)
    artifacts = []
    if os.path.exists(brain_path):
        for root, dirs, files in os.walk(brain_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, brain_path)
                artifacts.append(rel_path)
    return artifacts

async def index(request):
    db_dir = request.app['DB_DIR']
    db_files = glob.glob(os.path.join(db_dir, '*.db'))
    db_names = [os.path.basename(f) for f in db_files]
    
    html = "<html><head><title>Conversations</title><style>"
    html += "body { font-family: sans-serif; margin: 2em; background: #fafafa; }"
    html += "li { margin: 0.5em 0; padding: 0.5em; background: white; border-radius: 4px; border: 1px solid #ddd; }"
    html += "a { text-decoration: none; color: #2196f3; font-weight: bold; }"
    html += "h1 { color: #333; }"
    html += "</style></head><body>"
    html += "<h1>Conversations</h1><ul>"
    for name in db_names:
        html += f'<li><a href="/chat/{name}">{name}</a></li>'
    html += "</ul></body></html>"
    return web.Response(text=html, content_type='text/html')

async def chat_detail(request):
    db_dir = request.app['DB_DIR']
    brain_dir = request.app['BRAIN_DIR']
    db_name = request.match_info['db_name']
    db_uuid = db_name.replace('.db', '')
    db_path = os.path.join(db_dir, db_name)
    
    if not os.path.exists(db_path):
        return web.Response(text="Database not found", status=404)
        
    messages = await get_messages(db_path)
    artifacts = get_artifacts(brain_dir, db_uuid)
    
    html = f"<html><head><title>{db_name}</title><style>"
    html += "body { font-family: sans-serif; max-width: 1200px; margin: 0 auto; background: #f4f4f9; display: flex; }"
    html += ".sidebar { width: 300px; padding: 2em; background: #fff; border-right: 1px solid #ddd; height: 100vh; overflow-y: auto; position: sticky; top: 0; }"
    html += ".content { flex: 1; padding: 2em; overflow-y: auto; }"
    html += ".message { margin-bottom: 1.5em; padding: 1em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); background: white; }"
    html += ".USER { border-left: 5px solid #2196f3; }"
    html += ".ASSISTANT { border-left: 5px solid #8bc34a; }"
    html += ".OBSERVATION { border-left: 5px solid #ff9800; font-family: monospace; font-size: 0.9em; }"
    html += "pre { background: #f8f8f8; padding: 0.8em; overflow-x: auto; border: 1px solid #eee; border-radius: 4px; }"
    html += ".role { font-weight: bold; margin-bottom: 0.5em; display: block; color: #666; font-size: 0.8em; text-transform: uppercase; }"
    html += "h1 { margin-top: 0; font-size: 1.5em; }"
    html += ".artifact-link { display: block; margin: 0.3em 0; font-size: 0.9em; color: #555; text-decoration: none; }"
    html += ".artifact-link:hover { color: #2196f3; }"
    html += "</style></head><body>"
    
    # Sidebar
    html += '<div class="sidebar">'
    html += f'<h1>Chat History</h1><p><a href="/">← Back to list</a></p>'
    html += '<h3>Artifacts (Brain)</h3>'
    if not artifacts:
        html += '<p style="color: #999; font-style: italic;">No artifacts found</p>'
    for art in artifacts:
        html += f'<a class="artifact-link" href="/brain/{db_uuid}/{art}" target="_blank">{art}</a>'
    html += '</div>'
    
    # Main Content
    html += '<div class="content">'
    html += f'<h2>Database: {db_name}</h2>'
    for msg in messages:
        role = msg['role']
        content = msg['content'].replace('\n', '<br>')
        if '```' in content:
            import re
            content = re.sub(r'```(\w+)?<br>(.*?)```', r'<pre><code>\2</code></pre>', content, flags=re.DOTALL)
        
        html += f'<div class="message {role}">'
        html += f'<span class="role">{role} (Step {msg["idx"]})</span>'
        html += f'<div>{content}</div>'
        html += '</div>'
    html += '</div>'
        
    html += "</body></html>"
    return web.Response(text=html, content_type='text/html')

async def view_artifact(request):
    brain_dir = request.app['BRAIN_DIR']
    db_uuid = request.match_info['db_uuid']
    artifact_path = request.match_info['path']
    full_path = os.path.join(brain_dir, db_uuid, artifact_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return web.Response(text="Artifact not found", status=404)
        
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/plain')
    except Exception as e:
        return web.Response(text=f"Error reading artifact: {str(e)}", status=500)

def main():
    parser = argparse.ArgumentParser(description='Conversations Viewer')
    parser.add_argument('--db-dir', default='~/.gemini/antigravity/conversations', help='Directory for conversation databases')
    parser.add_argument('--brain-dir', default='~/.gemini/antigravity/brain', help='Directory for brain artifacts')
    parser.add_argument('--host', default='localhost', help='Host to bind')
    parser.add_argument('--port', type=int, default=7396, help='Port to bind')
    args = parser.parse_args()

    app = web.Application()
    app['DB_DIR'] = args.db_dir
    app['BRAIN_DIR'] = args.brain_dir
    
    app.add_routes([
        web.get('/', index),
        web.get('/chat/{db_name}', chat_detail),
        web.get('/brain/{db_uuid}/{path:.*}', view_artifact),
    ])

    print(f"Starting server at http://{args.host}:{args.port}")
    web.run_app(app, host=args.host, port=args.port)

if __name__ == '__main__':
    main()
