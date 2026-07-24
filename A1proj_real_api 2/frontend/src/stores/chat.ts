import { defineStore } from 'pinia';
import type { ConversationSession, ChatMessage, UploadedImageState, UserRole } from '../types/chat';
import { sendChatMessageStream } from '../api/chat';

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [] as ConversationSession[],
    activeSessionId: '' as string,
    loading: false as boolean,
    error: null as string | null,
    uploadedImage: null as UploadedImageState | null,
    selectedDeviceModel: '' as string,

    // Auth States
    isLoggedIn: false as boolean,
    username: '' as string,
    role: 'intern' as UserRole,
    permissions: [] as string[],

    globalReports: JSON.parse(localStorage.getItem('INDUSTRIAL_GLOBAL_REPORTS') || '[]') as Array<any>
  }),
  getters: {
    activeSession: (state) => state.sessions.find(s => s.id === state.activeSessionId),
    messages(): ChatMessage[] {
      return this.activeSession ? this.activeSession.messages : [];
    },
    // ✅ 动态权限鉴定
    hasPermission: (state) => (permission: string) => {
      if (state.permissions.includes('all')) return true;
      return state.permissions.includes(permission);
    }
  },
  actions: {
    init() {
      if (this.sessions.length === 0) {
        const defaultSession: ConversationSession = {
          id: 'session_' + Date.now(),
          title: '新检修任务',
          messages: [],
          updatedAt: Date.now()
        };
        this.sessions.push(defaultSession);
        this.activeSessionId = defaultSession.id;
      }
    },
    activateSession(id: string) {
      this.activeSessionId = id;
    },
    setUploadedImage(fileName: string, url: string) {
      this.uploadedImage = { fileName, url, loading: false };
    },
    clearUploadedImage() {
      this.uploadedImage = null;
    },
    async sendMessage(textInput: string) {
      if (!this.activeSessionId) return;
      this.loading = true;
      this.error = null;

      const displayText = textInput;
      let finalMessageText = textInput;
      const imageBase64 = this.uploadedImage?.url || undefined;
      const deviceModel = this.selectedDeviceModel || undefined;

      const userMessage: ChatMessage = {
        id: 'msg_' + Date.now(),
        role: 'user',
        content: displayText,
        status: 'done',
        timestamp: Date.now(),
        deviceModel: deviceModel,
        imageUrl: imageBase64
      };

      const session = this.activeSession;
      if (session) {
        session.messages.push(userMessage);
        if (session.title === '新检修任务') {
          session.title = displayText.substring(0, 10) || '检修作业问答';
        }
      }

      const assistantMsgId = 'msg_ai_' + Date.now();
      const assistantMessage: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        status: 'sending',
        timestamp: Date.now(),
        sources: [],
        vision: undefined,
        fault_localization: undefined
      };

      session?.messages.push(assistantMessage);

      this.clearUploadedImage();

      try {
        const stream = sendChatMessageStream(finalMessageText, this.activeSessionId, deviceModel, imageBase64);
        const targetMsg = session?.messages.find(m => m.id === assistantMsgId);
        if (!targetMsg) throw new Error('找不到目标消息');

        for await (const chunk of stream) {
          switch (chunk.type) {
            case 'text':
              targetMsg.content += chunk.content || '';
              break;
            case 'sources':
              targetMsg.sources = chunk.sources || [];
              break;
            case 'vision':
              targetMsg.vision = chunk.vision;
              break;
            case 'fault_localization':
              targetMsg.fault_localization = chunk.fault_localization;
              break;
            case 'done':
              targetMsg.status = 'done';
              break;
            case 'error':
              throw new Error(chunk.error || '流式输出出错');
          }
        }
      } catch (err: any) {
        const targetMsg = session?.messages.find(m => m.id === assistantMsgId);
        if (targetMsg) {
          targetMsg.content = '故障检索失败，请检查后端网络连接。';
          targetMsg.status = 'error';
        }
        this.error = err.message || '请求出错';
      } finally {
        this.loading = false;
      }
    },

    // ✅ 登录状态注入
    setUserLoggedIn(status: boolean, role: UserRole, username: string, permissions: string[] = []) {
      this.isLoggedIn = status;
      this.role = role;
      this.username = username;
      this.permissions = permissions;
    },

    submitReport(report: any) {
      this.globalReports.unshift(report);
      localStorage.setItem('INDUSTRIAL_GLOBAL_REPORTS', JSON.stringify(this.globalReports));
    },
    deleteReport(index: number) {
      this.globalReports.splice(index, 1);
      localStorage.setItem('INDUSTRIAL_GLOBAL_REPORTS', JSON.stringify(this.globalReports));
    },
    async logout() {
      if (this.username) {
         try {
            const API_BASE = import.meta.env.VITE_API_BASE ?? '';
           await fetch(`${API_BASE}/user/logout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: this.username })
            });
         } catch(e) {}
      }
      this.isLoggedIn = false;
      this.username = '';
      this.role = 'intern';
      this.permissions = [];
      this.sessions = [];
      this.activeSessionId = '';
    }
  }
});