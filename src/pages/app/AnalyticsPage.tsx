import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import AppLayout from '../../layouts/AppLayout';
import { useAuth } from '../../context/AuthContext';
import { useSelectedProject } from '../../context/SelectedProjectContext';
import { useTheme } from '../../context/ThemeContext';
import { ENDPOINTS } from '../../config/api';
import ProjectSwitcher from '../../components/shared/ProjectSwitcher';
import { TrendingUp, GitBranch, AlertCircle, Github, FileCode2 } from 'lucide-react';

interface AnalyticsResponse {
  health_score_trend: { date: string; score: number }[];
  category_scores: { category: string; score: number }[];
  tech_stack_breakdown: { name: string; value: number }[];
  commit_activity: { week: string; commits: number }[];
  open_issues: number | null;
  has_github_data: boolean;
  python_files_analyzed: number | null;
  total_functions: number | null;
  total_classes: number | null;
  avg_docstring_coverage_pct: number | null;
}

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899'];

export default function AnalyticsPage() {
  const { getIdToken } = useAuth();
  const { selectedProject, loading: projectsLoading } = useSelectedProject();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const axisColor = isDark ? '#64748b' : '#94a3b8';
  const gridColor = isDark ? '#1e293b' : '#f1f5f9';
  const tooltipBg = isDark ? '#1e293b' : '#fff';
  const tooltipBorder = isDark ? '#334155' : '#e2e8f0';
  const tooltipText = isDark ? '#f1f5f9' : '#0f172a';

  const tooltipStyle: React.CSSProperties = {
    background: tooltipBg,
    border: `1px solid ${tooltipBorder}`,
    borderRadius: 8,
    color: tooltipText,
    fontSize: 12,
    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
  };

  useEffect(() => {
    if (!selectedProject) {
      setLoading(false);
      return;
    }

    async function fetchData() {
      setLoading(true);
      try {
        const token = await getIdToken();
        const res = await fetch(ENDPOINTS.analytics.get(String(selectedProject!.id)), {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Failed to load analytics');
        const analytics: AnalyticsResponse = await res.json();
        setData(analytics);
        setError(null);
      } catch {
        setError('Could not load analytics. Please try again.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [selectedProject, getIdToken]);

  if (projectsLoading || loading) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto">
          <div className="card p-8 text-center text-muted">Loading analytics...</div>
        </div>
      </AppLayout>
    );
  }

  if (!selectedProject) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto space-y-6">
          <h1 className="page-title">Analytics</h1>
          <div className="card p-8 text-center text-muted">You don't have any projects yet. Upload one to get started.</div>
        </div>
      </AppLayout>
    );
  }

  if (error || !data) {
    return (
      <AppLayout>
        <div className="max-w-6xl mx-auto">
          <div className="card p-8 text-center text-red-500">{error || 'No data available.'}</div>
        </div>
      </AppLayout>
    );
  }

  const techStackWithColors = data.tech_stack_breakdown.map((entry, i) => ({
    ...entry,
    color: PIE_COLORS[i % PIE_COLORS.length],
  }));

  // Only render the code-quality card when repo intelligence actually ran
  // (python_files_analyzed is null, not 0, until a repo has been ingested).
  const hasCodeQualityData = data.python_files_analyzed !== null;

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="page-title">Analytics</h1>
            <p className="text-muted mt-1">{selectedProject.title} — Project metrics and trends</p>
          </div>
          <ProjectSwitcher />
        </div>

        {/* Overview Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card p-5 card-hover">
            <div className="w-9 h-9 rounded-lg bg-amber-50 dark:bg-amber-950 flex items-center justify-center mb-3">
              <AlertCircle size={17} className="text-amber-500" />
            </div>
            <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">{data.open_issues ?? '—'}</div>
            <div className="text-sm text-muted mt-0.5">Open Issues</div>
          </div>
          <div className="card p-5 card-hover">
            <div className="w-9 h-9 rounded-lg bg-primary-50 dark:bg-primary-950 flex items-center justify-center mb-3">
              <GitBranch size={17} className="text-primary-500" />
            </div>
            <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
              {data.commit_activity.reduce((sum, c) => sum + c.commits, 0)}
            </div>
            <div className="text-sm text-muted mt-0.5">Recent Commits</div>
          </div>
          <div className="card p-5 card-hover">
            <div className="w-9 h-9 rounded-lg bg-accent-50 dark:bg-accent-950 flex items-center justify-center mb-3">
              <TrendingUp size={17} className="text-accent-500" />
            </div>
            <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
              {data.health_score_trend.length > 0 ? data.health_score_trend[data.health_score_trend.length - 1].score : '—'}
            </div>
            <div className="text-sm text-muted mt-0.5">Latest Health Score</div>
          </div>
          <div className="card p-5 card-hover">
            <div className="w-9 h-9 rounded-lg bg-violet-50 dark:bg-violet-950 flex items-center justify-center mb-3">
              <Github size={17} className="text-violet-500" />
            </div>
            <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">{techStackWithColors.length}</div>
            <div className="text-sm text-muted mt-0.5">Languages Detected</div>
          </div>
        </div>

        {/* Warning Banner */}
        {!data.has_github_data && (
          <div className="card p-4 flex items-center gap-3 text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800">
            <AlertCircle size={16} />
            This project has no linked GitHub repo, so commit activity and open issue counts aren't available.
            {data.tech_stack_breakdown.length > 0 && ' Tech stack below is estimated from the uploaded code, not GitHub\'s language statistics.'}
          </div>
        )}

        {/* Code Quality Snapshot — real AST-derived numbers, only shown once a repo has been analyzed */}
        {hasCodeQualityData && (
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileCode2 size={16} className="text-primary-500" />
              <h2 className="font-semibold text-surface-900 dark:text-surface-100">Code Quality Snapshot</h2>
              <span className="text-xs text-muted">(Python files)</span>
            </div>
            {data.python_files_analyzed === 0 ? (
              <p className="text-sm text-muted">No Python files were detected in this repository.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <div className="text-xl font-bold text-surface-900 dark:text-surface-100">{data.python_files_analyzed}</div>
                  <div className="text-xs text-muted mt-0.5">Python files analyzed</div>
                </div>
                <div>
                  <div className="text-xl font-bold text-surface-900 dark:text-surface-100">{data.total_functions ?? '—'}</div>
                  <div className="text-xs text-muted mt-0.5">Functions</div>
                </div>
                <div>
                  <div className="text-xl font-bold text-surface-900 dark:text-surface-100">{data.total_classes ?? '—'}</div>
                  <div className="text-xs text-muted mt-0.5">Classes</div>
                </div>
                <div>
                  <div className="text-xl font-bold text-surface-900 dark:text-surface-100">
                    {data.avg_docstring_coverage_pct !== null ? `${data.avg_docstring_coverage_pct}%` : '—'}
                  </div>
                  <div className="text-xs text-muted mt-0.5">Avg. docstring coverage</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Charts Grid */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Commit Activity */}
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-6">
              <GitBranch size={16} className="text-primary-500" />
              <h2 className="font-semibold text-surface-900 dark:text-surface-100">Commit Activity</h2>
            </div>
            {data.commit_activity.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.commit_activity} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="week" tick={{ fill: axisColor, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: axisColor, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="commits" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Commits" />
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="h-[200px] flex items-center justify-center text-sm text-muted">No commit data available</div>}
          </div>

          {/* Health Score Trend */}
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-6">
              <TrendingUp size={16} className="text-accent-500" />
              <h2 className="font-semibold text-surface-900 dark:text-surface-100">Health Score Trend</h2>
            </div>
            {data.health_score_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data.health_score_trend} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: axisColor, fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: string) => v ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
                  />
                  <YAxis domain={[0, 100]} tick={{ fill: axisColor, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    labelFormatter={(v) => v ? new Date(String(v)).toLocaleDateString() : ''}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#10b981"
                    strokeWidth={2.5}
                    dot={{ fill: '#10b981', r: 4, strokeWidth: 0 }}
                    activeDot={{ r: 6 }}
                    name="Health Score"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="h-[200px] flex items-center justify-center text-sm text-muted">No health reports yet</div>}
          </div>

          {/* Tech Stack Breakdown */}
          <div className="card p-6">
            <h2 className="font-semibold text-surface-900 dark:text-surface-100 mb-6">Tech Stack Breakdown</h2>
            {techStackWithColors.length > 0 ? (
              <div className="flex flex-col sm:flex-row items-center gap-6">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie data={techStackWithColors} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={3} dataKey="value">
                      {techStackWithColors.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`, '']} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-2 w-full">
                  {techStackWithColors.map(({ name, value, color }) => (
                    <div key={name} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: color }} />
                      <span className="text-sm text-surface-700 dark:text-surface-300 flex-1">{name}</span>
                      <span className="text-sm font-medium text-surface-900 dark:text-surface-100">{value}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : <div className="h-[160px] flex items-center justify-center text-sm text-muted">No language data available</div>}
          </div>

          {/* Category Scores */}
          <div className="card p-6">
            <h2 className="font-semibold text-surface-900 dark:text-surface-100 mb-6">Category Scores</h2>
            {data.category_scores.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={data.category_scores} margin={{ top: 0, right: 20, bottom: 0, left: 20 }}>
                  <PolarGrid stroke={isDark ? '#334155' : '#e2e8f0'} />
                  <PolarAngleAxis dataKey="category" tick={{ fill: axisColor, fontSize: 11 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar dataKey="score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} strokeWidth={2} name="Score" />
                  <Tooltip contentStyle={tooltipStyle} />
                </RadarChart>
              </ResponsiveContainer>
            ) : <div className="h-[220px] flex items-center justify-center text-sm text-muted">No health report data yet</div>}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
