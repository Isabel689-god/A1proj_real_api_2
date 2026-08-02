// src/types/chat.ts

// 新增 Source 单独的类型定义
export interface Source {
  source: string;
  title: string;
  content: string;
}

// 1. 单条聊天消息接口（支持多模态文本与图片）
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  status: 'sending' | 'done' | 'error';
  deviceModel?: string;
  imageUrl?: string;
  sources?: Array<{
    source: string;
    title: string;
    content: string;
  }>;
  vision?: any;  // 新增：视觉分析结果
  fault_localization?: any;
  suggestions?: string[];
  sop_steps?: Array<{ title: string; desc: string }>;
  current_sop?: {
    version: number;
    sop_id?: string;
    issue_fingerprint?: string;
    sop_status?: string;
    steps: Array<{ title: string; desc: string; step_order?: number; step_type?: string }>;
    notes?: Array<{ title: string; content: string; type?: string }>;
    created_at?: string;
    updated_at?: string;
  };
  tool_calls?: Array<{ name: string; label: string; output: string }>;
  token_usage?: { prompt: number; completion: number; total: number };
}

// 2. 检修工单/会话接口
export interface ConversationSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: number;
}

// 3. 上传图片状态接口
export interface UploadedImageState {
  fileName: string;
  url: string;
  loading: boolean;
}

// 4. API响应接口
export interface ChatResponse {
  answer: string;
  sources: Array<{
    source: string;
    title: string;
    content: string;
  }>;
}

// 6. SOP 与 报告业务接口
export interface SopStep {
  id: number;
  title: string;
  description: string;
  isCompleted: boolean;
  warning?: string;
}

export interface RepairReportData {
  reporter: string;
  deviceName: string;
  faultDescription: string;
  solution: string;
  partsReplaced: string;
  status: string;
}

export interface UserInfo {
  username: string;
  group: string;
  permissions: string[];
}
