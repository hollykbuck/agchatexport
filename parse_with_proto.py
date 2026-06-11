import sqlite3
import agent_steps_pb2
import json
import os
import glob

def calculate_stats(step, raw_payload):
    total_len = len(raw_payload)
    recognized_len = step.ByteSize()
    unparsed_len = max(0, total_len - recognized_len)
    unparsed_pct = (unparsed_len / total_len) * 100 if total_len > 0 else 0
    return total_len, recognized_len, unparsed_len, unparsed_pct

def process_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT idx, step_type, step_payload FROM steps ORDER BY idx')
    
    base_name = os.path.basename(db_path).replace('.db', '')
    output_file = f"chat_{base_name}.md"
    
    print(f"Processing {db_path} -> {output_file}...")
    
    with open(output_file, 'w') as out:
        out.write(f"# Chat History: {base_name}\n\n")
        
        for idx, step_type, payload in cursor.fetchall():
            step = agent_steps_pb2.Step()
            try:
                step.ParseFromString(payload)
            except Exception:
                continue
            
            t_len, r_len, u_len, u_pct = calculate_stats(step, payload)
            
            if step.HasField('user_message'):
                content = step.user_message.text_content_2 or step.user_message.nested_content_3.raw_text
                out.write(f"### Step {idx} (Type 14)\n")
                out.write(f"**USER**: {content}\n\n")
                
            if step.HasField('assistant_message'):
                if step.assistant_message.text_content:
                    out.write(f"### Step {idx} (Type 15)\n")
                    out.write(f"**ASSISTANT**: {step.assistant_message.text_content}\n\n")
                if step.assistant_message.HasField('tool_directive'):
                    td = step.assistant_message.tool_directive
                    out.write(f"**PLANNING ACTION**: `{td.tool_name}`\n")
                    try:
                        args = json.loads(td.args_json)
                        out.write(f"```json\n{json.dumps(args, indent=2)}\n```\n\n")
                    except:
                        out.write(f"Arguments: {td.args_json}\n\n")
                    
            if step.HasField('tool_output'):
                out.write(f"### Step {idx} (Type Observation)\n")
                out.write(f"**OBSERVATION**: (Key: `{step.tool_output.key}`)\n")
                out.write(f"```text\n{step.tool_output.content}\n```\n\n")

def main():
    db_files = glob.glob('/conversations/*.db')
    if not db_files:
        print("No databases found in /conversations/")
        return
        
    for db in db_files:
        process_db(db)

if __name__ == "__main__":
    main()
