export interface Chat {
  name: string;
}

export interface ToolCall {
  tool_name: string;
  args?: any;
  args_raw?: string;
}

export interface Message {
  idx: number;
  type: number;
  role: 'USER' | 'ASSISTANT' | 'OBSERVATION';
  content: string;
  key?: string;
  tool_call?: ToolCall;
}

export interface ChatDetail {
  db_name: string;
  db_uuid: string;
  messages: Message[];
  artifacts: string[];
}
