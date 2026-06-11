import sqlite3
import agent_steps_pb2

def main():
    conn = sqlite3.connect('')
    cursor = conn.cursor()
    cursor.execute('SELECT idx, step_type, step_payload FROM steps ORDER BY idx')
    
    for idx, step_type, payload in cursor.fetchall():
        step = agent_steps_pb2.Step()
        try:
            step.ParseFromString(payload)
        except Exception as e:
            # Some steps might have extra wrapping or slightly different schema
            # We skip those for this demo or handle them gracefully
            continue
            
        print(f"--- Step {idx} (Type {step.step_type}) ---")
        
        if step.HasField('user_message'):
            content = step.user_message.text_content_2 or step.user_message.nested_content_3.raw_text
            print(f"USER: {content}\n")
            
        if step.HasField('assistant_message'):
            if step.assistant_message.text_content:
                print(f"ASSISTANT: {step.assistant_message.text_content}\n")
            if step.assistant_message.HasField('tool_directive'):
                td = step.assistant_message.tool_directive
                print(f"ACTION: {td.tool_name}({td.args_json})\n")
                
        if step.HasField('metadata') and step.metadata.HasField('tool_call'):
            tc = step.metadata.tool_call
            if tc.tool_name:
                print(f"EXECUTING TOOL: {tc.tool_name}")
                print(f"SUMMARY: {step.metadata.tool_summary}")
                print(f"ACTION: {step.metadata.tool_action}\n")

if __name__ == "__main__":
    main()
