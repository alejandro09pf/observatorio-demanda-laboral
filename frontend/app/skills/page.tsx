'use client';

import { useEffect, useState } from 'react';
import {
  getTopSkills,
  getStats,
  TopSkillsResponse,
  StatsResponse,
} from '@/lib/api';
import Link from 'next/link';

export default function SkillsPage() {
  const [data, setData] = useState<TopSkillsResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [country, setCountry] = useState<string>('all');
  const [skillType, setSkillType] = useState<string>('all');
  const [extractionMethod, setExtractionMethod] = useState<string>('all');
  const [mappingStatus, setMappingStatus] = useState<string>('all');
  const [viewMode, setViewMode] = useState<string>('top50'); // 'top20', 'top50', 'top100', 'all'
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(0);

  // Fetch stats for filter options
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const statsData = await getStats();
        setStats(statsData);
      } catch (err) {
        console.error('Error fetching stats:', err);
      }
    };
    fetchStats();
  }, []);

  // Reset to page 1 when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  useEffect(() => {
    const fetchSkills = async () => {
      setLoading(true);
      try {
        let result;

        // If there's a search term, use search endpoint with pagination
        if (searchTerm && searchTerm.length >= 2) {
          const params = new URLSearchParams({
            query: searchTerm,
            page: currentPage.toString(),
            page_size: '50',
          });

          if (country !== 'all') params.append('country', country);
          if (skillType !== 'all') params.append('skill_type', skillType);
          if (extractionMethod !== 'all') params.append('extraction_method', extractionMethod);
          if (mappingStatus !== 'all') params.append('mapping_status', mappingStatus);

          const response = await fetch(`http://localhost:8000/api/skills/search?${params}`);
          if (!response.ok) throw new Error('Failed to search skills');
          result = await response.json();
          setTotalPages(result.total_pages || 0);
        } else if (viewMode === 'all') {
          // View all mode with pagination
          const params = new URLSearchParams({
            query: '', // Empty query to match all
            page: currentPage.toString(),
            page_size: '50',
          });

          if (country !== 'all') params.append('country', country);
          if (skillType !== 'all') params.append('skill_type', skillType);
          if (extractionMethod !== 'all') params.append('extraction_method', extractionMethod);
          if (mappingStatus !== 'all') params.append('mapping_status', mappingStatus);

          const response = await fetch(`http://localhost:8000/api/skills/search?${params}`);
          if (!response.ok) throw new Error('Failed to fetch skills');
          result = await response.json();
          setTotalPages(result.total_pages || 0);
        } else {
          // Top X mode (no pagination)
          const limit = parseInt(viewMode.replace('top', ''));
          result = await getTopSkills({
            country: country !== 'all' ? country : undefined,
            skill_type: skillType !== 'all' ? (skillType as 'hard' | 'soft') : undefined,
            extraction_method: extractionMethod !== 'all' ? extractionMethod : undefined,
            mapping_status: mappingStatus !== 'all' ? mappingStatus : undefined,
            limit,
          });
          setTotalPages(0);
          setCurrentPage(1);
        }

        setData(result);
        setError(null);
      } catch (err) {
        setError('Error al cargar habilidades');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSkills();
  }, [country, skillType, extractionMethod, mappingStatus, viewMode, searchTerm, currentPage]);

  const hasActiveFilters = country !== 'all' || skillType !== 'all' ||
                          extractionMethod !== 'all' || mappingStatus !== 'all' || searchTerm !== '';

  const clearFilters = () => {
    setCountry('all');
    setSkillType('all');
    setExtractionMethod('all');
    setMappingStatus('all');
    setViewMode('top50');
    setSearchTerm('');
    setCurrentPage(1);
  };

  return (
    <div className="space-y-4">
      {/* Header with Filters */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Habilidades</h1>
          <p className="text-gray-600 mt-1">
            Análisis de habilidades demandadas en el mercado laboral
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
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todos</option>
                {stats?.countries?.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="method-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Método
              </label>
              <select
                id="method-filter"
                value={extractionMethod}
                onChange={(e) => setExtractionMethod(e.target.value)}
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
              <label htmlFor="type-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Tipo
              </label>
              <select
                id="type-filter"
                value={skillType}
                onChange={(e) => setSkillType(e.target.value)}
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
                value={mappingStatus}
                onChange={(e) => setMappingStatus(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todas</option>
                <option value="esco_mapped">ESCO</option>
                <option value="unmapped">Emergentes</option>
              </select>
            </div>

            <div>
              <label htmlFor="view-mode-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Mostrar
              </label>
              <select
                id="view-mode-filter"
                value={viewMode}
                onChange={(e) => { setViewMode(e.target.value); setCurrentPage(1); }}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                disabled={searchTerm.length >= 2}
              >
                <option value="top20">Top 20</option>
                <option value="top50">Top 50</option>
                <option value="top100">Top 100</option>
                <option value="all">Todos</option>
              </select>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative mb-3">
            <input
              type="text"
              placeholder="Buscar por nombre..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-1.5 pl-8 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <svg
              className="absolute left-2.5 top-2 h-4 w-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2 top-1.5 text-gray-400 hover:text-gray-600"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
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

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-4 text-gray-600">Cargando habilidades...</p>
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

      {/* Skills List */}
      {data && !loading && !error && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-gray-900">
              {searchTerm ? 'Resultados de Búsqueda' : viewMode === 'all' ? 'Todas las Habilidades' : `Top ${viewMode.replace('top', '')} Habilidades`}
              {hasActiveFilters && <span className="text-blue-600 text-sm ml-2">(Filtrado)</span>}
            </h2>
            <p className="text-sm text-gray-600">
              {(searchTerm || viewMode === 'all') ? `${data.total_unique.toLocaleString()} encontradas` : `${data.skills.length} de ${data.total_unique.toLocaleString()} habilidades únicas`}
            </p>
          </div>

          {data.skills.length === 0 && searchTerm && (
            <div className="text-center py-8 text-gray-500">
              No se encontraron habilidades que coincidan con "{searchTerm}"
            </div>
          )}

          <div className="space-y-2">
            {data.skills.map((skill, idx) => (
              <Link
                key={idx}
                href={`/skills/${encodeURIComponent(skill.skill_text)}`}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-blue-50 hover:border-blue-300 border border-transparent transition cursor-pointer"
              >
                <span className="text-xs font-bold text-gray-400 w-5">{(searchTerm || viewMode === 'all') ? (currentPage - 1) * 50 + idx + 1 : idx + 1}</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900 hover:text-blue-600">{skill.skill_text}</span>
                      {skill.type && (
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded ${
                            skill.type === 'hard'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-purple-100 text-purple-700'
                          }`}
                        >
                          {skill.type}
                        </span>
                      )}
                      {skill.esco_uri && skill.esco_uri.startsWith('http') && (
                        <a
                          href={skill.esco_uri}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800"
                          title="Ver en ESCO"
                          onClick={(e) => e.stopPropagation()}
                        >
                          ESCO →
                        </a>
                      )}
                      {skill.esco_uri && !skill.esco_uri.startsWith('http') && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700">
                          ESCO
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-600">{skill.count.toLocaleString()} ({skill.percentage.toFixed(1)}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full transition-all"
                      style={{ width: `${Math.min(100, skill.percentage)}%` }}
                    ></div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {(searchTerm || viewMode === 'all') && totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6 pt-6 border-t border-gray-200">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium text-gray-700"
              >
                ← Anterior
              </button>
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-1 rounded text-sm font-medium ${
                        currentPage === pageNum
                          ? 'bg-blue-600 text-white'
                          : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium text-gray-700"
              >
                Siguiente →
              </button>
              <span className="text-sm text-gray-600 ml-2">
                Página {currentPage} de {totalPages}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
