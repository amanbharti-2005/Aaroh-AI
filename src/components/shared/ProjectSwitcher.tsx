import { ChevronDown } from 'lucide-react';
import { useSelectedProject } from '../../context/SelectedProjectContext';

export default function ProjectSwitcher() {
  const { projects, selectedProjectId, setSelectedProjectId, loading } = useSelectedProject();

  if (loading) return null;

  if (projects.length === 0) {
    return (
      <p className="text-sm text-muted">No projects yet — upload one to get started.</p>
    );
  }

  return (
    <div className="relative inline-block">
      <select
        value={selectedProjectId ?? ''}
        onChange={e => setSelectedProjectId(Number(e.target.value))}
        className="input text-sm py-1.5 pl-3 pr-8 appearance-none cursor-pointer"
      >
        {projects.map(p => (
          <option key={p.id} value={p.id}>{p.title}</option>
        ))}
      </select>
      <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-surface-400 pointer-events-none" />
    </div>
  );
}