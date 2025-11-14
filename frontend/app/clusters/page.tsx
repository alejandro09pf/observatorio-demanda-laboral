'use client';

import { useEffect, useState } from 'react';
import {
  getClusters,
  getAvailableClusterConfigs,
  ClusteringResponse,
} from '@/lib/api';

export default function ClustersPage() {
  const [data, setData] = useState<ClusteringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [availableConfigs, setAvailableConfigs] = useState<string[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>('');

  // Fetch available configs on mount
  useEffect(() => {
    const fetchConfigs = async () => {
      try {
        const result = await getAvailableClusterConfigs();
        setAvailableConfigs(result.configs);
        // Set first config as default if available
        if (result.configs.length > 0) {
          setSelectedConfig(result.configs[0]);
        }
      } catch (err) {
        console.error('Error fetching configs:', err);
      }
    };
    fetchConfigs();
  }, []);

  // Fetch clustering data when config changes
  useEffect(() => {
    if (!selectedConfig) return;

    const fetchClusters = async () => {
      setLoading(true);
      try {
        const result = await getClusters(selectedConfig);
        setData(result);
        setError(null);
      } catch (err) {
        setError('Error al cargar clustering');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchClusters();
  }, [selectedConfig]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Clustering de Habilidades</h1>
        <p className="text-gray-600 mt-2">
          Agrupación automática de habilidades similares
        </p>
      </div>

      {/* Configuration Selector */}
      {availableConfigs.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <label htmlFor="config-selector" className="block text-sm font-medium text-gray-700 mb-2">
            Configuración de Clustering
          </label>
          <select
            id="config-selector"
            value={selectedConfig}
            onChange={(e) => setSelectedConfig(e.target.value)}
            className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {availableConfigs.map((config) => (
              <option key={config} value={config}>
                {config.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </select>
        </div>
      )}

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
                  </div>
                ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
