'use client';

import { useEffect, useState, useMemo } from 'react';
import {
  getClusters,
  getAvailableClusterConfigs,
  getClusterImages,
  ClusteringResponse,
  ClusterConfig,
  ClusterImage,
} from '@/lib/api';

export default function ClustersPage() {
  const [data, setData] = useState<ClusteringResponse | null>(null);
  const [images, setImages] = useState<ClusterImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [availableConfigs, setAvailableConfigs] = useState<ClusterConfig[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>('');

  // Filters
  const [pipelineFilter, setPipelineFilter] = useState<string>('all');
  const [sizeFilter, setSizeFilter] = useState<string>('all');
  const [escoStageFilter, setEscoStageFilter] = useState<string>('all');

  // Fetch available configs on mount
  useEffect(() => {
    const fetchConfigs = async () => {
      try {
        const result = await getAvailableClusterConfigs();
        setAvailableConfigs(result.configs);
        // Set first config as default if available
        if (result.configs.length > 0) {
          setSelectedConfig(result.configs[0].name);
        }
      } catch (err) {
        console.error('Error fetching configs:', err);
      }
    };
    fetchConfigs();
  }, []);

  // Filtered configs based on selected filters
  const filteredConfigs = useMemo(() => {
    return availableConfigs.filter((config) => {
      if (pipelineFilter !== 'all' && config.pipeline !== pipelineFilter) return false;
      if (sizeFilter !== 'all' && config.size !== sizeFilter) return false;
      if (escoStageFilter !== 'all' && config.esco_stage !== escoStageFilter) return false;
      return true;
    });
  }, [availableConfigs, pipelineFilter, sizeFilter, escoStageFilter]);

  // Auto-select first filtered config when filters change
  useEffect(() => {
    if (filteredConfigs.length > 0 && !filteredConfigs.find(c => c.name === selectedConfig)) {
      setSelectedConfig(filteredConfigs[0].name);
    }
  }, [filteredConfigs, selectedConfig]);

  // Get unique filter values from available configs
  const pipelines = useMemo(() =>
    [...new Set(availableConfigs.map(c => c.pipeline))].sort(),
    [availableConfigs]
  );
  const sizes = useMemo(() =>
    [...new Set(availableConfigs.map(c => c.size))].sort(),
    [availableConfigs]
  );
  const escoStages = useMemo(() =>
    [...new Set(availableConfigs.map(c => c.esco_stage))].sort(),
    [availableConfigs]
  );

  // Fetch clustering data and images when config changes
  useEffect(() => {
    if (!selectedConfig) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const [clusterData, imageData] = await Promise.all([
          getClusters(selectedConfig),
          getClusterImages(selectedConfig),
        ]);
        setData(clusterData);
        setImages(imageData.images);
        setError(null);
      } catch (err) {
        setError('Error al cargar clustering');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedConfig]);

  // Get current config info
  const currentConfig = availableConfigs.find(c => c.name === selectedConfig);

  // Get friendly pipeline name
  const getPipelineName = (pipeline: string) => {
    switch (pipeline) {
      case 'manual': return 'Manual (ONET)';
      case 'pipeline_a': return 'Pipeline A (NER + Regex)';
      case 'pipeline_b': return 'Pipeline B (LLM)';
      default: return pipeline;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Clustering de Habilidades</h1>
        <p className="text-gray-600 mt-2">
          Agrupación automática de habilidades similares mediante UMAP + HDBSCAN
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Filtros de Configuración</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Pipeline Filter */}
          <div>
            <label htmlFor="pipeline-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Pipeline de Extracción
            </label>
            <select
              id="pipeline-filter"
              value={pipelineFilter}
              onChange={(e) => setPipelineFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Todos</option>
              {pipelines.map((pipeline) => (
                <option key={pipeline} value={pipeline}>
                  {getPipelineName(pipeline)}
                </option>
              ))}
            </select>
          </div>

          {/* Size Filter */}
          <div>
            <label htmlFor="size-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Tamaño del Dataset
            </label>
            <select
              id="size-filter"
              value={sizeFilter}
              onChange={(e) => setSizeFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Todos</option>
              {sizes.map((size) => (
                <option key={size} value={size}>
                  {size === '30k' ? '30,000 jobs' : `${size} jobs`}
                </option>
              ))}
            </select>
          </div>

          {/* ESCO Stage Filter */}
          <div>
            <label htmlFor="esco-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Etapa ESCO
            </label>
            <select
              id="esco-filter"
              value={escoStageFilter}
              onChange={(e) => setEscoStageFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Todas</option>
              {escoStages.map((stage) => (
                <option key={stage} value={stage}>
                  {stage === 'pre' ? 'Pre-ESCO (original)' : 'Post-ESCO (normalizado)'}
                </option>
              ))}
            </select>
          </div>

          {/* Config Selector */}
          <div>
            <label htmlFor="config-selector" className="block text-sm font-medium text-gray-700 mb-1">
              Configuración ({filteredConfigs.length})
            </label>
            <select
              id="config-selector"
              value={selectedConfig}
              onChange={(e) => setSelectedConfig(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {filteredConfigs.map((config) => (
                <option key={config.name} value={config.name}>
                  {config.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Current Config Info */}
        {currentConfig && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex flex-wrap gap-3">
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                {getPipelineName(currentConfig.pipeline)}
              </span>
              <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                {currentConfig.size === '30k' ? '30,000 jobs' : `${currentConfig.size} jobs`}
              </span>
              <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
                {currentConfig.esco_stage === 'pre' ? 'Pre-ESCO' : 'Post-ESCO'}
              </span>
              <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm font-medium">
                {currentConfig.image_count} imágenes
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-4 text-gray-600">Cargando clustering...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 text-lg font-semibold mb-2">Error</h2>
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Clustering Data */}
      {data && !loading && !error && (
        <>
          {/* Images Gallery */}
          {images.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Visualizaciones ({images.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {images.map((image) => (
                  <div key={image.filename} className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition">
                    <img
                      src={`http://localhost:8000${image.url}`}
                      alt={image.filename}
                      className="w-full h-auto"
                    />
                    <div className="p-3 bg-gray-50">
                      <p className="text-sm font-medium text-gray-900 truncate">{image.filename}</p>
                      <p className="text-xs text-gray-600">{image.size_kb.toFixed(0)} KB</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Información del Análisis</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-gray-500">Algoritmo</p>
                <p className="text-lg font-semibold text-gray-900">{data.metadata.algorithm}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Habilidades Analizadas</p>
                <p className="text-lg font-semibold text-gray-900">{data.metadata.n_skills.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Fecha de Creación</p>
                <p className="text-lg font-semibold text-gray-900">
                  {new Date(data.metadata.created_at).toLocaleDateString('es-ES')}
                </p>
              </div>
            </div>

            {/* Parameters */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Parámetros</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-700 mb-2">UMAP</h4>
                  <div className="space-y-1 text-sm">
                    <p><span className="text-gray-600">Componentes:</span> {data.metadata.parameters.umap.n_components}</p>
                    <p><span className="text-gray-600">Vecinos:</span> {data.metadata.parameters.umap.n_neighbors}</p>
                    <p><span className="text-gray-600">Min Dist:</span> {data.metadata.parameters.umap.min_dist}</p>
                    <p><span className="text-gray-600">Métrica:</span> {data.metadata.parameters.umap.metric}</p>
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-700 mb-2">HDBSCAN</h4>
                  <div className="space-y-1 text-sm">
                    <p><span className="text-gray-600">Min Cluster Size:</span> {data.metadata.parameters.hdbscan.min_cluster_size}</p>
                    <p><span className="text-gray-600">Min Samples:</span> {data.metadata.parameters.hdbscan.min_samples}</p>
                    <p><span className="text-gray-600">Métrica:</span> {data.metadata.parameters.hdbscan.metric}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-sm text-gray-600">Clusters</p>
              <p className="text-3xl font-bold text-blue-600">{data.metrics.n_clusters}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-sm text-gray-600">Ruido</p>
              <p className="text-3xl font-bold text-orange-600">{data.metrics.n_noise}</p>
              <p className="text-xs text-gray-500">{data.metrics.noise_percentage.toFixed(1)}%</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-sm text-gray-600">Silhouette</p>
              <p className="text-3xl font-bold text-green-600">{data.metrics.silhouette_score.toFixed(3)}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-sm text-gray-600">Davies-Bouldin</p>
              <p className="text-3xl font-bold text-purple-600">{data.metrics.davies_bouldin_score.toFixed(3)}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-sm text-gray-600">Tamaño Promedio</p>
              <p className="text-3xl font-bold text-gray-900">{data.metrics.mean_cluster_size.toFixed(1)}</p>
            </div>
          </div>

          {/* Clusters List */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Clusters Identificados ({data.clusters.length})
            </h2>
            <div className="space-y-4">
              {data.clusters
                .sort((a, b) => b.size - a.size) // Sort by size descending
                .map((cluster) => (
                  <div
                    key={cluster.cluster_id}
                    className="border border-gray-200 rounded-lg p-4 hover:border-blue-500 transition"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <span className="inline-flex items-center justify-center w-10 h-10 bg-blue-100 text-blue-800 font-bold rounded-full">
                            {cluster.cluster_id}
                          </span>
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900">{cluster.label}</h3>
                            <p className="text-sm text-gray-600">
                              {cluster.size} habilidades • Frecuencia promedio: {cluster.mean_frequency.toFixed(1)}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Top Skills */}
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-2">Habilidades Principales:</p>
                      <div className="flex flex-wrap gap-2">
                        {cluster.top_skills.map((skill, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* All Skills (Expandable) */}
                    {cluster.all_skills && cluster.all_skills.length > 0 && (
                      <details className="mt-3">
                        <summary className="text-sm text-blue-600 cursor-pointer hover:text-blue-800">
                          Ver todas las habilidades ({cluster.all_skills.length})
                        </summary>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {cluster.all_skills.map((skill, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
