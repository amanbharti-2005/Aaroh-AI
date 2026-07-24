import { useEffect, useState } from 'react';
import { Circle } from 'lucide-react';
import AppLayout from '../../layouts/AppLayout';
import { useAuth } from '../../context/AuthContext';
import { useSelectedProject } from '../../context/SelectedProjectContext';
import { ENDPOINTS } from '../../config/api';
import ProjectSwitcher from '../../components/shared/ProjectSwitcher';

interface BackendMilestone {
  id: number;
  project_id: number;
  milestone_title: string;
  milestone_description: string | null;
  order_index: number;
  created_at: string;
}

export default function RoadmapPage() {
  const { getIdToken } = useAuth();
  const { selectedProject, loading: projectsLoading } = useSelectedProject();
  const [milestones, setMilestones] = useState<BackendMilestone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedProject) {
      setLoading(false);
      return;
    }

    async function fetchRoadmap() {
      setLoading(true);
      try {
        const token = await getIdToken();
        const res = await fetch(ENDPOINTS.roadmap.get(String(selectedProject!.id)), {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Failed to load roadmap');
        const data: BackendMilestone[] = await res.json();
        setMilestones(data.sort((a, b) => a.order_index - b.order_index));
        setError(null);
      } catch {
        setError('Could not load the roadmap. Please try again.');
      } finally {
        setLoading(false);
      }
    }
    fetchRoadmap();
  }, [selectedProject, getIdToken]);

  if (projectsLoading || loading) {
    return (
      <AppLayout>
        <div className="max-w-5xl mx-auto"><div className="card p-8 text-center text-muted">Loading roadmap...</div></div>
      </AppLayout>
    );
  }

  if (!selectedProject) {
    return (
      <AppLayout>
        <div className="max-w-5xl mx-auto space-y-6">
          <h1 className="page-title">Roadmap</h1>
          <div className="card p-8 text-center text-muted">You don't have any projects yet. Upload one to get started.</div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="page-title">Roadmap</h1>
            <p className="text-muted mt-1">
              {selectedProject.title} — {milestones.length} milestone{milestones.length !== 1 ? 's' : ''}
            </p>
          </div>
          <ProjectSwitcher />
        </div>

        {error && <div className="card p-8 text-center text-red-500">{error}</div>}

        {!error && milestones.length === 0 && (
          <div className="card p-8 text-center text-muted">No milestones yet for this project.</div>
        )}

        {!error && milestones.length > 0 && (
          <div className="space-y-3">
            {milestones.map((m, i) => (
              <div key={m.id} className="flex gap-4">
                <div className="flex flex-col items-center flex-shrink-0">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center border-2 border-surface-300 dark:border-surface-600 bg-surface-50 dark:bg-surface-800">
                    <Circle size={16} className="text-surface-400 dark:text-surface-500" />
                  </div>
                  {i !== milestones.length - 1 && (
                    <div className="flex-1 w-px bg-surface-200 dark:bg-surface-700 my-1 min-h-[24px]" />
                  )}
                </div>
                <div className="flex-1 pb-2">
                  <div className="card p-5">
                    <h3 className="font-semibold text-surface-900 dark:text-surface-100">{m.milestone_title}</h3>
                    {m.milestone_description && (
                      <p className="text-sm text-muted mt-1">{m.milestone_description}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}