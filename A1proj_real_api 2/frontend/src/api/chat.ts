// 💡 关键修改：加上 type 关键字，防止 Vite 将其编译到浏览器运行时
import type { Source } from '../types/chat';

// 流式输出块类型定义（建议同步添加到 types/chat.ts 中）
export interface StreamChunk {
  type: 'text' | 'sources' | 'done' | 'error' | 'vision' | 'fault_localization';
  content?: string;
  sources?: Source[];
  error?: string;
  vision?: any;
  fault_localization?: any;
}

// 后端API基础地址
const API_BASE = import.meta.env.VITE_API_BASE ?? '';

/**
 * 【流式输出版】发送聊天消息并返回异步生成器
 * 完全兼容真实后端 FastAPI StreamingResponse 格式
 */
export async function* sendChatMessageStream(
  message: string,
  sessionId: string,
  deviceModel?: string,
  imageBase64?: string
): AsyncGenerator<StreamChunk, void, unknown> {
  console.log(`[前端 API] 准备发送给后端的数据:`, { message, session_id: sessionId, deviceModel, hasImage: !!imageBase64 });

  try {
    let response: Response;

    // 如果有图片，使用multipart/form-data接口
    if (imageBase64) {
      const formData = new FormData();
      formData.append('user_id', 'user_001');
      formData.append('session_id', sessionId);
      formData.append('question', message);
      if (deviceModel) {
        formData.append('device_model', deviceModel);
      }

      // 将base64转换为Blob
      const base64Parts = imageBase64.split(',');
      const mimeType = base64Parts[0].match(/:(.*?);/)?.[1] || 'image/jpeg';
      const byteString = atob(base64Parts[1]);
      const ab = new ArrayBuffer(byteString.length);
      const ia = new Uint8Array(ab);
      for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
      }
      const blob = new Blob([ab], { type: mimeType });
      formData.append('image', blob, 'fault_image.jpg');

      response = await fetch(`${API_BASE}/chat/stream/multipart`, {
        method: 'POST',
        mode: 'cors',
        body: formData
      });
    } else {
      // 纯文本使用JSON接口
      response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        mode: 'cors',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'user_001',
          session_id: sessionId,
          question: message,
          device_model: deviceModel,
          image_url: null
        })
      });
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('无法获取响应流');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const dataStr = line.slice(6);

        try {
          const data = JSON.parse(dataStr);
          yield data as StreamChunk;
        } catch (e) {
          // 兼容旧格式纯文本
          if (dataStr === '[DONE]') {
            yield { type: 'done' };
          } else {
            yield { type: 'text', content: dataStr };
          }
        }
      }
    }

    // 处理缓冲区剩余内容
    if (buffer) {
      const lines = buffer.split('\n\n');
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const dataStr = line.slice(6);

        try {
          const data = JSON.parse(dataStr);
          yield data as StreamChunk;
        } catch (e) {
          if (dataStr === '[DONE]') {
            yield { type: 'done' };
          } else {
            yield { type: 'text', content: dataStr };
          }
        }
      }
    }

  } catch (err: any) {
    console.error('API调用失败:', err);
    yield { type: 'error', error: err.message || '网络请求失败，请检查后端服务是否启动' };
  }
}

/**
 * 【保留原有非流式接口】兼容旧代码
 * 已标记为废弃，建议迁移至 sendChatMessageStream
 */
export async function sendChatMessageWithSession(
  message: string,
  sessionId: string
): Promise<ChatResponse> {
  console.warn('⚠️ 警告：正在使用已废弃的非流式接口，请迁移至 sendChatMessageStream');

  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      device_model: undefined,
      image_url: null
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}