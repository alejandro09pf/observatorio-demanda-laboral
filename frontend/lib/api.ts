import axios from 'axios';

// Base URL from environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================
// TYPES
// ============================================

export interface StatsResponse {
  // Data funnel
  total_raw_jobs: number;
  total_cleaned_jobs: number;
  total_jobs_with_skills: number;

  // Skills
  total_skills: number;
  total_unique_skills: number;
  extraction_methods: {
    ner: number;
    regex: number;
    pipeline_a1: number;  // Combined NER + Regex
    pipeline_b_total: number;  // Total LLM enhanced
    pipeline_b_gemma: number;  // Gemma specifically
    pipeline_b_jobs: number;  // Jobs with LLM
  };

  // Clustering
  n_clusters: number;

  // Geography
  n_countries: number;
  countries: string[];
  portals: string[];

  // Temporal
  date_range: {
    start: string;
    end: string;
  };
  last_scraping: string;
}

export interface Job {
  job_id: string;
  title: string;
  company: string;
  location?: string;
  country: string;
  portal: string;
  posted_date: string;
  scraped_at: string;
  url: string;
  salary_raw?: string;
  contract_type?: string;
  remote_type?: string;
}

export interface JobDetail extends Job {
  description?: string;
  requirements?: string;
  extracted_skills: ExtractedSkill[];
}

export interface ExtractedSkill {
  skill_text: string;
  skill_type: string;
  extraction_method: string;
  confidence_score: number;
  esco_uri?: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface Skill {
  id: number;
  skill_text: string;
  skill_type: string;
  esco_uri?: string;
  count: number;
}

export interface SkillCount {
  skill_text: string;
  count: number;
  percentage: number;
  type?: string;
  esco_uri?: string;
}

export interface TopSkillsResponse {
  skills: SkillCount[];
  total_unique: number;
  country?: string;
}

export interface SkillTypeDistribution {
  type: string;
  count: number;
  percentage: number;
}

export interface SkillsByTypeResponse {
  total: number;
  by_type: SkillTypeDistribution[];
}

export interface ClusterInfo {
  cluster_id: number;
  size: number;
  label: string;
  top_skills: string[];
  mean_frequency: number;
  all_skills: string[];
}

export interface ClusterMetrics {
  n_clusters: number;
  n_samples: number;
  n_noise: number;
  noise_percentage: number;
  silhouette_score: number;
  davies_bouldin_score: number;
  largest_cluster_size: number;
  smallest_cluster_size: number;
  mean_cluster_size: number;
}

export interface ClusterMetadata {
  created_at: string;
  n_skills: number;
  algorithm: string;
  parameters: {
    umap: {
      n_components: number;
      n_neighbors: number;
      min_dist: number;
      metric: string;
    };
    hdbscan: {
      min_cluster_size: number;
      min_samples: number;
      metric: string;
    };
  };
}

export interface ClusteringResponse {
  config: string;
  metadata: ClusterMetadata;
  metrics: ClusterMetrics;
  clusters: ClusterInfo[];
}

export interface QuarterData {
  quarter: string;
  count: number;
}

export interface TemporalAnalysisResponse {
  country: string;
  year?: number;
  skills: Record<string, QuarterData[]>;
  heatmap_data: Array<Record<string, any>>;
}

export interface ScrapingTask {
  task_id: string;
  status: 'running' | 'completed' | 'failed';
  spiders: string[];
  countries: string[];
  max_jobs: number;
  max_pages: number;
  started_at: string;
  completed_at?: string;
  pid?: number;
  error?: string;
}

export interface ScrapingStatus {
  active_tasks: ScrapingTask[];
  total_active: number;
  system_status: string;
}

// ============================================
// STATS ENDPOINTS
// ============================================

export const getStats = async (): Promise<StatsResponse> => {
  const response = await api.get('/api/stats');
  return response.data;
};

export const getStatsSummary = async (): Promise<StatsResponse> => {
  const response = await api.get('/api/stats/summary');
  return response.data;
};

// ============================================
// JOBS ENDPOINTS
// ============================================

export const getJobs = async (params?: {
  country?: string;
  portal?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<JobListResponse> => {
  const response = await api.get('/api/jobs', { params });
  return response.data;
};

export const getJobById = async (jobId: string): Promise<JobDetail> => {
  const response = await api.get(`/api/jobs/${jobId}`);
  return response.data;
};

export const getJobsByCountry = async (
  countryCode: string,
  params?: { limit?: number; offset?: number }
): Promise<JobListResponse> => {
  const response = await api.get(`/api/jobs/country/${countryCode}`, { params });
  return response.data;
};

// ============================================
// SKILLS ENDPOINTS
// ============================================

export const getTopSkills = async (params?: {
  country?: string;
  skill_type?: 'hard' | 'soft';
  limit?: number;
}): Promise<TopSkillsResponse> => {
  const response = await api.get('/api/skills/top', { params });
  return response.data;
};

export const searchSkills = async (
  query: string,
  params?: { limit?: number }
): Promise<{
  query: string;
  results: Array<{ skill_text: string; count: number }>;
}> => {
  const response = await api.get('/api/skills/search', {
    params: { query, ...params },
  });
  return response.data;
};

export const getSkillsByType = async (params?: {
  country?: string;
}): Promise<SkillsByTypeResponse> => {
  const response = await api.get('/api/skills/by-type', { params });
  return response.data;
};

// ============================================
// CLUSTERS ENDPOINTS
// ============================================

export const getClusters = async (
  configName?: string
): Promise<ClusteringResponse> => {
  const params = configName ? { config: configName } : undefined;
  const response = await api.get('/api/clusters', { params });
  return response.data;
};

export const getClusterById = async (
  clusterId: number,
  configName?: string
): Promise<ClusterInfo> => {
  const params = configName ? { config: configName } : undefined;
  const response = await api.get(`/api/clusters/${clusterId}`, { params });
  return response.data;
};

export const getAvailableClusterConfigs = async (): Promise<{
  count: number;
  configs: string[];
}> => {
  const response = await api.get('/api/clusters/configs/available');
  return response.data;
};

// ============================================
// TEMPORAL ENDPOINTS
// ============================================

export const getTemporalSkills = async (params?: {
  country?: string;
  year?: number;
  top_n?: number;
}): Promise<TemporalAnalysisResponse> => {
  const response = await api.get('/api/temporal/skills', { params });
  return response.data;
};

export const getSkillTrend = async (
  skill: string,
  params?: { country?: string }
): Promise<{
  skill: string;
  data: QuarterData[];
  country?: string;
}> => {
  const response = await api.get('/api/temporal/trends', {
    params: { skill, ...params },
  });
  return response.data;
};

// ============================================
// ADMIN ENDPOINTS
// ============================================

export const getAvailableSpiders = async (): Promise<{
  spiders: string[];
  countries: string[];
}> => {
  const response = await api.get('/api/admin/available');
  return response.data;
};

export const startScraping = async (config: {
  spiders: string[];
  countries: string[];
  max_jobs?: number;
  max_pages?: number;
}): Promise<ScrapingTask> => {
  const response = await api.post('/api/admin/scraping/start', config);
  return response.data;
};

export const getScrapingStatus = async (): Promise<ScrapingStatus> => {
  const response = await api.get('/api/admin/scraping/status');
  return response.data;
};

export const stopScraping = async (taskId: string): Promise<{
  message: string;
  task_id: string;
}> => {
  const response = await api.post(`/api/admin/scraping/stop/${taskId}`);
  return response.data;
};

export const getScrapingLogs = async (taskId: string): Promise<{
  task_id: string;
  logs: string;
}> => {
  const response = await api.get(`/api/admin/scraping/logs/${taskId}`);
  return response.data;
};

export const deleteScrapingTask = async (taskId: string): Promise<{
  message: string;
}> => {
  const response = await api.delete(`/api/admin/scraping/tasks/${taskId}`);
  return response.data;
};

// ============================================
// LLM PIPELINE B ENDPOINTS
// ============================================

export interface LLMStatus {
  model_name: string;
  downloaded: boolean;
  size_gb: number;
  model_info?: any;
  ready: boolean;
}

export interface PipelineBTask {
  status: string;
  task_id: string;
  message: string;
  limit: number;
  model: string;
  country?: string;
}

export const getLLMStatus = async (): Promise<LLMStatus> => {
  const response = await api.get('/api/admin/llm/status');
  return response.data;
};

export const downloadGemma = async (): Promise<{
  status: string;
  message: string;
  model_name: string;
  size_gb?: number;
}> => {
  const response = await api.post('/api/admin/llm/download-gemma');
  return response.data;
};

export const runPipelineB = async (config: {
  limit: number;
  country?: string;
  model?: string;
}): Promise<PipelineBTask> => {
  const response = await api.post('/api/admin/llm/run-pipeline-b', config);
  return response.data;
};

// ============================================
// ERROR HANDLING
// ============================================

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error:', error.message);
    } else {
      // Something else happened
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default api;
