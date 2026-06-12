import os
import glob
import json
import argparse
from aiohttp import web
import aiohttp_cors
import aiosqlite
from agchatexport import agent_steps_pb2

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
                        tool_call = {
                            "tool_name": td.tool_name,
                            "args": {}
                        }
                        try:
                            tool_call["args"] = json.loads(td.args_json)
                        except:
                            tool_call["args_raw"] = td.args_json
                        msg['tool_call'] = tool_call
                    
                    msg['content'] = content
                    messages.append(msg)
                        
                elif step.HasField('tool_output'):
                    msg['role'] = 'OBSERVATION'
                    msg['content'] = step.tool_output.content
                    msg['key'] = step.tool_output.key
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

async def api_list_chats(request):
    db_dir = request.app['DB_DIR']
    db_files = glob.glob(os.path.join(db_dir, '*.db'))
    db_names = [os.path.basename(f) for f in db_files]
    return web.json_response({"chats": db_names})

async def api_chat_detail(request):
    db_dir = request.app['DB_DIR']
    brain_dir = request.app['BRAIN_DIR']
    db_name = request.match_info['db_name']
    db_uuid = db_name.replace('.db', '')
    db_path = os.path.join(db_dir, db_name)
    
    if not os.path.exists(db_path):
        return web.json_response({"error": "Database not found"}, status=404)
        
    messages = await get_messages(db_path)
    artifacts = get_artifacts(brain_dir, db_uuid)
    
    return web.json_response({
        "db_name": db_name,
        "db_uuid": db_uuid,
        "messages": messages,
        "artifacts": artifacts
    })

async def api_view_artifact(request):
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
    parser = argparse.ArgumentParser(description='Conversations API')
    parser.add_argument('--db-dir', default=os.path.expanduser("~/.gemini/antigravity-cli/conversations"), help='Directory for conversation databases')
    parser.add_argument('--brain-dir', default=os.path.expanduser('~/.gemini/antigravity-cli/brain'), help='Directory for brain artifacts')
    parser.add_argument('--host', default='localhost', help='Host to bind')
    parser.add_argument('--port', type=int, default=7396, help='Port to bind')
    args = parser.parse_args()

    app = web.Application()
    app['DB_DIR'] = args.db_dir
    app['BRAIN_DIR'] = args.brain_dir
    
    # Configure CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Add routes
    chats_resource = cors.add(app.router.add_resource("/api/chats"))
    cors.add(chats_resource.add_route("GET", api_list_chats))

    chat_detail_resource = cors.add(app.router.add_resource("/api/chat/{db_name}"))
    cors.add(chat_detail_resource.add_route("GET", api_chat_detail))

    artifact_resource = cors.add(app.router.add_resource("/api/brain/{db_uuid}/{path:.*}"))
    cors.add(artifact_resource.add_route("GET", api_view_artifact))

    # Serve static frontend files
    static_dir = os.path.join(os.path.dirname(__file__), "frontend", "out")
    if os.path.exists(static_dir):
        # Serve the single-page application
        app.router.add_static('/_next', os.path.join(static_dir, '_next'))
        
        async def serve_index(request):
            return web.FileResponse(os.path.join(static_dir, 'index.html'))
            
        async def serve_chat(request):
            return web.FileResponse(os.path.join(static_dir, 'chat.html'))

        app.router.add_get('/', serve_index)
        app.router.add_get('/chat', serve_chat)
        app.router.add_static('/', static_dir) # For other assets like favicon.ico

    print(f"Server starting at http://{args.host}:{args.port}")
    web.run_app(app, host=args.host, port=args.port)

if __name__ == '__main__':
    main()
