'use client';

import { useEffect, useState } from 'react';
import {
  getScrapingStatus,
  startScraping,
  stopScraping,
  ScrapingStatus,
  getAvailableSpiders,
} from '@/lib/api';

interface ExtractionStats {
  total_jobs: number;
  pending: number;
  completed: number;
  failed: number;
  total_skills_extracted: number;
  completion_rate: number;
}

interface EnhancementStats {
  total_jobs: number;
  pending: number;
  completed: number;
  failed: number;
  total_enhanced: number;
  completion_rate: number;
}

interface ScheduleTask {
  name: string;
  schedule: string;
  spider?: string;
  country?: string;
  max_jobs?: number;
  pipeline?: string;
  n_clusters?: number;
}

interface CelerySchedule {
  scraping_tasks: ScheduleTask[];
  extraction_tasks: ScheduleTask[];
  clustering_tasks: ScheduleTask[];
  other_tasks: ScheduleTask[];
  total_scheduled_tasks: number;
}

export default function AdminPage() {
  const [scrapingStatus, setScrapingStatus] = useState<ScrapingStatus | null>(null);
  const [extractionStats, setExtractionStats] = useState<ExtractionStats | null>(null);
  const [enhancementStats, setEnhancementStats] = useState<EnhancementStats | null>(null);
  const [schedule, setSchedule] = useState<CelerySchedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Scraping config
  const [availableSpiders, setAvailableSpiders] = useState<string[]>([]);
  const [availableCountries, setAvailableCountries] = useState<string[]>([]);

  // Fetch all status data
  const fetchAllData = async () => {
    try {
      // Fetch with error handling for each endpoint
      const [scraping, extraction, enhancement, available, scheduleData] = await Promise.all([
        fetch('http://localhost:8000/api/admin/scraping/status')
          .then(r => r.json())
          .catch(() => ({ active_tasks: [], total_active: 0, system_status: 'unavailable' })),
        fetch('http://localhost:8000/api/admin/extraction/stats')
          .then(r => r.json())
          .catch(() => null),
        fetch('http://localhost:8000/api/admin/enhancement/stats')
          .then(r => r.json())
          .catch(() => null),
        getAvailableSpiders().catch(() => ({ spiders: [], countries: [] })),
        fetch('http://localhost:8000/api/admin/schedule')
          .then(r => r.json())
          .catch(() => null),
      ]);

      setScrapingStatus(scraping);
      setExtractionStats(extraction);
      setEnhancementStats(enhancement);
      setAvailableSpiders(available.spiders || []);
      setAvailableCountries(available.countries || []);
      setSchedule(scheduleData);
      setError(null);
    } catch (err) {
      console.error('Error fetching admin data:', err);
      setError('Error al cargar datos de administración');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchAllData, 10000);
    return () => clearInterval(interval);
  }, []);


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando panel de administración...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h2 className="text-red-800 text-lg font-semibold mb-2">Error</h2>
        <p className="text-red-600">{error}</p>
        <button
          onClick={fetchAllData}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Panel de Administración</h1>
        <p className="text-gray-600 mt-2">
          Gestión y monitoreo del observatorio laboral
        </p>
      </div>

      {/* Scraping Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">🔄 Scraping de Datos</h2>

        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <h3 className="font-semibold text-gray-900 mb-3">📊 Estado Actual</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-600">Estado del Sistema:</span>
              <span className={`ml-2 font-medium ${
                scrapingStatus?.system_status === 'operational' ? 'text-green-600' :
                scrapingStatus?.system_status === 'unavailable' ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {scrapingStatus?.system_status === 'operational' ? '✅ Operacional' :
                 scrapingStatus?.system_status === 'unavailable' ? '⚠️ No disponible (Celery)' :
                 '❌ Con problemas'}
              </span>
            </div>
            <div>
              <span className="text-sm text-gray-600">Tareas Activas:</span>
              <span className="ml-2 font-medium">
                {scrapingStatus?.total_active || 0}
              </span>
            </div>
          </div>

          {scrapingStatus && scrapingStatus.active_tasks && scrapingStatus.active_tasks.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Tareas en Ejecución:</h4>
              {scrapingStatus.active_tasks.map((task: any) => (
                <div key={task.task_id} className="bg-white rounded p-3 mb-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium">{task.config?.spiders?.join(', ') || 'N/A'}</span>
                      <span className="text-sm text-gray-500 ml-2">
                        ({task.config?.country || 'N/A'})
                      </span>
                    </div>
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      {task.status || 'running'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {scrapingStatus?.system_status === 'unavailable' && (
            <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm text-yellow-800">
                ⚠️ Sistema de scraping no disponible (Celery workers no están corriendo)
              </p>
            </div>
          )}
        </div>

        {schedule && schedule.scraping_tasks && schedule.scraping_tasks.length > 0 && (
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4">
            <h3 className="font-semibold text-blue-900 mb-3">⏰ Tareas Programadas de Scraping</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
              {schedule.scraping_tasks.map((task, idx) => (
                <div key={idx} className="bg-white rounded p-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{task.spider}</span>
                    <span className="text-xs px-2 py-0.5 bg-gray-100 rounded">{task.country}</span>
                  </div>
                  <span className="text-xs text-gray-600">{task.schedule}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-blue-700 mt-3 italic">
              💡 {schedule.scraping_tasks.length} tareas automáticas configuradas en Celery Beat
            </p>
          </div>
        )}
      </div>

      {/* Pipeline Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">📊 Estado del Pipeline de Procesamiento</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Extraction (Pipeline A) */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-3">🎯 Extracción de Skills (Pipeline A)</h3>
            {extractionStats ? (
              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total Jobs:</span>
                  <span className="font-medium">{(extractionStats.total_jobs || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Completados:</span>
                  <span className="font-medium text-green-600">{(extractionStats.completed || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Pendientes:</span>
                  <span className="font-medium text-orange-600">{(extractionStats.pending || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Fallidos:</span>
                  <span className="font-medium text-red-600">{(extractionStats.failed || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Skills Extraídas:</span>
                  <span className="font-medium text-blue-600">{(extractionStats.total_skills_extracted || 0).toLocaleString()}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
                  <div
                    className="bg-green-600 h-2 rounded-full"
                    style={{ width: `${extractionStats.completion_rate || 0}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 text-right">{(extractionStats.completion_rate || 0).toFixed(1)}% completado</p>
              </div>
            ) : (
              <div className="text-sm text-gray-500 mb-4 p-4 bg-gray-50 rounded">
                Cargando estadísticas...
              </div>
            )}
          </div>

          {/* Enhancement (Pipeline B) */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-3">🤖 Enhancement LLM (Pipeline B)</h3>
            {enhancementStats ? (
              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total Jobs:</span>
                  <span className="font-medium">{(enhancementStats.total_jobs || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Completados:</span>
                  <span className="font-medium text-green-600">{(enhancementStats.completed || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Pendientes:</span>
                  <span className="font-medium text-orange-600">{(enhancementStats.pending || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Fallidos:</span>
                  <span className="font-medium text-red-600">{(enhancementStats.failed || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Skills Mejoradas:</span>
                  <span className="font-medium text-purple-600">{(enhancementStats.total_enhanced || 0).toLocaleString()}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
                  <div
                    className="bg-purple-600 h-2 rounded-full"
                    style={{ width: `${enhancementStats.completion_rate || 0}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 text-right">{(enhancementStats.completion_rate || 0).toFixed(1)}% completado</p>
              </div>
            ) : (
              <div className="text-sm text-gray-500 mb-4 p-4 bg-gray-50 rounded">
                Cargando estadísticas...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-gradient-to-r from-gray-700 to-gray-900 rounded-lg shadow p-6 text-white">
        <h2 className="text-xl font-bold mb-4">ℹ️ Información del Sistema</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-300">Versión</p>
            <p className="font-semibold">1.0.0</p>
          </div>
          <div>
            <p className="text-gray-300">Database</p>
            <p className="font-semibold">PostgreSQL 15</p>
          </div>
          <div>
            <p className="text-gray-300">Cache</p>
            <p className="font-semibold">Redis</p>
          </div>
          <div>
            <p className="text-gray-300">Workers</p>
            <p className="font-semibold">Celery</p>
          </div>
        </div>
      </div>
    </div>
  );
}
