'use client';

import { useEffect, useState } from 'react';
import {
  getAvailableSpiders,
  getScrapingStatus,
  startScraping,
  stopScraping,
  ScrapingStatus,
  ScrapingTask,
  getLLMStatus,
  downloadGemma,
  runPipelineB,
  LLMStatus,
} from '@/lib/api';

export default function AdminPage() {
  const [status, setStatus] = useState<ScrapingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [availableSpiders, setAvailableSpiders] = useState<string[]>([]);
  const [availableCountries, setAvailableCountries] = useState<string[]>([]);

  // Form state
  const [selectedSpiders, setSelectedSpiders] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [maxJobs, setMaxJobs] = useState<number>(100);
  const [maxPages, setMaxPages] = useState<number>(10);
  const [isStarting, setIsStarting] = useState(false);

  // LLM Pipeline B state
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);
  const [isDownloadingGemma, setIsDownloadingGemma] = useState(false);
  const [pipelineBLimit, setPipelineBLimit] = useState<number>(100);
  const [pipelineBCountry, setPipelineBCountry] = useState<string>('');
  const [isRunningPipelineB, setIsRunningPipelineB] = useState(false);

  // Fetch available spiders and countries
  useEffect(() => {
    const fetchAvailable = async () => {
      try {
        const result = await getAvailableSpiders();
        setAvailableSpiders(result.spiders);
        setAvailableCountries(result.countries);
      } catch (err) {
        console.error('Error fetching available:', err);
      }
    };
    fetchAvailable();
  }, []);

  // Fetch LLM status
  useEffect(() => {
    const fetchLLMStatus = async () => {
      try {
        const result = await getLLMStatus();
        setLlmStatus(result);
      } catch (err) {
        console.error('Error fetching LLM status:', err);
      }
    };
    fetchLLMStatus();
    // Refresh every 10 seconds
    const interval = setInterval(fetchLLMStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  // Fetch scraping status
  const fetchStatus = async () => {
    setLoading(true);
    try {
      const result = await getScrapingStatus();
      setStatus(result);
      setError(null);
    } catch (err) {
      setError('Error al cargar estado');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStartScraping = async () => {
    if (selectedSpiders.length === 0) {
      alert('Selecciona al menos un portal');
      return;
    }
    if (selectedCountries.length === 0) {
      alert('Selecciona al menos un país');
      return;
    }

    setIsStarting(true);
    try {
      await startScraping({
        spiders: selectedSpiders,
        countries: selectedCountries,
        max_jobs: maxJobs,
        max_pages: maxPages,
      });
      // Clear form
      setSelectedSpiders([]);
      setSelectedCountries([]);
      setMaxJobs(100);
      setMaxPages(10);
      // Refresh status
      await fetchStatus();
      alert('Scraping iniciado exitosamente');
    } catch (err) {
      console.error('Error starting scraping:', err);
      alert('Error al iniciar scraping');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopTask = async (taskId: string) => {
    if (!confirm('¿Estás seguro de detener esta tarea?')) return;

    try {
      await stopScraping(taskId);
      await fetchStatus();
      alert('Tarea detenida');
    } catch (err) {
      console.error('Error stopping task:', err);
      alert('Error al detener tarea');
    }
  };

  const toggleSpider = (spider: string) => {
    setSelectedSpiders(prev =>
      prev.includes(spider)
        ? prev.filter(s => s !== spider)
        : [...prev, spider]
    );
  };

  const toggleCountry = (country: string) => {
    setSelectedCountries(prev =>
      prev.includes(country)
        ? prev.filter(c => c !== country)
        : [...prev, country]
    );
  };

  const handleDownloadGemma = async () => {
    if (!confirm('¿Descargar Gemma 3 4B (2.8 GB)? Puede tardar 5-10 minutos.')) return;

    setIsDownloadingGemma(true);
    try {
      const result = await downloadGemma();
      alert(result.message);
      // Refresh LLM status after a few seconds
      setTimeout(async () => {
        const newStatus = await getLLMStatus();
        setLlmStatus(newStatus);
      }, 3000);
    } catch (err) {
      console.error('Error downloading Gemma:', err);
      alert('Error al descargar Gemma');
    } finally {
      setIsDownloadingGemma(false);
    }
  };

  const handleRunPipelineB = async () => {
    if (pipelineBLimit <= 0) {
      alert('Debes especificar un límite mayor a 0');
      return;
    }

    setIsRunningPipelineB(true);
    try {
      const result = await runPipelineB({
        limit: pipelineBLimit,
        country: pipelineBCountry || undefined,
        model: 'gemma-3-4b-instruct'
      });
      alert(`Pipeline B iniciado: ${result.message}\nTask ID: ${result.task_id}`);
      // Reset form
      setPipelineBLimit(100);
      setPipelineBCountry('');
    } catch (err: any) {
      console.error('Error running Pipeline B:', err);
      const errorMsg = err.response?.data?.detail || 'Error al iniciar Pipeline B';
      alert(errorMsg);
    } finally {
      setIsRunningPipelineB(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Administración</h1>
        <p className="text-gray-600 mt-2">Control del sistema y tareas de scraping</p>
      </div>

      {/* System Status */}
      {status && (
        <div className={`rounded-lg p-4 ${
          status.system_status === 'operational'
            ? 'bg-green-50 border border-green-200'
            : 'bg-red-50 border border-red-200'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className={`inline-block w-3 h-3 rounded-full ${
                status.system_status === 'operational' ? 'bg-green-600' : 'bg-red-600'
              }`}></span>
              <p className="font-medium">
                Estado del Sistema: {status.system_status === 'operational' ? 'Operativo' : 'Error'}
              </p>
            </div>
            <p className="text-sm">
              Tareas activas: <span className="font-bold">{status.total_active}</span>
            </p>
          </div>
        </div>
      )}

      {/* New Scraping Task */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Iniciar Nuevo Scraping</h2>

        <div className="space-y-6">
          {/* Spiders Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Portales de Empleo
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {availableSpiders.map(spider => (
                <button
                  key={spider}
                  onClick={() => toggleSpider(spider)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                    selectedSpiders.includes(spider)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {spider}
                </button>
              ))}
            </div>
          </div>

          {/* Countries Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Países
            </label>
            <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
              {availableCountries.map(country => (
                <button
                  key={country}
                  onClick={() => toggleCountry(country)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                    selectedCountries.includes(country)
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {country}
                </button>
              ))}
            </div>
          </div>

          {/* Parameters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="max-jobs" className="block text-sm font-medium text-gray-700 mb-2">
                Máximo de Empleos
              </label>
              <input
                id="max-jobs"
                type="number"
                value={maxJobs}
                onChange={(e) => setMaxJobs(Number(e.target.value))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="max-pages" className="block text-sm font-medium text-gray-700 mb-2">
                Máximo de Páginas
              </label>
              <input
                id="max-pages"
                type="number"
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={handleStartScraping}
            disabled={isStarting || selectedSpiders.length === 0 || selectedCountries.length === 0}
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStarting ? 'Iniciando...' : 'Iniciar Scraping'}
          </button>
        </div>
      </div>

      {/* LLM Pipeline B */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Pipeline B - Extracción LLM</h2>

        {llmStatus && (
          <div className={`rounded-lg p-4 mb-4 ${
            llmStatus.ready
              ? 'bg-green-50 border border-green-200'
              : 'bg-yellow-50 border border-yellow-200'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`inline-block w-3 h-3 rounded-full ${
                  llmStatus.ready ? 'bg-green-600' : 'bg-yellow-600'
                }`}></span>
                <div>
                  <p className="font-medium">
                    {llmStatus.model_name} - {llmStatus.downloaded ? 'Descargado' : 'No descargado'}
                  </p>
                  <p className="text-sm text-gray-600">Tamaño: {llmStatus.size_gb} GB</p>
                </div>
              </div>
              {!llmStatus.downloaded && (
                <button
                  onClick={handleDownloadGemma}
                  disabled={isDownloadingGemma}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isDownloadingGemma ? 'Descargando...' : 'Descargar Modelo'}
                </button>
              )}
            </div>
          </div>
        )}

        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="pipeline-b-limit" className="block text-sm font-medium text-gray-700 mb-2">
                Cantidad de Empleos a Procesar
              </label>
              <input
                id="pipeline-b-limit"
                type="number"
                value={pipelineBLimit}
                onChange={(e) => setPipelineBLimit(Number(e.target.value))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="pipeline-b-country" className="block text-sm font-medium text-gray-700 mb-2">
                País (Opcional)
              </label>
              <select
                id="pipeline-b-country"
                value={pipelineBCountry}
                onChange={(e) => setPipelineBCountry(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos los países</option>
                {availableCountries.map(country => (
                  <option key={country} value={country}>{country}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={handleRunPipelineB}
            disabled={isRunningPipelineB || !llmStatus?.ready}
            className="w-full px-6 py-3 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRunningPipelineB ? 'Iniciando Pipeline B...' : 'Ejecutar Pipeline B'}
          </button>

          {!llmStatus?.ready && (
            <p className="text-sm text-yellow-600 text-center">
              Descarga el modelo Gemma primero para habilitar Pipeline B
            </p>
          )}
        </div>
      </div>

      {/* Active Tasks */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Tareas Activas {status && `(${status.total_active})`}
        </h2>

        {loading && !status && (
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
              <p className="mt-2 text-gray-600 text-sm">Cargando...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-600">{error}</p>
          </div>
        )}

        {status && status.active_tasks.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500">No hay tareas activas</p>
          </div>
        )}

        {status && status.active_tasks.length > 0 && (
          <div className="space-y-4">
            {status.active_tasks.map(task => (
              <div
                key={task.task_id}
                className="border border-gray-200 rounded-lg p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Tarea {task.task_id.slice(0, 8)}
                      </h3>
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        task.status === 'running'
                          ? 'bg-green-100 text-green-800'
                          : task.status === 'completed'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {task.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p><strong>Portales:</strong> {task.spiders.join(', ')}</p>
                      <p><strong>Países:</strong> {task.countries.join(', ')}</p>
                      <p><strong>Límites:</strong> {task.max_jobs} empleos, {task.max_pages} páginas</p>
                      <p><strong>Iniciada:</strong> {new Date(task.started_at).toLocaleString('es-ES')}</p>
                      {task.completed_at && (
                        <p><strong>Completada:</strong> {new Date(task.completed_at).toLocaleString('es-ES')}</p>
                      )}
                      {task.pid && <p><strong>PID:</strong> {task.pid}</p>}
                      {task.error && (
                        <p className="text-red-600"><strong>Error:</strong> {task.error}</p>
                      )}
                    </div>
                  </div>
                  {task.status === 'running' && (
                    <button
                      onClick={() => handleStopTask(task.task_id)}
                      className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition text-sm font-medium"
                    >
                      Detener
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
