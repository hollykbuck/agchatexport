import os
import glob
import json
import asyncio
import aiohttp
from aiohttp import web
import aiosqlite
import agent_steps_pb2

# Configuration
DB_DIR = 'datasource/conversations'

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

async def index(request):
    db_files = glob.glob(os.path.join(DB_DIR, '*.db'))
    db_names = [os.path.basename(f) for f in db_files]
    
    html = "<html><head><title>Conversations</title><style>"
    html += "body { font-family: sans-serif; margin: 2em; }"
    html += "li { margin: 0.5em 0; }"
    html += "</style></head><body>"
    html += "<h1>Conversations</h1><ul>"
    for name in db_names:
        html += f'<li><a href="/chat/{name}">{name}</a></li>'
    html += "</ul></body></html>"
    return web.Response(text=html, content_type='text/html')

async def chat_detail(request):
    db_name = request.match_info['db_name']
    db_path = os.path.join(DB_DIR, db_name)
    
    if not os.path.exists(db_path):
        return web.Response(text="Database not found", status=404)
        
    messages = await get_messages(db_path)
    
    html = f"<html><head><title>{db_name}</title><style>"
    html += "body { font-family: sans-serif; max-width: 800px; margin: 2em auto; background: #f4f4f9; }"
    html += ".message { margin-bottom: 1.5em; padding: 1em; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }"
    html += ".USER { background: #e3f2fd; border-left: 5px solid #2196f3; }"
    html += ".ASSISTANT { background: #f1f8e9; border-left: 5px solid #8bc34a; }"
    html += ".OBSERVATION { background: #fff3e0; border-left: 5px solid #ff9800; font-family: monospace; font-size: 0.9em; }"
    html += "pre { background: #eee; padding: 0.5em; overflow-x: auto; }"
    html += "h3 { margin-top: 0; }"
    html += ".role { font-weight: bold; margin-bottom: 0.5em; display: block; }"
    html += "</style></head><body>"
    html += f'<h1>Chat: {db_name}</h1><p><a href="/">Back to list</a></p>'
    
    for msg in messages:
        role = msg['role']
        content = msg['content'].replace('\n', '<br>')
        # Handle code blocks for better rendering in HTML
        if '```' in content:
            import re
            content = re.sub(r'```(\w+)?<br>(.*?)```', r'<pre><code>\2</code></pre>', content, flags=re.DOTALL)
        
        html += f'<div class="message {role}">'
        html += f'<span class="role">{role} (Step {msg["idx"]})</span>'
        html += f'<div>{content}</div>'
        html += '</div>'
        
    html += "</body></html>"
    return web.Response(text=html, content_type='text/html')

app = web.Application()
app.add_routes([
    web.get('/', index),
    web.get('/chat/{db_name}', chat_detail),
])

if __name__ == '__main__':
    print("Starting server at http://localhost:8080")
    web.run_app(app, port=8080)
