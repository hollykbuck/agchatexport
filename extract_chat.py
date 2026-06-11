import sqlite3
import subprocess
import re

def decode_blob(blob):
    process = subprocess.Popen(['protoc', '--decode_raw'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(input=blob)
    return stdout.decode('utf-8', errors='ignore')

def decode_octal(s):
    if not s: return s
    try:
        # First handle the octal escapes like \345\246
        # The string might already be partially decoded or have literal backslashes
        s = s.encode('latin-1').decode('unicode-escape').encode('latin-1').decode('utf-8')
        return s
    except:
        return s

def get_field_at_level(decoded_lines, field_num, start_index, end_index):
    depth = 0
    for i in range(start_index, end_index):
        line = decoded_lines[i].strip()
        if not line: continue
        
        if depth == 0:
            match = re.match(r'^' + str(field_num) + r'\s*:\s*(.*)$', line)
            if match:
                return match.group(1).strip('"')
        
        if '{' in line: depth += line.count('{')
        if '}' in line: depth -= line.count('}')
    return None

def get_all_blocks_at_level(decoded_lines, field_num, start_index, end_index):
    depth = 0
    blocks = []
    block_start = -1
    for i in range(start_index, end_index):
        line = decoded_lines[i].strip()
        if not line: continue
        
        if depth == 0:
            if re.match(r'^' + str(field_num) + r'\s*{\s*$', line):
                block_start = i
                depth = 1
        else:
            if '{' in line: depth += line.count('{')
            if '}' in line: depth -= line.count('}')
            if depth == 0:
                blocks.append((block_start, i))
    return blocks

def extract_path(decoded, path):
    lines = decoded.splitlines()
    parts = path.split('.')
    
    def walk(current_lines_range, path_parts):
        start, end = current_lines_range
        if not path_parts: return None
        
        part = path_parts[0]
        if len(path_parts) == 1:
            return get_field_at_level(lines, part, start, end)
        else:
            blocks = get_all_blocks_at_level(lines, part, start, end)
            for s, e in blocks:
                res = walk((s + 1, e), path_parts[1:])
                if res: return res
            return None

    return walk((0, len(lines)), parts)

def main():
    conn = sqlite3.connect('a23a10c4-115e-418c-95c0-5454cc1081b6.db')
    cursor = conn.cursor()
    cursor.execute('SELECT idx, step_type, step_payload FROM steps ORDER BY idx')
    
    for idx, step_type, payload in cursor.fetchall():
        decoded = decode_blob(payload)
        
        if step_type == 14: # User
            msg = extract_path(decoded, "19.2") or extract_path(decoded, "19.3")
            if msg:
                print(f"[{idx}] USER: {decode_octal(msg)}\n")
        
        elif step_type == 15: # Assistant
            # Assistant text is in the *second* field 20.1 if the first is just IDs
            # Actually my walk() will find the first one that has a sub-field 1.
            # But the first field 20.1 is an ID string, not a message text.
            # Let's try to get the longest string or just skip field 5.
            
            # Special case: skip field 5 when looking for assistant text
            blocks = get_all_blocks_at_level(decoded.splitlines(), "20", 0, len(decoded.splitlines()))
            for s, e in blocks:
                # Check if this block is NOT inside a field 5 block
                # (Simple check: is there a '5 {' earlier that hasn't closed?)
                # Or just check if field 1 in this block is long enough
                text = get_field_at_level(decoded.splitlines(), "1", s + 1, e)
                if text and len(text) > 40: # IDs are usually ~36 chars
                    print(f"[{idx}] ASSISTANT: {decode_octal(text)}\n")
                    break
        
        elif step_type in [7, 8, 9, 23, 33]: # Tool Calls
            tool_name = extract_path(decoded, "5.4.2")
            tool_args = extract_path(decoded, "5.4.3")
            if tool_name:
                print(f"[{idx}] TOOL CALL: {tool_name}({decode_octal(tool_args)})")

if __name__ == "__main__":
    main()
