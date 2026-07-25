import { useCallback, useState, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Info, AlertCircle, Loader, GitBranch } from 'lucide-react';
import AppLayout from '../../layouts/AppLayout';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { useSelectedProject } from '../../context/SelectedProjectContext';
import { ENDPOINTS } from '../../config/api';
import ProjectSwitcher from '../../components/shared/ProjectSwitcher';

const colorMap: Record<string, { bg: string; border: string; text: string }> = {
  blue: { bg: '#eff6ff', border: '#3b82f6', text: '#1d4ed8' },
  teal: { bg: '#f0fdfa', border: '#14b8a6', text: '#0f766e' },
  green: { bg: '#f0fdf4', border: '#22c55e', text: '#15803d' },
  orange: { bg: '#fff7ed', border: '#f97316', text: '#c2410c' },
  purple: { bg: '#faf5ff', border: '#a855f7', text: '#7e22ce' },
  red: { bg: '#fef2f2', border: '#ef4444', text: '#b91c1c' },
  indigo: { bg: '#eef2ff', border: '#6366f1', text: '#4338ca' },
  gray: { bg: '#f8fafc', border: '#94a3b8', text: '#475569' },
};

const darkColorMap: Record<string, { bg: string; border: string; text: string }> = {
  blue: { bg: '#172554', border: '#3b82f6', text: '#93c5fd' },
  teal: { bg: '#042f2e', border: '#14b8a6', text: '#5eead4' },
  green: { bg: '#052e16', border: '#22c55e', text: '#86efac' },
  orange: { bg: '#431407', border: '#f97316', text: '#fdba74' },
  purple: { bg: '#3b0764', border: '#a855f7', text: '#d8b4fe' },
  red: { bg: '#450a0a', border: '#ef4444', text: '#fca5a5' },
  indigo: { bg: '#1e1b4b', border: '#6366f1', text: '#a5b4fc' },
  gray: { bg: '#1e293b', border: '#64748b', text: '#94a3b8' },
};

// The categories the Architecture Agent emits (see backend
// app/core/agents/architecture_agent.py CATEGORIES), in rough data-flow
// order — used both for colour and for the left-to-right column layout.
const CATEGORY_COLORS: Record<string, string> = {
  'Frontend': 'blue',
  'Auth': 'orange',
  'API Layer': 'teal',
  'AI/ML': 'green',
  'Data Pipeline': 'purple',
  'Cache': 'red',
  'Database': 'indigo',
  'External': 'gray',
};

const CATEGORY_ORDER = Object.keys(CATEGORY_COLORS);

// Raw shape returned by GET /api/architecture/{id}
interface RawNode { id: string; label?: string; category?: string; detail?: string }
interface RawEdge { source: string; target: string; label?: string }

// What CustomNode renders. React Flow's useNodesState<T> generic is the NODE
// DATA type, not the node type — it was previously passed `Node[]`, which
// typed every node's `data` as an array of nodes.
interface FlowNodeData {
  label: string;
  sublabel: string;
  color: string;
  category: string;
}

const COLUMN_WIDTH = 260;
const ROW_HEIGHT = 120;

/**
 * Converts the backend's {id, label, category, detail} into the shape React
 * Flow actually requires: {id, position: {x, y}, data: {...}}.
 *
 * The API response was previously passed straight to setNodes(). React Flow
 * dereferences node.position while measuring, so every node arriving without
 * one threw during render — and with no error boundary above it, the entire
 * Architecture page went blank rather than showing a diagram or an error.
 * Edges hit the same problem: React Flow needs an `id` per edge, which the
 * backend doesn't emit.
 *
 * The agent returns no coordinates, so we lay nodes out ourselves: one column
 * per category in CATEGORY_ORDER, stacked vertically within the column.
 */
function toFlowGraph(rawNodes: RawNode[], rawEdges: RawEdge[]): { nodes: Node<FlowNodeData>[]; edges: Edge[] } {
  const columnCounts: Record<number, number> = {};

  const nodes: Node<FlowNodeData>[] = rawNodes
    .filter(n => n && n.id)
    .map(n => {
      const category = n.category && CATEGORY_COLORS[n.category] ? n.category : 'External';
      const column = Math.max(0, CATEGORY_ORDER.indexOf(category));
      const row = columnCounts[column] ?? 0;
      columnCounts[column] = row + 1;

      return {
        id: String(n.id),
        type: 'default',
        position: { x: column * COLUMN_WIDTH, y: row * ROW_HEIGHT },
        data: {
          label: n.label || n.id,
          sublabel: n.detail || category,
          color: CATEGORY_COLORS[category],
          category,
        },
      };
    });

  // Drop edges pointing at nodes the model didn't actually define, otherwise
  // React Flow warns and draws dangling connections.
  const known = new Set(nodes.map(n => n.id));
  const edges: Edge[] = rawEdges
    .filter(e => e && known.has(String(e.source)) && known.has(String(e.target)))
    .map((e, i) => ({
      id: `e-${e.source}-${e.target}-${i}`,
      source: String(e.source),
      target: String(e.target),
      label: e.label,
      animated: true,
    }));

  return { nodes, edges };
}

function CustomNode({ data }: { data: FlowNodeData }) {
  const { theme } = useTheme();
  const palette = theme === 'dark' ? darkColorMap : colorMap;
  const colors = palette[data.color] || palette.blue;

  return (
    <div
      style={{
        background: colors.bg,
        border: `2px solid ${colors.border}`,
        borderRadius: '12px',
        padding: '12px 16px',
        minWidth: '140px',
        boxShadow: '0 1px 6px rgba(0,0,0,0.08)',
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: colors.border, width: 8, height: 8 }} />
      <div style={{ fontWeight: 600, fontSize: 13, color: colors.text, marginBottom: 2 }}>{data.label}</div>
      <div style={{ fontSize: 11, color: colors.border, opacity: 0.8 }}>{data.sublabel}</div>
      <Handle type="source" position={Position.Right} style={{ background: colors.border, width: 8, height: 8 }} />
    </div>
  );
}

const nodeTypes = { default: CustomNode, input: CustomNode, output: CustomNode };


export default function ArchitecturePage() {
  const { theme } = useTheme();
  const { getIdToken } = useAuth();
  const { selectedProject, loading: projectsLoading } = useSelectedProject();
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node<FlowNodeData> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notIngested, setNotIngested] = useState(false);

  const onConnect = useCallback(
    (params: Connection) => setEdges(eds => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  useEffect(() => {
    if (!selectedProject) {
      setLoading(false);
      return;
    }

    async function fetchArchitecture() {
      setLoading(true);
      setError(null);
      setNotIngested(false);
      try {
        const token = await getIdToken();
        const res = await fetch(ENDPOINTS.architecture.get(String(selectedProject!.id)), {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.status === 404) {
          // Expected state for a project whose repo hasn't been ingested yet
          // (e.g. an idea-only text/voice project, or ingestion failed) —
          // not an error, just nothing to show.
          setNotIngested(true);
          setNodes([]);
          setEdges([]);
          return;
        }

        if (!res.ok) throw new Error('Failed to load architecture');

        const data = await res.json();
        const graph = toFlowGraph(data.nodes || [], data.edges || []);
        setNodes(graph.nodes);
        setEdges(graph.edges);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not load architecture.');
        setNodes([]);
        setEdges([]);
      } finally {
        setLoading(false);
      }
    }
    fetchArchitecture();
  }, [selectedProject, getIdToken, setNodes, setEdges]);

  if (projectsLoading || loading) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto">
          <div className="card p-8 text-center text-muted flex items-center justify-center gap-2">
            <Loader size={20} className="animate-spin" /> Loading architecture...
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!selectedProject) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto space-y-6">
          <h1 className="page-title">Architecture Visualization</h1>
          <div className="card p-8 text-center text-muted">
            You don't have any projects yet. Upload one to get started.
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-4 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="page-title">Architecture Visualization</h1>
            <p className="text-muted mt-1">{selectedProject.title} — Interactive architecture diagram</p>
          </div>
          <div className="flex items-center gap-3">
            <ProjectSwitcher />
            {nodes.length > 0 && (
              <div className="flex items-center gap-2 text-xs text-muted bg-primary-50 dark:bg-primary-950 border border-primary-200 dark:border-primary-800 rounded-lg px-3 py-2">
                <Info size={13} className="text-primary-500" />
                <span>Drag nodes to rearrange. Click for details.</span>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm">
            <AlertCircle size={15} />
            {error}
          </div>
        )}

        {notIngested && (
          <div className="card p-10 text-center">
            <div className="w-14 h-14 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center mx-auto mb-4">
              <GitBranch size={24} className="text-surface-400" />
            </div>
            <h2 className="font-semibold text-surface-900 dark:text-surface-100 mb-1">No repository analyzed yet</h2>
            <p className="text-sm text-muted max-w-sm mx-auto">
              {selectedProject.input_type === 'text' || selectedProject.input_type === 'voice'
                ? "This project was created from an idea description, so there's no code to diagram yet. Upload a GitHub repo or ZIP to see its architecture."
                : "Repository analysis hasn't completed for this project yet."}
            </p>
          </div>
        )}

        {!notIngested && !error && nodes.length === 0 && (
          <div className="card p-10 text-center">
            <div className="w-14 h-14 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center mx-auto mb-4">
              <GitBranch size={24} className="text-surface-400" />
            </div>
            <h2 className="font-semibold text-surface-900 dark:text-surface-100 mb-1">No architecture detected</h2>
            <p className="text-sm text-muted max-w-sm mx-auto">
              The repository was analyzed, but no clear architectural components could be identified from the code.
            </p>
          </div>
        )}

        {nodes.length > 0 && (
          <>
            {/* Legend */}
            <div className="card p-4 flex flex-wrap gap-3">
              {/* Only the categories actually present in this diagram. The old
                  static list always showed all seven and omitted Database. */}
              {CATEGORY_ORDER
                .filter(category => nodes.some(n => n.data?.category === category))
                .map(category => {
                  const palette = theme === 'dark' ? darkColorMap : colorMap;
                  const c = palette[CATEGORY_COLORS[category]];
                  return (
                    <div key={category} className="flex items-center gap-1.5 text-xs">
                      <div className="w-3 h-3 rounded" style={{ background: c.border }} />
                      <span className="text-surface-600 dark:text-surface-400">{category}</span>
                    </div>
                  );
                })}
            </div>

            {/* React Flow canvas */}
            <div className="card overflow-hidden" style={{ height: '560px' }}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={(_, node) => setSelectedNode(node)}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                defaultEdgeOptions={{
                  style: { stroke: theme === 'dark' ? '#64748b' : '#94a3b8', strokeWidth: 1.5 },
                  labelStyle: { fontSize: 11, fill: theme === 'dark' ? '#94a3b8' : '#64748b' },
                  labelBgStyle: { fill: theme === 'dark' ? '#1e293b' : '#fff', fillOpacity: 0.8 },
                }}
              >
                <Controls
                  style={{
                    background: theme === 'dark' ? '#1e293b' : '#fff',
                    border: theme === 'dark' ? '1px solid #334155' : '1px solid #e2e8f0',
                  }}
                />
                <MiniMap
                  style={{
                    background: theme === 'dark' ? '#0f172a' : '#f8fafc',
                    border: theme === 'dark' ? '1px solid #334155' : '1px solid #e2e8f0',
                  }}
                  nodeColor={(node) => {
                    const color = (node.data as { color?: string }).color;
                    const c = colorMap[color || 'blue'];
                    return c?.border || '#3b82f6';
                  }}
                />
                <Background
                  variant={BackgroundVariant.Dots}
                  gap={20}
                  size={1}
                  color={theme === 'dark' ? '#334155' : '#e2e8f0'}
                />
              </ReactFlow>
            </div>

            {/* Node detail panel */}
            {selectedNode && (
              <div className="card p-5 border-l-4 border-l-primary-500 animate-slide-up">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-surface-900 dark:text-surface-100">{selectedNode.data.label}</h3>
                    <p className="text-sm text-muted">{selectedNode.data.sublabel}</p>
                  </div>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="text-xs text-muted hover:text-surface-700 dark:hover:text-surface-300"
                  >
                    Dismiss
                  </button>
                </div>
                <div className="mt-3 grid sm:grid-cols-3 gap-3">
                  <div className="text-sm">
                    <span className="text-muted">Node ID:</span>{' '}
                    <span className="font-mono text-primary-600 dark:text-primary-400">{selectedNode.id}</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-muted">Type:</span>{' '}
                    <span className="font-medium text-surface-700 dark:text-surface-300 capitalize">
                      {selectedNode.type}
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-muted">Connections:</span>{' '}
                    <span className="font-medium text-surface-700 dark:text-surface-300">
                      {edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length} edges
                    </span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </AppLayout>
  );
}
