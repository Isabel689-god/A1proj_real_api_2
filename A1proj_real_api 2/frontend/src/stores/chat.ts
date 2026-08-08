import { defineStore } from 'pinia';
import type { ConversationSession, ChatMessage, UploadedImageState } from '../types/chat';
import { sendChatMessageStream } from '../api/chat';

const AUTH_KEY = 'a1proj_auth';

function loadSavedAuth() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY) || 'null') || {};
  } catch {
    return {};
  }
}

export const useChatStore = defineStore('chat', {
  state: () => {
    const savedAuth = loadSavedAuth();
    return ({
    sessions: [] as ConversationSession[],
    activeSessionId: '' as string,
    loading: false as boolean,
    error: null as string | null,
    uploadedImage: null as UploadedImageState | null,
    selectedDeviceModel: '' as string,

    // Auth States
    isLoggedIn: Boolean(savedAuth.username) as boolean,
    username: (savedAuth.username || '') as string,
    group: (savedAuth.group || '') as string,
    permissions: (savedAuth.permissions || []) as string[],

    globalReports: JSON.parse(localStorage.getItem('INDUSTRIAL_GLOBAL_REPORTS') || '[]') as Array<any>,
    sopTick: 0,  // SOP 变更计数器，强制前端刷新
    lockedSOP: null as any,  // 首轮锁定的 SOP 结构，后续只更新状态
    });
  },
  getters: {
    activeSession: (state) => state.sessions.find(s => s.id === state.activeSessionId),
    messages(): ChatMessage[] {
      return this.activeSession ? this.activeSession.messages : [];
    },
    hasPermission: (state) => (permission: string) => {
      if (state.permissions.includes('all')) return true;
      return state.permissions.includes(permission);
    }
  },
  actions: {
    async init() {
      this.restoreAuth();
      if (!this.isLoggedIn) return;

      // 从后端 MySQL 同步会话列表
      try {
        const API_BASE = import.meta.env.VITE_API_BASE || '';
        const res = await fetch(`${API_BASE}/chat/sessions?user_id=${encodeURIComponent(this.username || 'user_001')}`);
        if (res.ok) {
          const data = await res.json();
          const remoteMap = new Map<string, any>();
          for (const s of (data.sessions || [])) {
            remoteMap.set(s.session_id, {
              id: s.session_id, title: s.title || '新对话', messages: [],
              updatedAt: new Date(s.updated_at || Date.now()).getTime(),
            });
          }
          if (remoteMap.size > 0) {
            const merged = Array.from(remoteMap.values());
            merged.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
            this.sessions = merged.map((s: any) => ({ ...s, messages: s.messages || [], updatedAt: s.updatedAt || Date.now() }));
            this.activeSessionId = this.sessions[0].id;
            this._persist();
            // 自动加载第一条会话的消息
            await this.activateSession(this.activeSessionId || this.sessions[0].id);
            return;
          }
        }
      } catch { /* ignore */ }

      // 无历史则新建
      const defaultSession: ConversationSession = {
        id: 'session_' + Date.now(),
        title: '新检修任务',
        messages: [],
        updatedAt: Date.now()
      };
      this.sessions.push(defaultSession);
      this.activeSessionId = defaultSession.id;
    },

    restoreAuth() {
      const savedAuth = loadSavedAuth();
      if (!savedAuth.username) return false;
      this.isLoggedIn = true;
      this.username = savedAuth.username;
      this.group = savedAuth.group || '';
      this.permissions = savedAuth.permissions || [];
      return true;
    },

    _persist() {
      // 只存元数据，消息内容不外泄到 localStorage
      const meta = this.sessions.map(s => ({
        id: s.id, title: s.title, updatedAt: s.updatedAt,
        messageCount: s.messages?.length || 0
      }));
      localStorage.setItem('a1proj_sessions', JSON.stringify(meta));
    },

    _syncLockedSOP() {
      // 从当前会话消息中提取 SOP 并同步到 lockedSOP
      const session = this.activeSession;
      if (!session?.messages?.length) {
        this.lockedSOP = null;
        this.sopTick++;
        return;
      }
      // 从最后一条 assistant 消息获取 SOP
      for (let i = session.messages.length - 1; i >= 0; i--) {
        const m = session.messages[i];
        if (m.role === 'assistant' && m.current_sop) {
          this.lockedSOP = JSON.parse(JSON.stringify(m.current_sop));
          this.sopTick++;
          return;
        }
      }
      this.lockedSOP = null;
      this.sopTick++;
    },

    async activateSession(id: string) {
      this.activeSessionId = id;
      const session = this.sessions.find(s => s.id === id);
      if (session && (!session.messages || session.messages.length === 0)) {
        try {
          const API_BASE = import.meta.env.VITE_API_BASE || '';
          const res = await fetch(`${API_BASE}/chat/sessions/${encodeURIComponent(id)}?user_id=${encodeURIComponent(this.username || 'user_001')}`);
          if (res.ok) {
            const data = await res.json();
            const msgs = data.session?.messages || [];
            session.messages = msgs.map((m: any) => ({
              id: 'msg_' + Math.random(),
              role: m.role === 'assistant' ? 'assistant' : 'user',
              content: m.content || '',
              status: 'done' as const,
              timestamp: Date.now(),
              sop_steps: m.sop_steps || undefined,
              current_sop: m.current_sop || undefined,
            }));
          } else if (res.status === 404) {
            this.sessions = this.sessions.filter(s => s.id !== id);
            this.activeSessionId = this.sessions[0]?.id || '';
          }
        } catch { /* ignore */ }
      }
      // 同步 lockedSOP，确保右侧面板显示当前会话的 SOP
      this._syncLockedSOP();
    },

    createNewSession() {
      this.lockedSOP = null;
      this.sopTick++;
      const s: ConversationSession = {
        id: 'session_' + Date.now(),
        title: '新检修任务',
        messages: [],
        updatedAt: Date.now()
      };
      this.sessions.unshift(s);
      this.activeSessionId = s.id;
      this._persist();
    },

    async deleteSession(sessionId: string) {
      // 调后端删除
      try {
        await fetch(`${import.meta.env.VITE_API_BASE || ''}/chat/sessions/${encodeURIComponent(sessionId)}?user_id=${encodeURIComponent(this.username || 'user_001')}`, { method: 'DELETE' });
      } catch { /* ignore */ }
      // 前端移除
      const idx = this.sessions.findIndex(s => s.id === sessionId);
      if (idx !== -1) {
        this.sessions.splice(idx, 1);
        if (this.activeSessionId === sessionId) {
          this.activeSessionId = this.sessions[0]?.id || '';
        }
        if (this.sessions.length === 0) {
          this.createNewSession();
        }
        this._persist();
      }
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
        suggestions: [],
        tool_calls: [],
        token_usage: undefined,
        vision: undefined,
        fault_localization: undefined
      };

      session?.messages.push(assistantMessage);

      this.clearUploadedImage();

      try {
        const stream = sendChatMessageStream(finalMessageText, this.activeSessionId, this.username, deviceModel, imageBase64);
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
            case 'tool_end':
              targetMsg.tool_calls = targetMsg.tool_calls || [];
              targetMsg.tool_calls.push({ name: chunk.tool || '', label: chunk.label || '', output: chunk.output || '' });
              break;
            case 'suggestions':
              targetMsg.suggestions = chunk.items || [];
              break;
            case 'sop_steps':
              targetMsg.sop_steps = chunk.steps || [];
              break;
            case 'sop_version':
              targetMsg.current_sop = chunk.sop;
              targetMsg.sop_steps = chunk.sop?.steps || targetMsg.sop_steps || [];
              // 首轮锁定 SOP 结构
              if (!this.lockedSOP && chunk.sop?.steps?.length) {
                this.lockedSOP = JSON.parse(JSON.stringify(chunk.sop));
              }
              this.sopTick++;
              break;
            case 'sop_state':
              if (chunk.state?.steps) {
                // 首轮：从 sop_state 构建锁定 SOP
                if (!this.lockedSOP) {
                  this.lockedSOP = {
                    version: 1,
                    steps: chunk.state.steps.map((s: any) => ({
                      title: s.title || '',
                      desc: s.desc || '',
                      step_status: s.status || 'pending',
                      step_note: s.note || '',
                    })),
                    current_step: chunk.state.current_step || 1,
                    all_done: chunk.state.all_done || false,
                  };
                } else {
                  // 后续：只更新锁定 SOP 的步骤状态
                  const stateSteps = chunk.state.steps;
                  const lockedSteps: any[] = this.lockedSOP.steps || [];
                  for (let i = 0; i < Math.min(lockedSteps.length, stateSteps.length); i++) {
                    lockedSteps[i].step_status = stateSteps[i].status;
                    lockedSteps[i].step_note = stateSteps[i].note;
                  }
                  this.lockedSOP.current_step = chunk.state.current_step;
                  this.lockedSOP.all_done = chunk.state.all_done;
                }
                // 同步到当前消息供文本回退
                targetMsg.current_sop = { ...this.lockedSOP };
              }
              this.sopTick++;
              break;
            case 'token_usage':
              targetMsg.token_usage = chunk.usage;
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
        if (session) {
          session.updatedAt = Date.now();
          this._persist();
        }
      }
    },

    // ✅ 登录状态注入
    setUserLoggedIn(status: boolean, group: string, username: string, permissions: string[] = []) {
      this.isLoggedIn = status;
      this.group = group;
      this.username = username;
      this.permissions = permissions;
      if (status) {
        localStorage.setItem(AUTH_KEY, JSON.stringify({ username, group, permissions }));
      } else {
        localStorage.removeItem(AUTH_KEY);
      }
    },

    submitReport(report: any) {
      report.submitStatus = '已提交';
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
      this.group = '';
      this.permissions = [];
      this.sessions = [];
      localStorage.removeItem('a1proj_sessions');
      localStorage.removeItem(AUTH_KEY);
      this.activeSessionId = '';
    }
  }
});
