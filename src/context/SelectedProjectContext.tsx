import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { ENDPOINTS } from '../config/api';

export interface ProjectSummary {
  id: number;
  owner_id: number;
  title: string;
  idea_description: string | null;
  input_type: string;
  github_url: string | null;
  zip_filename: string | null;
  timeline: string | null;
  created_at: string;
}

interface SelectedProjectContextValue {
  projects: ProjectSummary[];
  selectedProject: ProjectSummary | null;
  selectedProjectId: number | null;
  setSelectedProjectId: (id: number) => void;
  loading: boolean;
  refresh: () => Promise<void>;
}

const STORAGE_KEY = 'aaroh_selected_project_id';

const SelectedProjectContext = createContext<SelectedProjectContextValue>({
  projects: [],
  selectedProject: null,
  selectedProjectId: null,
  setSelectedProjectId: () => {},
  loading: true,
  refresh: async () => {},
});

export function SelectedProjectProvider({ children }: { children: React.ReactNode }) {
  const { user, getIdToken } = useAuth();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectIdState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const setSelectedProjectId = (id: number) => {
    setSelectedProjectIdState(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  };

  const fetchProjects = useCallback(async () => {
    if (!user) {
      setProjects([]);
      setSelectedProjectIdState(null);
      setLoading(false);
      return;
    }
    try {
      const token = await getIdToken();
      const res = await fetch(ENDPOINTS.projects.list, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load projects');
      const data: ProjectSummary[] = await res.json();
      setProjects(data);

      // Restore previously selected project if it still exists, otherwise default to the first one
      const stored = localStorage.getItem(STORAGE_KEY);
      const storedId = stored ? Number(stored) : null;
      const stillExists = storedId && data.some(p => p.id === storedId);

      if (stillExists) {
        setSelectedProjectIdState(storedId);
      } else if (data.length > 0) {
        setSelectedProjectIdState(data[0].id);
        localStorage.setItem(STORAGE_KEY, String(data[0].id));
      } else {
        setSelectedProjectIdState(null);
      }
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [user, getIdToken]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const selectedProject = projects.find(p => p.id === selectedProjectId) || null;

  return (
    <SelectedProjectContext.Provider
      value={{ projects, selectedProject, selectedProjectId, setSelectedProjectId, loading, refresh: fetchProjects }}
    >
      {children}
    </SelectedProjectContext.Provider>
  );
}

export const useSelectedProject = () => useContext(SelectedProjectContext);