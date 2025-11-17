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

  // Filters - Changed from pipeline to data source (pipeline + size)
  const [dataSourceFilter, setDataSourceFilter] = useState<string>('manual_golden');
  const [escoStageFilter, setEscoStageFilter] = useState<string>('pre');

  // Image modal state
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);

  // Fetch available configs on mount
  useEffect(() => {
    const fetchConfigs = async () => {
      try {
        const result = await getAvailableClusterConfigs();
        setAvailableConfigs(result.configs);
        // Set default config based on filters
        const defaultConfig = result.configs.find(
          c => c.pipeline === 'manual' && c.size === '300' && c.esco_stage === 'pre'
        );
        if (defaultConfig) {
          setSelectedConfig(defaultConfig.name);
        } else if (result.configs.length > 0) {
          setSelectedConfig(result.configs[0].name);
        }
      } catch (err) {
        console.error('Error fetching configs:', err);
      }
    };
    fetchConfigs();
  }, []);

  // Auto-select config when filters change
  useEffect(() => {
    // Parse dataSourceFilter to get pipeline and size
    let pipeline = 'manual';
    let size = '300';

    if (dataSourceFilter === 'manual_golden') {
      pipeline = 'manual';
      size = '300';
    } else if (dataSourceFilter === 'pipeline_a_golden') {
      pipeline = 'pipeline_a';
      size = '300';
    } else if (dataSourceFilter === 'pipeline_b_golden') {
      pipeline = 'pipeline_b';
      size = '300';
    } else if (dataSourceFilter === 'pipeline_a_all') {
      pipeline = 'pipeline_a';
      size = '30k';
    }

    const matchingConfig = availableConfigs.find(
      c => c.pipeline === pipeline && c.size === size && c.esco_stage === escoStageFilter
    );
    if (matchingConfig) {
      setSelectedConfig(matchingConfig.name);
    }
  }, [dataSourceFilter, escoStageFilter, availableConfigs]);

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

  // Get friendly data source name
  const getDataSourceName = (dataSource: string) => {
    switch (dataSource) {
      case 'manual_golden': return 'Manual (ONET Golden)';
      case 'pipeline_a_golden': return 'Pipeline A Golden';
      case 'pipeline_b_golden': return 'Pipeline B (LLM Golden)';
      case 'pipeline_a_all': return 'Pipeline A (Todos)';
      default: return dataSource;
    }
  };

  // Image modal navigation
  const openImageModal = (index: number) => {
    setSelectedImageIndex(index);
  };

  const closeImageModal = () => {
    setSelectedImageIndex(null);
  };

  const nextImage = () => {
    if (selectedImageIndex !== null && selectedImageIndex < images.length - 1) {
      setSelectedImageIndex(selectedImageIndex + 1);
    }
  };

  const previousImage = () => {
    if (selectedImageIndex !== null && selectedImageIndex > 0) {
      setSelectedImageIndex(selectedImageIndex - 1);
    }
  };

  // Keyboard navigation for modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (selectedImageIndex === null) return;

      if (e.key === 'Escape') closeImageModal();
      if (e.key === 'ArrowRight') nextImage();
      if (e.key === 'ArrowLeft') previousImage();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedImageIndex, images.length]);

  return (
    <div className="space-y-4">
      {/* Header with Filters */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Clustering de Habilidades</h1>
          <p className="text-gray-600 mt-1">
            Agrupación automática de habilidades similares mediante UMAP + HDBSCAN
          </p>
        </div>

        {/* Compact Filters */}
        <div className="bg-white rounded-lg shadow p-4 min-w-[450px]">
          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label htmlFor="data-source-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Datos
              </label>
              <select
                id="data-source-filter"
                value={dataSourceFilter}
                onChange={(e) => setDataSourceFilter(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="manual_golden">Manual (ONET Golden)</option>
                <option value="pipeline_a_golden">Pipeline A Golden</option>
                <option value="pipeline_b_golden">Pipeline B (LLM Golden)</option>
                <option value="pipeline_a_all">Pipeline A (Todos)</option>
              </select>
            </div>

            <div>
              <label htmlFor="esco-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Etapa ESCO
              </label>
              <select
                id="esco-filter"
                value={escoStageFilter}
                onChange={(e) => setEscoStageFilter(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="pre">Pre-ESCO</option>
                <option value="post">Post-ESCO</option>
              </select>
            </div>
          </div>

          {/* Current Config Info */}
          {currentConfig && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                  {getDataSourceName(dataSourceFilter)}
                </span>
                <span className="px-2 py-0.5 bg-green-100 text-green-800 rounded text-xs font-medium">
                  {currentConfig.size === '30k' ? '30,000 jobs' : `${currentConfig.size} jobs`}
                </span>
                <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded text-xs font-medium">
                  {currentConfig.esco_stage === 'pre' ? 'Pre-ESCO' : 'Post-ESCO'}
                </span>
                <span className="px-2 py-0.5 bg-gray-100 text-gray-800 rounded text-xs font-medium">
                  {currentConfig.image_count} imágenes
                </span>
              </div>
            </div>
          )}
        </div>
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
                {images.map((image, idx) => (
                  <div
                    key={image.filename}
                    className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition cursor-pointer"
                    onClick={() => openImageModal(idx)}
                  >
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

      {/* Image Modal */}
      {selectedImageIndex !== null && (
        <div
          className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
          onClick={closeImageModal}
        >
          <div className="relative max-w-7xl max-h-full" onClick={(e) => e.stopPropagation()}>
            {/* Close Button */}
            <button
              onClick={closeImageModal}
              className="absolute -top-12 right-0 text-white hover:text-gray-300 transition"
              aria-label="Cerrar"
            >
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Image Info */}
            <div className="absolute -top-12 left-0 text-white text-sm">
              <p className="font-medium">{images[selectedImageIndex].filename}</p>
              <p className="text-gray-300">
                {selectedImageIndex + 1} de {images.length}
              </p>
            </div>

            {/* Previous Button */}
            {selectedImageIndex > 0 && (
              <button
                onClick={previousImage}
                className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-16 text-white hover:text-gray-300 transition"
                aria-label="Anterior"
              >
                <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            )}

            {/* Image */}
            <img
              src={`http://localhost:8000${images[selectedImageIndex].url}`}
              alt={images[selectedImageIndex].filename}
              className="max-w-full max-h-[85vh] w-auto h-auto mx-auto rounded-lg shadow-2xl"
            />

            {/* Next Button */}
            {selectedImageIndex < images.length - 1 && (
              <button
                onClick={nextImage}
                className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-16 text-white hover:text-gray-300 transition"
                aria-label="Siguiente"
              >
                <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            )}

            {/* Keyboard Hints */}
            <div className="absolute -bottom-12 left-0 right-0 text-center text-white text-xs text-gray-400">
              <p>Usa las flechas ← → para navegar • ESC para cerrar</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
