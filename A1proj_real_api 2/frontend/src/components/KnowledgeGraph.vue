<template>
  <section class="kg-shell">
    <header class="kg-header">
      <div class="kg-title-block">
        <span class="kg-kicker">Knowledge Graph</span>
        <h2>设备检修知识图谱</h2>
        <p>围绕设备、部件、故障、原因和解决方案组织维修知识。</p>
      </div>

      <div class="kg-actions">
        <label class="kg-search" aria-label="搜索图谱节点或关系">
          <span>搜索</span>
          <input v-model.trim="searchText" type="search" placeholder="输入设备、故障、关系..." />
        </label>
        <button class="kg-icon-btn" type="button" title="刷新图谱" @click="loadGraph">刷新</button>
        <button class="kg-icon-btn" type="button" title="重置视图" @click="resetView">重置</button>
      </div>
    </header>

    <div class="kg-stat-grid">
      <article v-for="item in statCards" :key="item.label" class="kg-stat-card">
        <strong>{{ item.value }}</strong>
        <span>{{ item.label }}</span>
      </article>
    </div>

    <div class="kg-toolbar">
      <div class="kg-filter-group" role="tablist" aria-label="图谱类型筛选">
        <button
          v-for="item in typeOptions"
          :key="item.value || 'all'"
          class="kg-chip"
          :class="{ active: activeType === item.value }"
          type="button"
          @click="setType(item.value)"
        >
          <span class="kg-chip-dot" :style="{ background: item.color }"></span>
          {{ item.label }}
        </button>
      </div>

      <div class="kg-switches">
        <button class="kg-switch" :class="{ active: layoutMode === 'explore' }" type="button" @click="layoutMode = 'explore'">
          探索布局
        </button>
        <button class="kg-switch" :class="{ active: layoutMode === 'compact' }" type="button" @click="layoutMode = 'compact'">
          紧凑布局
        </button>
        <button class="kg-switch" :class="{ active: showLabels }" type="button" @click="showLabels = !showLabels">
          标签
        </button>
      </div>
    </div>

    <main class="kg-content">
      <div class="kg-graph-panel">
        <div ref="nvlContainerRef" class="kg-chart kg-nvl-frame" @click="handleNvlCanvasClick"></div>

        <div v-if="loading" class="kg-state">
          <div class="kg-loader"></div>
          <span>正在加载知识图谱...</span>
        </div>
        <div v-else-if="errorMessage" class="kg-state danger">
          <strong>图谱加载失败</strong>
          <span>{{ errorMessage }}</span>
        </div>
        <div v-else-if="visibleNodes.length === 0" class="kg-state">
          <strong>没有匹配的节点</strong>
          <span>换一个关键词或切回全部类型试试。</span>
        </div>

        <div class="kg-map-tools" aria-label="图谱缩放控制">
          <button type="button" title="放大" @click="zoomIn">+</button>
          <button type="button" title="缩小" @click="zoomOut">-</button>
          <button type="button" title="适应画布" @click="fitNvl()">适应</button>
        </div>

        <div class="kg-canvas-hint">Neo4j NVL 渲染，拖动画布整理结构，滚轮缩放，点击节点查看详情。</div>
      </div>

      <aside class="kg-side-panel">
        <section class="kg-panel-section">
          <div class="kg-section-head">
            <h3>实体分布</h3>
            <span>{{ visibleNodes.length }} / {{ rawNodes.length }}</span>
          </div>
          <div class="kg-legend-list">
            <button v-for="item in categoryStats" :key="item.name" type="button" class="kg-legend-item" @click="setType(item.name)">
              <span class="kg-legend-color" :style="{ background: item.color }"></span>
              <span>{{ categoryLabel(item.name) }}</span>
              <strong>{{ item.count }}</strong>
            </button>
          </div>
        </section>

        <section class="kg-panel-section kg-detail-section">
          <div class="kg-section-head">
            <h3>{{ selectedNode ? '节点详情' : selectedEdge ? '关系详情' : '图谱概览' }}</h3>
            <span v-if="detailLoading">查询中</span>
          </div>

          <div v-if="selectedNode" class="kg-detail">
            <div class="kg-node-badge" :style="{ borderColor: colorFor(selectedNode.category) }">
              <span :style="{ background: colorFor(selectedNode.category) }"></span>
              {{ categoryLabel(selectedNode.category) }}
            </div>
            <h4>{{ selectedNode.name }}</h4>
            <p>{{ selectedNode.description || nodeDetail?.node?.description || '暂无描述，可在后端图谱实体表中补充 description 字段。' }}</p>

            <div class="kg-property-table">
              <div><span>ID</span><strong>{{ selectedNode.id }}</strong></div>
              <div><span>连接数</span><strong>{{ degreeMap[selectedNode.id] || 0 }}</strong></div>
              <div><span>邻接关系</span><strong>{{ nodeDetail?.neighbors?.length ?? relatedEdges.length }}</strong></div>
            </div>

            <div class="kg-neighbor-list">
              <div v-for="neighbor in neighborPreview" :key="`${neighbor.direction}-${neighbor.entity_id}-${neighbor.relation}`">
                <span>{{ neighbor.direction === 'out' ? '指向' : '来自' }}</span>
                <strong>{{ neighbor.relation }}</strong>
                <em>{{ neighbor.entity_id }}</em>
              </div>
            </div>
          </div>

          <div v-else-if="selectedEdge" class="kg-detail">
            <div class="kg-node-badge relation">
              <span></span>
              关系
            </div>
            <h4>{{ selectedEdge.relation || '关联' }}</h4>
            <div class="kg-property-table">
              <div><span>起点</span><strong>{{ selectedEdge.source }}</strong></div>
              <div><span>终点</span><strong>{{ selectedEdge.target }}</strong></div>
              <div v-if="selectedEdge.confidence !== undefined">
                <span>置信度</span><strong>{{ Number(selectedEdge.confidence).toFixed(2) }}</strong>
              </div>
            </div>
          </div>

          <div v-else class="kg-detail">
            <p>当前图谱会自动保留连接度最高的核心实体，并在搜索时带出一阶邻居，方便从故障现象快速追踪到原因和处置方案。</p>
            <div class="kg-property-table">
              <div><span>当前类型</span><strong>{{ activeType ? categoryLabel(activeType) : '全部' }}</strong></div>
              <div><span>关系类型</span><strong>{{ relationStats.length }}</strong></div>
              <div><span>渲染上限</span><strong>{{ maxVisibleNodes }}</strong></div>
            </div>
          </div>
        </section>

        <section class="kg-panel-section">
          <div class="kg-section-head">
            <h3>关系类型</h3>
            <span>{{ visibleEdges.length }}</span>
          </div>
          <div class="kg-relation-list">
            <button v-for="item in relationStats" :key="item.name" type="button" @click="searchText = item.name">
              <span>{{ item.name }}</span>
              <strong>{{ item.count }}</strong>
            </button>
          </div>
        </section>
      </aside>
    </main>
  </section>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import NVL from '@neo4j-nvl/base';
import type { Node as NvlNode, Relationship as NvlRelationship } from '@neo4j-nvl/base';

type LayoutMode = 'explore' | 'compact';

interface GraphNode {
  id: string;
  name: string;
  category: string;
  description?: string;
  symbolSize?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  relation?: string;
  confidence?: number;
}

interface NodeDetail {
  node?: GraphNode;
  neighbors?: Array<{
    direction: 'in' | 'out';
    relation: string;
    entity_type: string;
    entity_id: string;
    confidence?: number;
  }>;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? '';
const maxVisibleNodes = 620;

const typeOptions = [
  { label: '全部', value: '', color: '#8ba4c7' },
  { label: '设备', value: 'device', color: '#4a90d9' },
  { label: '部件', value: 'component', color: '#52c41a' },
  { label: '故障', value: 'fault', color: '#ff5f66' },
  { label: '原因', value: 'fault_cause', color: '#f0b44c' },
  { label: '方案', value: 'solution', color: '#20c7c7' },
];

const categoryNameMap: Record<string, string> = {
  device: '设备',
  component: '部件',
  fault: '故障',
  fault_cause: '原因',
  solution: '解决方案',
  document: '文档',
  source_file: '来源',
  tag: '标签',
  device_model: '设备',
};

const nvlContainerRef = ref<HTMLElement | null>(null);
const nvlRef = shallowRef<any>(null);
let nvlFitTimer: number | undefined;

// 使用 Neo4j Labs llm-graph-builder 同款核心配置；Vue 项目接入 @neo4j-nvl/base，而不是 React wrapper。
const nvlBaseOptions = {
  allowDynamicMinZoom: true,
  disableWebGL: true,
  maxZoom: 3,
  minZoom: 0.05,
  relationshipThreshold: 0.55,
  useWebGL: false,
  renderer: 'canvas',
  instanceId: 'a1-knowledge-graph-nvl',
  initialZoom: 1,
  disableTelemetry: true,
  disableWebWorkers: true,
} as const;
const rawNodes = ref<GraphNode[]>([]);
const rawEdges = ref<GraphEdge[]>([]);
const rawCategories = ref<Array<{ name: string; itemStyle?: { color?: string } }>>([]);
const activeType = ref('');
const searchText = ref('');
const loading = ref(false);
const detailLoading = ref(false);
const errorMessage = ref('');
const selectedNode = ref<GraphNode | null>(null);
const selectedEdge = ref<GraphEdge | null>(null);
const nodeDetail = ref<NodeDetail | null>(null);
const layoutMode = ref<LayoutMode>('explore');
const showLabels = ref(true);

const colorMap = computed<Record<string, string>>(() => {
  const fromApi = Object.fromEntries(rawCategories.value.map((item) => [item.name, item.itemStyle?.color || '#6d84a8']));
  return {
    ...fromApi,
    device: '#4a90d9',
    component: '#52c41a',
    fault: '#ff5f66',
    fault_cause: '#f0b44c',
    solution: '#20c7c7',
    document: '#8ba4c7',
    source_file: '#b0c4de',
    tag: '#d7a34d',
  };
});

const degreeMap = computed<Record<string, number>>(() => {
  const result: Record<string, number> = {};
  for (const edge of rawEdges.value) {
    result[edge.source] = (result[edge.source] || 0) + 1;
    result[edge.target] = (result[edge.target] || 0) + 1;
  }
  return result;
});

const searchedNodeIds = computed(() => {
  const query = searchText.value.toLowerCase();
  const ids = new Set<string>();
  if (!query) return ids;

  for (const node of rawNodes.value) {
    const haystack = `${node.id} ${node.name} ${node.category} ${node.description || ''}`.toLowerCase();
    if (haystack.includes(query)) ids.add(node.id);
  }
  for (const edge of rawEdges.value) {
    if ((edge.relation || '').toLowerCase().includes(query)) {
      ids.add(edge.source);
      ids.add(edge.target);
    }
  }
  return ids;
});

const visibleNodes = computed(() => {
  const query = searchText.value.toLowerCase();
  let nodes = rawNodes.value;

  if (query) {
    const expanded = new Set(searchedNodeIds.value);
    for (const edge of rawEdges.value) {
      if (searchedNodeIds.value.has(edge.source) || searchedNodeIds.value.has(edge.target)) {
        expanded.add(edge.source);
        expanded.add(edge.target);
      }
    }
    nodes = nodes.filter((node) => expanded.has(node.id));
  }

  if (nodes.length <= maxVisibleNodes) return nodes;

  return [...nodes]
    .sort((a, b) => (degreeMap.value[b.id] || 0) - (degreeMap.value[a.id] || 0))
    .slice(0, maxVisibleNodes);
});

const visibleNodeIds = computed(() => new Set(visibleNodes.value.map((node) => node.id)));

const visibleEdges = computed(() =>
  rawEdges.value.filter((edge) => visibleNodeIds.value.has(edge.source) && visibleNodeIds.value.has(edge.target))
);

const categoryStats = computed(() => {
  const counts = new Map<string, number>();
  for (const node of visibleNodes.value) {
    counts.set(node.category, (counts.get(node.category) || 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count, color: colorFor(name) }))
    .sort((a, b) => b.count - a.count);
});

const relationStats = computed(() => {
  const counts = new Map<string, number>();
  for (const edge of visibleEdges.value) {
    const name = edge.relation || '关联';
    counts.set(name, (counts.get(name) || 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 12);
});

const statCards = computed(() => [
  { label: '可见实体', value: visibleNodes.value.length },
  { label: '可见关系', value: visibleEdges.value.length },
  { label: '实体类型', value: categoryStats.value.length },
  { label: '关系类型', value: relationStats.value.length },
]);

const edgeByNvlId = computed<Record<string, GraphEdge>>(() => {
  const result: Record<string, GraphEdge> = {};
  visibleEdges.value.forEach((edge, index) => {
    result[edgeNvlId(edge, index)] = edge;
  });
  return result;
});

const nvlNodes = computed<NvlNode[]>(() => {
  const maxDegree = Math.max(...visibleNodes.value.map((node) => degreeMap.value[node.id] || 0), 1);
  const query = searchText.value.toLowerCase();

  return visibleNodes.value.map((node) => {
    const degree = degreeMap.value[node.id] || 0;
    const isMatch = Boolean(query && searchedNodeIds.value.has(node.id));
    const isSelected = selectedNode.value?.id === node.id;
    const size = node.symbolSize || Math.max(22, Math.min(74, 22 + (degree / maxDegree) * 48));
    const captionVisible = showLabels.value || isMatch || isSelected;

    return {
      id: node.id,
      caption: captionVisible ? truncate(node.name || node.id, isMatch || isSelected ? 20 : 14) : '',
      color: colorFor(node.category),
      size,
      selected: isSelected || isMatch,
      captionSize: isMatch || isSelected ? 13 : 10,
      captionAlign: 'bottom',
    };
  });
});

const nvlRelationships = computed<NvlRelationship[]>(() => {
  const query = searchText.value.toLowerCase();

  return visibleEdges.value.map((edge, index) => {
    const relation = edge.relation || '关联';
    const relationMatch = Boolean(query && relation.toLowerCase().includes(query));
    const isSelected = edgeEquals(edge, selectedEdge.value);

    return {
      id: edgeNvlId(edge, index),
      from: edge.source,
      to: edge.target,
      type: relation,
      caption: relationMatch || isSelected ? truncate(relation, 16) : '',
      color: relationMatch || isSelected ? '#ffffff' : 'rgba(120, 168, 210, 0.52)',
      width: relationMatch || isSelected ? 2.8 : 1.2,
      selected: isSelected,
      captionSize: 10,
    };
  });
});

const relatedEdges = computed(() => {
  if (!selectedNode.value) return [];
  return rawEdges.value.filter((edge) => edge.source === selectedNode.value?.id || edge.target === selectedNode.value?.id);
});

const neighborPreview = computed(() => {
  if (nodeDetail.value?.neighbors?.length) return nodeDetail.value.neighbors.slice(0, 8);
  if (!selectedNode.value) return [];
  return relatedEdges.value.slice(0, 8).map((edge) => ({
    direction: edge.source === selectedNode.value?.id ? ('out' as const) : ('in' as const),
    relation: edge.relation || '关联',
    entity_type: '',
    entity_id: edge.source === selectedNode.value?.id ? edge.target : edge.source,
    confidence: edge.confidence,
  }));
});

async function loadGraph() {
  loading.value = true;
  errorMessage.value = '';
  selectedNode.value = null;
  selectedEdge.value = null;
  nodeDetail.value = null;
  try {
    const endpoint = activeType.value
      ? `${API_BASE}/knowledge/graph?entity_type=${encodeURIComponent(activeType.value)}`
      : `${API_BASE}/knowledge/graph`;
    const response = await fetch(endpoint);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    const data = result.data || result;
    rawNodes.value = Array.isArray(data.nodes) ? data.nodes : [];
    rawEdges.value = Array.isArray(data.edges) ? data.edges : data.links || [];
    rawCategories.value = Array.isArray(data.categories) ? data.categories : [];
    await nextTick();
    renderNvl();
  } catch (error: any) {
    rawNodes.value = [];
    rawEdges.value = [];
    rawCategories.value = [];
    errorMessage.value = error?.message || '请确认后端 /knowledge/graph 接口已启动。';
  } finally {
    loading.value = false;
  }
}

async function fetchNodeDetail(node: GraphNode) {
  detailLoading.value = true;
  nodeDetail.value = null;
  try {
    const response = await fetch(`${API_BASE}/knowledge/graph/node/${encodeURIComponent(node.id)}`);
    if (!response.ok) return;
    const result = await response.json();
    nodeDetail.value = result.data || null;
  } finally {
    detailLoading.value = false;
  }
}

function handleNvlCanvasClick(event: MouseEvent) {
  const nvl = nvlRef.value;
  if (!nvl) return;

  const targets = nvl.getHits(event, ['node', 'relationship'], { hitNodeMarginWidth: 8 })?.nvlTargets;
  const hitNode = targets?.nodes?.[0]?.data || targets?.nodes?.[0];
  const hitRelationship = targets?.relationships?.[0]?.data || targets?.relationships?.[0];

  if (hitNode?.id) {
    const node = rawNodes.value.find((item) => item.id === hitNode.id);
    if (node) selectNode(node);
    return;
  }

  if (hitRelationship?.id) {
    const edge = edgeByNvlId.value[hitRelationship.id];
    if (edge) selectEdge(edge);
  }
}

function selectNode(node: GraphNode) {
  selectedNode.value = node;
  selectedEdge.value = null;
  fetchNodeDetail(node);
}

function selectEdge(edge: GraphEdge) {
  selectedEdge.value = edge;
  selectedNode.value = null;
  nodeDetail.value = null;
}

function renderNvl() {
  const frame = nvlContainerRef.value;
  if (!frame) return;

  if (nvlFitTimer !== undefined) {
    window.clearTimeout(nvlFitTimer);
    nvlFitTimer = undefined;
  }

  nvlRef.value?.destroy?.();
  nvlRef.value = null;
  frame.innerHTML = '';

  if (errorMessage.value || visibleNodes.value.length === 0) return;

  try {
    const nvl = new NVL(
      frame,
      nvlNodes.value,
      nvlRelationships.value,
      {
        ...nvlBaseOptions,
        layout: layoutMode.value === 'explore' ? 'forceDirected' : 'd3Force',
        layoutOptions: layoutMode.value === 'explore' ? { gravity: 0.05 } : { gravity: 0.16 },
      },
      {
        onInitialization: () => {
          scheduleFit();
        },
        onLayoutDone: () => {
          scheduleFit(true);
        },
        onError: (error: Error) => {
          errorMessage.value = error.message || 'Neo4j NVL 渲染失败。';
        },
      }
    );
    nvlRef.value = markRaw(nvl);
  } catch (error: any) {
    errorMessage.value = error?.message || 'Neo4j NVL 渲染失败。';
  }
}

function scheduleFit(outOnly = false) {
  if (nvlFitTimer !== undefined) window.clearTimeout(nvlFitTimer);
  nvlFitTimer = window.setTimeout(() => fitNvl(outOnly), 120);
}

function fitNvl(outOnly = false) {
  const nvl = nvlRef.value;
  if (!nvl || visibleNodes.value.length === 0) return;
  nvl.fit(visibleNodes.value.map((node) => node.id), { animated: true, outOnly, maxZoom: 1.4 });
}

function zoomIn() {
  const nvl = nvlRef.value;
  if (!nvl) return;
  nvl.setZoom(Math.min(3, nvl.getScale() * 1.22));
}

function zoomOut() {
  const nvl = nvlRef.value;
  if (!nvl) return;
  nvl.setZoom(Math.max(0.05, nvl.getScale() / 1.22));
}

function setType(type: string) {
  activeType.value = type;
}

function resetView() {
  activeType.value = '';
  searchText.value = '';
  selectedNode.value = null;
  selectedEdge.value = null;
  nodeDetail.value = null;
  nextTick(() => {
    renderNvl();
    scheduleFit();
  });
}

function colorFor(category: string) {
  return colorMap.value[category] || '#8ba4c7';
}

function categoryLabel(category: string) {
  return categoryNameMap[category] || category;
}

function edgeNvlId(edge: GraphEdge, index: number) {
  return `rel:${index}:${edge.source}->${edge.target}:${edge.relation || '关联'}`;
}

function edgeEquals(left: GraphEdge, right: GraphEdge | null) {
  if (!right) return false;
  return left.source === right.source && left.target === right.target && (left.relation || '关联') === (right.relation || '关联');
}

function truncate(value: string, length: number) {
  if (!value) return '';
  return value.length > length ? `${value.slice(0, length)}...` : value;
}

watch(activeType, () => {
  loadGraph();
});

watch([searchText, layoutMode, showLabels, selectedNode, selectedEdge], () => {
  nextTick(renderNvl);
});

watch([visibleNodes, visibleEdges], () => {
  nextTick(renderNvl);
});

onMounted(loadGraph);

onBeforeUnmount(() => {
  if (nvlFitTimer !== undefined) window.clearTimeout(nvlFitTimer);
  nvlRef.value?.destroy?.();
});
</script>

<style scoped>
.kg-shell {
  width: 100%;
  height: 100%;
  min-height: 460px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  color: #e2e8f0;
  background:
    radial-gradient(circle at 18% 8%, rgba(74, 144, 217, 0.18), transparent 28%),
    radial-gradient(circle at 84% 18%, rgba(32, 199, 199, 0.12), transparent 28%),
    linear-gradient(135deg, rgba(5, 10, 24, 0.96), rgba(10, 16, 32, 0.92));
  border: 1px solid rgba(131, 165, 221, 0.18);
  border-radius: 8px;
  overflow: hidden;
}

.kg-header,
.kg-toolbar,
.kg-content,
.kg-stat-grid {
  position: relative;
  z-index: 1;
}

.kg-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.kg-title-block {
  min-width: 0;
}

.kg-kicker {
  display: block;
  margin-bottom: 4px;
  color: #8fb7df;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.kg-title-block h2 {
  margin: 0;
  color: #f8fbff;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0;
}

.kg-title-block p {
  margin: 6px 0 0;
  color: #96a8bd;
  font-size: 12px;
  line-height: 1.5;
}

.kg-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.kg-search {
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(340px, 42vw);
  height: 36px;
  padding: 0 10px;
  border: 1px solid rgba(131, 165, 221, 0.22);
  border-radius: 6px;
  background: rgba(6, 11, 24, 0.72);
}

.kg-search span {
  color: #87a0bd;
  font-size: 12px;
  white-space: nowrap;
}

.kg-search input {
  width: 100%;
  min-width: 0;
  color: #edf6ff;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: 13px;
}

.kg-search input::placeholder {
  color: #53677f;
}

.kg-icon-btn,
.kg-switch,
.kg-chip {
  border: 1px solid rgba(131, 165, 221, 0.22);
  border-radius: 6px;
  color: #dce9f8;
  background: rgba(12, 20, 38, 0.72);
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.kg-icon-btn {
  height: 36px;
  padding: 0 14px;
  font-size: 13px;
}

.kg-icon-btn:hover,
.kg-switch:hover,
.kg-chip:hover {
  border-color: rgba(116, 171, 231, 0.6);
  background: rgba(28, 44, 72, 0.78);
  transform: translateY(-1px);
}

.kg-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.kg-stat-card {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid rgba(131, 165, 221, 0.16);
  border-radius: 6px;
  background: rgba(13, 22, 42, 0.66);
}

.kg-stat-card strong {
  color: #f7fbff;
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.kg-stat-card span {
  color: #90a4ba;
  font-size: 12px;
  white-space: nowrap;
}

.kg-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.kg-filter-group,
.kg-switches {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kg-chip,
.kg-switch {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  padding: 0 11px;
  font-size: 12px;
}

.kg-chip.active,
.kg-switch.active {
  color: #ffffff;
  border-color: rgba(111, 176, 238, 0.68);
  background: rgba(57, 92, 139, 0.42);
}

.kg-chip-dot,
.kg-legend-color {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  box-shadow: 0 0 10px currentColor;
}

.kg-content {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 12px;
}

.kg-graph-panel,
.kg-side-panel {
  min-height: 0;
  border: 1px solid rgba(131, 165, 221, 0.16);
  border-radius: 8px;
  background: rgba(5, 10, 22, 0.52);
}

.kg-graph-panel {
  position: relative;
  overflow: hidden;
}

.kg-chart {
  width: 100%;
  height: 100%;
  min-height: 360px;
}

.kg-nvl-frame {
  cursor: grab;
  background:
    linear-gradient(rgba(131, 165, 221, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(131, 165, 221, 0.05) 1px, transparent 1px);
  background-size: 36px 36px;
}

.kg-nvl-frame:active {
  cursor: grabbing;
}

.kg-nvl-frame :deep(canvas) {
  outline: none;
}

.kg-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #a9bbcf;
  background: rgba(5, 10, 22, 0.72);
  text-align: center;
}

.kg-state.danger strong {
  color: #ffb4b4;
}

.kg-loader {
  width: 28px;
  height: 28px;
  border: 2px solid rgba(139, 164, 199, 0.22);
  border-top-color: #8fb7df;
  border-radius: 50%;
  animation: kg-spin 0.8s linear infinite;
}

@keyframes kg-spin {
  to {
    transform: rotate(360deg);
  }
}

.kg-map-tools {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kg-map-tools button {
  min-width: 36px;
  height: 32px;
  padding: 0 8px;
  color: #dce9f8;
  border: 1px solid rgba(131, 165, 221, 0.22);
  border-radius: 6px;
  background: rgba(6, 11, 24, 0.78);
  cursor: pointer;
  font-size: 12px;
}

.kg-map-tools button:hover {
  border-color: rgba(116, 171, 231, 0.64);
  background: rgba(28, 44, 72, 0.84);
}

.kg-canvas-hint {
  position: absolute;
  left: 12px;
  bottom: 12px;
  max-width: calc(100% - 24px);
  padding: 6px 9px;
  color: #7f93aa;
  background: rgba(6, 11, 24, 0.74);
  border: 1px solid rgba(131, 165, 221, 0.14);
  border-radius: 6px;
  font-size: 12px;
}

.kg-side-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  overflow: auto;
}

.kg-panel-section {
  padding: 12px;
  border: 1px solid rgba(131, 165, 221, 0.14);
  border-radius: 6px;
  background: rgba(13, 22, 42, 0.48);
}

.kg-detail-section {
  flex: 1;
}

.kg-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.kg-section-head h3 {
  margin: 0;
  color: #edf6ff;
  font-size: 14px;
  letter-spacing: 0;
}

.kg-section-head span {
  color: #7f93aa;
  font-size: 12px;
}

.kg-legend-list,
.kg-relation-list,
.kg-neighbor-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.kg-legend-item,
.kg-relation-list button {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 30px;
  padding: 0 8px;
  color: #cbd9e8;
  border: 1px solid transparent;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  text-align: left;
}

.kg-relation-list button {
  grid-template-columns: minmax(0, 1fr) auto;
}

.kg-legend-item:hover,
.kg-relation-list button:hover {
  border-color: rgba(131, 165, 221, 0.22);
  background: rgba(255, 255, 255, 0.06);
}

.kg-legend-item span:nth-child(2),
.kg-relation-list span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kg-legend-item strong,
.kg-relation-list strong {
  color: #f8fbff;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.kg-detail {
  color: #aebed0;
  font-size: 13px;
  line-height: 1.6;
}

.kg-detail h4 {
  margin: 10px 0 8px;
  color: #f8fbff;
  font-size: 17px;
  line-height: 1.35;
  word-break: break-word;
}

.kg-detail p {
  margin: 0 0 12px;
  color: #9eafc1;
}

.kg-node-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 26px;
  padding: 0 9px;
  color: #dce9f8;
  border: 1px solid;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.04);
  font-size: 12px;
}

.kg-node-badge span {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.kg-node-badge.relation {
  border-color: rgba(139, 164, 199, 0.4);
}

.kg-node-badge.relation span {
  background: #8ba4c7;
}

.kg-property-table {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin: 12px 0;
}

.kg-property-table div {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  padding: 7px 8px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.035);
}

.kg-property-table span {
  color: #7f93aa;
}

.kg-property-table strong {
  min-width: 0;
  color: #e5eef8;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.kg-neighbor-list div {
  display: grid;
  grid-template-columns: 42px minmax(0, 0.7fr) minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  padding: 7px 8px;
  border: 1px solid rgba(131, 165, 221, 0.1);
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.03);
}

.kg-neighbor-list span {
  color: #7f93aa;
  font-size: 12px;
}

.kg-neighbor-list strong,
.kg-neighbor-list em {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kg-neighbor-list strong {
  color: #dce9f8;
  font-style: normal;
}

.kg-neighbor-list em {
  color: #9fb3c9;
  font-style: normal;
}

@media (max-width: 1100px) {
  .kg-content {
    grid-template-columns: 1fr;
  }

  .kg-side-panel {
    max-height: 320px;
  }
}

@media (max-width: 760px) {
  .kg-shell {
    padding: 12px;
  }

  .kg-header,
  .kg-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .kg-search {
    width: 100%;
  }

  .kg-actions {
    justify-content: flex-start;
  }

  .kg-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
