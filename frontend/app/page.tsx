'use client';

import { useEffect, useState } from 'react';
import {
  getStats,
  getFilteredStats,
  getStatsByCountry,
  getTopSkills,
  StatsResponse,
  FilteredStatsResponse,
  StatsByCountryResponse,
  TopSkillsResponse
} from '@/lib/api';
import Link from 'next/link';

export default function Dashboard() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [filteredStats, setFilteredStats] = useState<FilteredStatsResponse | null>(null);
  const [countryStats, setCountryStats] = useState<StatsByCountryResponse | null>(null);
  const [topSkills, setTopSkills] = useState<TopSkillsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [countryFilter, setCountryFilter] = useState<string>('all');
  const [extractionMethodFilter, setExtractionMethodFilter] = useState<string>('all');
  const [jobStatusFilter, setJobStatusFilter] = useState<string>('all');
  const [mappingStatusFilter, setMappingStatusFilter] = useState<string>('all');
  const [skillTypeFilter, setSkillTypeFilter] = useState<string>('all');

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

  // Fetch filtered stats, country stats, and top skills when filters change
  useEffect(() => {
    const fetchFilteredData = async () => {
      try {
        const params: any = {};
        if (countryFilter !== 'all') params.country = countryFilter;
        if (extractionMethodFilter !== 'all') params.extraction_method = extractionMethodFilter;
        if (jobStatusFilter !== 'all') params.job_status = jobStatusFilter;
        if (mappingStatusFilter !== 'all') params.mapping_status = mappingStatusFilter;
        if (skillTypeFilter !== 'all') params.skill_type = skillTypeFilter;

        // Fetch all data in parallel
        const hasActiveFilters = countryFilter !== 'all' || extractionMethodFilter !== 'all' ||
                                  jobStatusFilter !== 'all' || mappingStatusFilter !== 'all' || skillTypeFilter !== 'all';

        const [filtered, countries, skills] = await Promise.all([
          hasActiveFilters ? getFilteredStats(params) : Promise.resolve(null),
          getStatsByCountry({
            extraction_method: extractionMethodFilter !== 'all' ? extractionMethodFilter : undefined,
            job_status: jobStatusFilter !== 'all' ? jobStatusFilter : undefined,
            mapping_status: mappingStatusFilter !== 'all' ? mappingStatusFilter : undefined,
            skill_type: skillTypeFilter !== 'all' ? skillTypeFilter : undefined,
          }),
          getTopSkills({
            country: countryFilter !== 'all' ? countryFilter : undefined,
            extraction_method: extractionMethodFilter !== 'all' ? extractionMethodFilter : undefined,
            mapping_status: mappingStatusFilter !== 'all' ? mappingStatusFilter : undefined,
            skill_type: skillTypeFilter !== 'all' ? (skillTypeFilter as 'hard' | 'soft') : undefined,
            limit: 15,
          }),
        ]);

        setFilteredStats(filtered);
        setCountryStats(countries);
        setTopSkills(skills);
      } catch (err) {
        console.error('Error fetching filtered data:', err);
      }
    };

    fetchFilteredData();
  }, [countryFilter, extractionMethodFilter, jobStatusFilter, mappingStatusFilter, skillTypeFilter]);

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
  const displayPipelineATotal = filteredStats?.extraction_methods.pipeline_a ?? stats.extraction_methods?.pipeline_a1;
  const displayNer = filteredStats?.extraction_methods.ner ?? stats.extraction_methods?.ner;
  const displayRegex = filteredStats?.extraction_methods.regex ?? stats.extraction_methods?.regex;
  const displayPipelineBGemma = filteredStats?.extraction_methods.pipeline_b_gemma ?? stats.extraction_methods?.pipeline_b_gemma;
  const displayPipelineBJobs = filteredStats?.extraction_methods.pipeline_b_jobs ?? stats.extraction_methods?.pipeline_b_jobs;
  const displayCountries = filteredStats?.countries ?? stats.countries;
  const displayPortals = filteredStats?.portals ?? stats.portals;

  const hasActiveFilters = countryFilter !== 'all' || extractionMethodFilter !== 'all' ||
                           jobStatusFilter !== 'all' || mappingStatusFilter !== 'all' || skillTypeFilter !== 'all';

  const clearFilters = () => {
    setCountryFilter('all');
    setExtractionMethodFilter('all');
    setJobStatusFilter('all');
    setMappingStatusFilter('all');
    setSkillTypeFilter('all');
  };

  return (
    <div className="space-y-4">
      {/* Header with Filters */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Observatorio de Demanda Laboral</h1>
          <p className="text-gray-600 mt-1">
            Análisis del mercado laboral en América Latina
          </p>
        </div>

        {/* Compact Filters */}
        <div className="bg-white rounded-lg shadow p-4 min-w-[700px]">
          <div className="grid grid-cols-5 gap-2.5 mb-3">
            <div>
              <label htmlFor="country-filter" className="block text-xs font-medium text-gray-600 mb-1">
                País
              </label>
              <select
                id="country-filter"
                value={countryFilter}
                onChange={(e) => setCountryFilter(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todos</option>
                {stats.countries?.map((country) => (
                  <option key={country} value={country}>{country}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="method-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Método
              </label>
              <select
                id="method-filter"
                value={extractionMethodFilter}
                onChange={(e) => setExtractionMethodFilter(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todos</option>
                <option value="manual">Manual</option>
                <option value="pipeline_a">Pipeline A</option>
                <option value="ner">NER</option>
                <option value="regex">Regex</option>
                <option value="pipeline_b">Pipeline B</option>
              </select>
            </div>

            <div>
              <label htmlFor="job-status-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Estado
              </label>
              <select
                id="job-status-filter"
                value={jobStatusFilter}
                onChange={(e) => setJobStatusFilter(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todos</option>
                <option value="raw">Raw</option>
                <option value="cleaned">Cleaned</option>
                <option value="golden">Golden</option>
              </select>
            </div>

            <div>
              <label htmlFor="skill-type-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Tipo
              </label>
              <select
                id="skill-type-filter"
                value={skillTypeFilter}
                onChange={(e) => setSkillTypeFilter(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todas</option>
                <option value="hard">Hard</option>
                <option value="soft">Soft</option>
              </select>
            </div>

            <div>
              <label htmlFor="mapping-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Mapeo
              </label>
              <select
                id="mapping-filter"
                value={mappingStatusFilter}
                onChange={(e) => setMappingStatusFilter(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todas</option>
                <option value="esco_mapped">ESCO</option>
                <option value="unmapped">Emergentes</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end">
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                Limpiar filtros
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Coverage Stats */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-bold text-gray-900 mb-3">
          Cobertura de Datos {hasActiveFilters && <span className="text-blue-600 text-sm">(Filtrado)</span>}
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{displayJobsTotal?.toLocaleString() || '0'}</div>
            <div className="text-xs text-gray-600 mt-1">Empleos</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{displaySkillsUnique?.toLocaleString() || '0'}</div>
            <div className="text-xs text-gray-600 mt-1">Skills Únicas</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-purple-600">{displayCountries?.length || 0}</div>
            <div className="text-xs text-gray-600 mt-1">Países</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-orange-600">{displayPortals?.length || 0}</div>
            <div className="text-xs text-gray-600 mt-1">Portales</div>
          </div>
        </div>
      </div>

      {/* Top Skills */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-gray-900">
            Top 15 Habilidades {hasActiveFilters && <span className="text-blue-600 text-sm">(Filtrado)</span>}
          </h2>
          <Link href="/skills" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
            Ver todas las skills →
          </Link>
        </div>
        {topSkills && topSkills.skills.length > 0 ? (
          <div className="space-y-2">
            {topSkills.skills.map((skill, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <span className="text-xs font-bold text-gray-400 w-5">{idx + 1}</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">{skill.skill_text}</span>
                      {skill.type && (
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          skill.type === 'hard'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-purple-100 text-purple-700'
                        }`}>
                          {skill.type}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-600">{skill.count} ({skill.percentage.toFixed(1)}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full transition-all"
                      style={{ width: `${Math.min(100, skill.percentage)}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-500 text-center py-4 text-sm">
            {loading ? 'Cargando skills...' : 'No hay skills disponibles'}
          </div>
        )}
      </div>

      {/* Geographic Distribution */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-bold text-gray-900 mb-3">
          Distribución Geográfica {hasActiveFilters && <span className="text-blue-600 text-sm">(Filtrado)</span>}
        </h2>
        <div className="space-y-3">
          {displayCountries?.map((country) => {
            const countryData = countryStats?.countries[country];
            const countryJobs = countryData?.total_jobs || 0;
            const countrySkills = countryData?.unique_skills || 0;

            // Only show country if it has data OR if no country filter is active
            if (countryFilter !== 'all' && countryFilter !== country && countryJobs === 0) {
              return null;
            }

            return (
              <div key={country} className="border border-gray-200 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center flex-1">
                    <span className="text-xl mr-2">
                      {country === 'CO' ? '🇨🇴' : country === 'MX' ? '🇲🇽' : '🇦🇷'}
                    </span>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 text-sm">{country}</h3>
                      <p className="text-xs text-gray-600">
                        {countryJobs.toLocaleString()} empleos • {countrySkills.toLocaleString()} skills
                      </p>
                    </div>
                  </div>
                  <Link
                    href={`/jobs?country=${country}`}
                    className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Ver →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Method Distribution - Only show when no extraction method filter is active */}
      {extractionMethodFilter === 'all' && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-bold text-gray-900 mb-3">
            Distribución por Método {(countryFilter !== 'all' || jobStatusFilter !== 'all' || skillTypeFilter !== 'all' || mappingStatusFilter !== 'all') && <span className="text-blue-600 text-sm">(Filtrado)</span>}
          </h2>
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">Pipeline A (NER + Regex)</span>
                  <span className="text-sm text-gray-600">{displayPipelineATotal?.toLocaleString() || '0'}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${Math.min(100, (displayPipelineATotal / (displaySkillsTotal || stats.total_skills)) * 100)}%` }}
                  ></div>
                </div>
                <div className="flex justify-between mt-1 text-xs text-gray-500">
                  <span>NER: {displayNer?.toLocaleString()}</span>
                  <span>Regex: {displayRegex?.toLocaleString()}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">Pipeline B (Gemma LLM)</span>
                  <span className="text-sm text-gray-600">{displayPipelineBGemma?.toLocaleString() || '0'}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full"
                    style={{ width: `${Math.min(100, (displayPipelineBGemma / (displaySkillsTotal || stats.total_skills)) * 100)}%` }}
                  ></div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  En {displayPipelineBJobs?.toLocaleString()} empleos
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Clustering */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-bold text-gray-900 mb-2">Perfiles Profesionales</h2>
        <p className="text-sm text-gray-600 mb-3">
          8 configuraciones de clustering disponibles
        </p>
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="bg-gray-50 p-2 rounded">
            <div className="text-xs font-medium text-gray-700">4 datasets</div>
            <div className="text-xs text-gray-500">Golden, A, B, 30k</div>
          </div>
          <div className="bg-gray-50 p-2 rounded">
            <div className="text-xs font-medium text-gray-700">Pre/Post ESCO</div>
            <div className="text-xs text-gray-500">Antes y después</div>
          </div>
        </div>
        <Link
          href="/clusters"
          className="block w-full text-center px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Explorar perfiles →
        </Link>
      </div>

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg shadow-lg p-4 text-white">
        <h3 className="text-base font-semibold mb-3">Accesos Rápidos</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Link
            href="/skills"
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-3 transition text-center"
          >
            <div className="text-2xl mb-1">🎯</div>
            <div className="font-semibold text-sm">Skills</div>
            <div className="text-xs text-blue-100">Análisis</div>
          </Link>
          <Link
            href="/jobs"
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-3 transition text-center"
          >
            <div className="text-2xl mb-1">💼</div>
            <div className="font-semibold text-sm">Empleos</div>
            <div className="text-xs text-blue-100">Explorar</div>
          </Link>
          <Link
            href="/clusters"
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-3 transition text-center"
          >
            <div className="text-2xl mb-1">🗺️</div>
            <div className="font-semibold text-sm">Clusters</div>
            <div className="text-xs text-blue-100">Perfiles</div>
          </Link>
          <Link
            href="/admin"
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-3 transition text-center"
          >
            <div className="text-2xl mb-1">⚙️</div>
            <div className="font-semibold text-sm">Admin</div>
            <div className="text-xs text-blue-100">Gestión</div>
          </Link>
        </div>
      </div>
    </div>
  );
}
