import sqlite3
import agent_steps_pb2
import json

def main():
    conn = sqlite3.connect('')
    cursor = conn.cursor()
    cursor.execute('SELECT idx, step_type, step_payload FROM steps ORDER BY idx')
    
    with open('reconstructed_chat.md', 'w') as out:
        out.write("# Reconstructed Agent Chat History\n\n")
        
        for idx, step_type, payload in cursor.fetchall():
            step = agent_steps_pb2.Step()
            try:
                step.ParseFromString(payload)
            except Exception:
                continue
                
            out.write(f"### Step {idx} (Type {step.step_type})\n")
            
            if step.HasField('user_message'):
                content = step.user_message.text_content_2 or step.user_message.nested_content_3.raw_text
                out.write(f"**USER**: {content}\n\n")
                
            if step.HasField('assistant_message'):
                if step.assistant_message.text_content:
                    out.write(f"**ASSISTANT**: {step.assistant_message.text_content}\n\n")
                if step.assistant_message.HasField('tool_directive'):
                    td = step.assistant_message.tool_directive
                    out.write(f"**PLANNING ACTION**: `{td.tool_name}`\n")
                    try:
                        args = json.loads(td.args_json)
                        out.write(f"```json\n{json.dumps(args, indent=2)}\n```\n\n")
                    except:
                        out.write(f"Arguments: {td.args_json}\n\n")
                    
            if step.HasField('metadata') and step.metadata.HasField('tool_call'):
                tc = step.metadata.tool_call
                if tc.tool_name:
                    out.write(f"> **EXECUTING**: `{tc.tool_name}`: {step.metadata.tool_action}\n\n")

    print("Extraction complete. Results saved to reconstructed_chat.md")

if __name__ == "__main__":
    main()
