'use client';

import { useEffect, useState } from 'react';
import { getStats, getFilteredStats, StatsResponse, FilteredStatsResponse } from '@/lib/api';
import Link from 'next/link';

export default function Dashboard() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [filteredStats, setFilteredStats] = useState<FilteredStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [countryFilter, setCountryFilter] = useState<string>('all');
  const [jobStatusFilter, setJobStatusFilter] = useState<string>('all');
  const [extractionMethodFilter, setExtractionMethodFilter] = useState<string>('all');
  const [mappingStatusFilter, setMappingStatusFilter] = useState<string>('all');

  // Fetch base stats (always)
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getStats();
        setStats(data);
      } catch (err) {
        setError('Error al cargar estadísticas');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  // Fetch filtered stats when filters change
  useEffect(() => {
    const fetchFilteredStats = async () => {
      try {
        const params: any = {};
        if (countryFilter !== 'all') params.country = countryFilter;
        if (jobStatusFilter !== 'all') params.job_status = jobStatusFilter;
        if (extractionMethodFilter !== 'all') params.extraction_method = extractionMethodFilter;
        if (mappingStatusFilter !== 'all') params.mapping_status = mappingStatusFilter;

        const data = await getFilteredStats(params);
        setFilteredStats(data);
      } catch (err) {
        console.error('Error fetching filtered stats:', err);
      }
    };

    // Only fetch if at least one filter is active
    if (countryFilter !== 'all' || jobStatusFilter !== 'all' ||
        extractionMethodFilter !== 'all' || mappingStatusFilter !== 'all') {
      fetchFilteredStats();
    } else {
      setFilteredStats(null);
    }
  }, [countryFilter, jobStatusFilter, extractionMethodFilter, mappingStatusFilter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando panel principal...</p>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 text-lg font-semibold mb-2">Error</h2>
          <p className="text-red-600">{error || 'Error al cargar datos'}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // Use filtered stats if available, otherwise use base stats
  const displayJobsTotal = filteredStats?.jobs.total ?? stats.total_raw_jobs;
  const displayCleanedJobs = filteredStats?.jobs.cleaned ?? stats.total_cleaned_jobs;
  const displayJobsWithSkills = filteredStats?.jobs.with_skills ?? stats.total_jobs_with_skills;
  const displaySkillsTotal = filteredStats?.skills.total ?? stats.total_skills;
  const displaySkillsUnique = filteredStats?.skills.unique ?? stats.total_unique_skills;
  const displayPipelineBGemma = filteredStats?.extraction_methods.pipeline_b_gemma ?? stats.extraction_methods?.pipeline_b_gemma;
  const displayPipelineBJobs = filteredStats?.extraction_methods.pipeline_b_jobs ?? stats.extraction_methods?.pipeline_b_jobs;
  const displayCountries = filteredStats?.countries ?? stats.countries;
  const displayPortals = filteredStats?.portals ?? stats.portals;
  const displayDateRange = filteredStats?.date_range ?? stats.date_range;

  const hasActiveFilters = countryFilter !== 'all' || jobStatusFilter !== 'all' ||
                           extractionMethodFilter !== 'all' || mappingStatusFilter !== 'all';

  return (
    <div className="space-y-6">
      {/* Header with Filters */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Panel Principal</h1>
          <p className="text-gray-600 mt-2">
            Resumen de datos del mercado laboral y análisis
          </p>
        </div>

        {/* Compact Filters */}
        <div className="flex flex-wrap gap-2 items-center">
          <select
            value={countryFilter}
            onChange={(e) => setCountryFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todos los países</option>
            {stats.countries?.map((country) => (
              <option key={country} value={country}>{country}</option>
            ))}
          </select>

          <select
            value={jobStatusFilter}
            onChange={(e) => setJobStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todos los estados</option>
            <option value="raw">Raw</option>
            <option value="cleaned">Limpiados</option>
            <option value="golden">Golden</option>
          </select>

          <select
            value={extractionMethodFilter}
            onChange={(e) => setExtractionMethodFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todos los métodos</option>
            <option value="ner">NER</option>
            <option value="regex">Regex</option>
            <option value="pipeline_a">Pipeline A</option>
            <option value="pipeline_b">Pipeline B</option>
          </select>

          <select
            value={mappingStatusFilter}
            onChange={(e) => setMappingStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todos los mapeos</option>
            <option value="esco_mapped">ESCO</option>
            <option value="unmapped">Sin mapear</option>
          </select>

          {hasActiveFilters && (
            <button
              onClick={() => {
                setCountryFilter('all');
                setJobStatusFilter('all');
                setExtractionMethodFilter('all');
                setMappingStatusFilter('all');
              }}
              className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              title="Limpiar filtros"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Filter Status Banner */}
      {hasActiveFilters && (
        <div className="bg-blue-50 border-l-4 border-blue-500 p-3">
          <p className="text-blue-800 text-sm font-medium">
            Filtros activos - Mostrando datos filtrados
          </p>
        </div>
      )}

      {/* Data Funnel Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Proceso de Datos {hasActiveFilters && <span className="text-blue-600">(Filtrado)</span>}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-4xl font-bold text-blue-600">
              {displayJobsTotal?.toLocaleString() || '0'}
            </div>
            <div className="text-sm text-gray-600 mt-2">
              {hasActiveFilters ? 'Empleos (Filtrados)' : 'Empleos Recolectados'}
            </div>
            <div className="text-xs text-gray-500">
              {!hasActiveFilters && 'Datos crudos del scraping'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-green-600">
              {displayCleanedJobs?.toLocaleString() || '0'}
            </div>
            <div className="text-sm text-gray-600 mt-2">
              {hasActiveFilters ? 'Limpiados (Filtrados)' : 'Empleos Limpiados'}
            </div>
            <div className="text-xs text-gray-500">
              {displayJobsTotal ? ((displayCleanedJobs / displayJobsTotal) * 100).toFixed(1) : '0'}% retenido
            </div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-purple-600">
              {displayJobsWithSkills?.toLocaleString() || '0'}
            </div>
            <div className="text-sm text-gray-600 mt-2">Con Habilidades</div>
            <div className="text-xs text-gray-500">
              {displayCleanedJobs ? ((displayJobsWithSkills / displayCleanedJobs) * 100).toFixed(1) : '0'}% procesado
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Habilidades Extraídas"
          value={displaySkillsTotal?.toLocaleString() || '0'}
          subtitle={`${displaySkillsUnique?.toLocaleString() || '0'} únicas`}
          icon="🎯"
          link="/skills"
        />
        <KPICard
          title="Pipeline A (NER + Regex)"
          value={filteredStats?.extraction_methods.pipeline_a?.toLocaleString() || stats.extraction_methods?.pipeline_a1?.toLocaleString() || '0'}
          subtitle="Extracción basada en reglas"
          icon="📝"
        />
        <KPICard
          title="Pipeline B (Gemma LLM)"
          value={displayPipelineBGemma?.toLocaleString() || '0'}
          subtitle={`En ${displayPipelineBJobs?.toLocaleString() || '0'} empleos`}
          icon="🤖"
        />
        <KPICard
          title="Países Analizados"
          value={displayCountries?.length.toString() || '0'}
          subtitle={displayCountries?.join(', ') || 'N/A'}
          icon="🌎"
        />
      </div>

      {/* Extraction Methods Breakdown (when filtered) */}
      {filteredStats && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Desglose de Métodos de Extracción (Filtrado)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-blue-700">
                {filteredStats.extraction_methods.ner.toLocaleString()}
              </div>
              <div className="text-sm text-gray-600 mt-1">NER</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-green-700">
                {filteredStats.extraction_methods.regex.toLocaleString()}
              </div>
              <div className="text-sm text-gray-600 mt-1">Regex</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="text-2xl font-bold text-purple-700">
                {filteredStats.extraction_methods.pipeline_a.toLocaleString()}
              </div>
              <div className="text-sm text-gray-600 mt-1">Pipeline A (Total)</div>
            </div>
          </div>
        </div>
      )}

      {/* Date Range and Last Scraping */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Rango de Datos
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Fecha Inicial:</span>
              <span className="font-semibold text-gray-900">
                {displayDateRange?.start ? new Date(displayDateRange.start).toLocaleDateString('es-ES') : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Fecha Final:</span>
              <span className="font-semibold text-gray-900">
                {displayDateRange?.end ? new Date(displayDateRange.end).toLocaleDateString('es-ES') : 'N/A'}
              </span>
            </div>
            {!hasActiveFilters && (
              <div className="flex justify-between items-center pt-3 border-t border-gray-200">
                <span className="text-gray-600">Último Scraping:</span>
                <span className="font-semibold text-gray-900">
                  {stats.last_scraping ? new Date(stats.last_scraping).toLocaleString('es-ES') : 'N/A'}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Distribución por Países {hasActiveFilters && <span className="text-blue-600 text-sm">(Filtrado)</span>}
          </h3>
          <div className="space-y-3">
            {displayCountries?.map((country) => (
              <div key={country} className="flex items-center justify-between">
                <span className="text-gray-700 font-medium">{country}</span>
                <Link
                  href={`/jobs?country=${country}`}
                  className="text-blue-600 hover:text-blue-800 text-sm"
                >
                  Ver Empleos
                </Link>
              </div>
            )) || <p className="text-gray-500">Sin datos</p>}
          </div>
        </div>
      </div>

      {/* Portals List */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Portales de Empleo {hasActiveFilters ? '(Filtrado)' : 'Soportados'}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          {displayPortals?.map((portal) => (
            <div
              key={portal}
              className="flex items-center justify-center p-3 bg-gray-50 rounded-lg border border-gray-200"
            >
              <span className="text-sm font-medium text-gray-700 capitalize">
                {portal}
              </span>
            </div>
          )) || <p className="text-gray-500">Sin datos</p>}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg shadow-lg p-6 text-white">
        <h3 className="text-xl font-semibold mb-4">Acciones Rápidas</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Link
            href="/jobs"
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 transition"
          >
            <div className="text-2xl mb-2">🔍</div>
            <div className="font-semibold">Explorar Empleos</div>
            <div className="text-sm text-blue-100 mt-1">
              Explora {stats.total_raw_jobs?.toLocaleString() || '0'} ofertas laborales
            </div>
          </Link>
          <Link
            href="/skills"
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 transition"
          >
            <div className="text-2xl mb-2">📈</div>
            <div className="font-semibold">Analizar Habilidades</div>
            <div className="text-sm text-blue-100 mt-1">
              Ver demanda de {stats.total_unique_skills?.toLocaleString() || '0'} habilidades
            </div>
          </Link>
          <Link
            href="/clusters"
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 transition"
          >
            <div className="text-2xl mb-2">🎯</div>
            <div className="font-semibold">Ver Clusters</div>
            <div className="text-sm text-blue-100 mt-1">
              Explorar 8 configuraciones de clustering
            </div>
          </Link>
          <Link
            href="/admin"
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 transition"
          >
            <div className="text-2xl mb-2">⚙️</div>
            <div className="font-semibold">Ejecutar Scraping</div>
            <div className="text-sm text-blue-100 mt-1">
              Iniciar nueva recolección de datos
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}

// KPI Card Component
interface KPICardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: string;
  link?: string;
}

function KPICard({ title, value, subtitle, icon, link }: KPICardProps) {
  const content = (
    <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        <div className="text-3xl">{icon}</div>
      </div>
    </div>
  );

  if (link) {
    return <Link href={link}>{content}</Link>;
  }

  return content;
}
