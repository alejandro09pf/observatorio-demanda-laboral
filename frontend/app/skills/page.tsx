'use client';

import { useEffect, useState } from 'react';
import {
  getTopSkills,
  getSkillsByType,
  searchSkills,
  TopSkillsResponse,
  SkillsByTypeResponse,
} from '@/lib/api';

type TabType = 'top' | 'by-type' | 'search';

export default function SkillsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('top');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Habilidades</h1>
        <p className="text-gray-600 mt-2">
          Análisis de habilidades demandadas en el mercado laboral
        </p>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('top')}
              className={`px-6 py-3 border-b-2 font-medium text-sm transition ${
                activeTab === 'top'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Principales
            </button>
            <button
              onClick={() => setActiveTab('by-type')}
              className={`px-6 py-3 border-b-2 font-medium text-sm transition ${
                activeTab === 'by-type'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Por Tipo
            </button>
            <button
              onClick={() => setActiveTab('search')}
              className={`px-6 py-3 border-b-2 font-medium text-sm transition ${
                activeTab === 'search'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Búsqueda
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'top' && <TopSkillsTab />}
          {activeTab === 'by-type' && <SkillsByTypeTab />}
          {activeTab === 'search' && <SearchSkillsTab />}
        </div>
      </div>
    </div>
  );
}

// ============================================
// TOP SKILLS TAB
// ============================================

function TopSkillsTab() {
  const [data, setData] = useState<TopSkillsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [country, setCountry] = useState<string>('');
  const [skillType, setSkillType] = useState<string>('');
  const [extractionMethod, setExtractionMethod] = useState<string>('');
  const [mappingStatus, setMappingStatus] = useState<string>('');
  const [limit, setLimit] = useState<number>(20);

  useEffect(() => {
    const fetchTopSkills = async () => {
      setLoading(true);
      try {
        const result = await getTopSkills({
          country: country || undefined,
          skill_type: skillType as 'hard' | 'soft' | undefined,
          extraction_method: extractionMethod || undefined,
          mapping_status: mappingStatus || undefined,
          limit,
        });
        setData(result);
        setError(null);
      } catch (err) {
        setError('Error al cargar habilidades');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchTopSkills();
  }, [country, skillType, extractionMethod, mappingStatus, limit]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando habilidades...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h2 className="text-red-800 text-lg font-semibold mb-2">Error</h2>
        <p className="text-red-600">{error || 'Error al cargar habilidades'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="space-y-4 pb-6 border-b border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="country-filter" className="block text-sm font-medium text-gray-700 mb-2">
              País
            </label>
            <select
              id="country-filter"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="AR">Argentina</option>
              <option value="CO">Colombia</option>
              <option value="MX">México</option>
            </select>
          </div>

          <div>
            <label htmlFor="type-filter" className="block text-sm font-medium text-gray-700 mb-2">
              Tipo
            </label>
            <select
              id="type-filter"
              value={skillType}
              onChange={(e) => setSkillType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="hard">Técnicas</option>
              <option value="soft">Blandas</option>
            </select>
          </div>

          <div>
            <label htmlFor="limit-filter" className="block text-sm font-medium text-gray-700 mb-2">
              Límite
            </label>
            <select
              id="limit-filter"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="10">Top 10</option>
              <option value="20">Top 20</option>
              <option value="50">Top 50</option>
              <option value="100">Top 100</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="extraction-method-filter" className="block text-sm font-medium text-gray-700 mb-2">
              Método de Extracción
            </label>
            <select
              id="extraction-method-filter"
              value={extractionMethod}
              onChange={(e) => setExtractionMethod(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="ner">Solo NER</option>
              <option value="regex">Solo Regex</option>
              <option value="pipeline_a">Pipeline A (NER + Regex)</option>
              <option value="pipeline_b">Pipeline B (LLM)</option>
            </select>
          </div>

          <div>
            <label htmlFor="mapping-status-filter" className="block text-sm font-medium text-gray-700 mb-2">
              Estado de Mapeo
            </label>
            <select
              id="mapping-status-filter"
              value={mappingStatus}
              onChange={(e) => setMappingStatus(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="esco_mapped">Mapeado a ESCO</option>
              <option value="unmapped">Sin mapear</option>
            </select>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Mostrando {data.skills.length} de {data.total_unique.toLocaleString()} habilidades únicas
        </p>
      </div>

      {/* Skills List */}
      <div className="space-y-2">
        {data.skills.map((skill, idx) => (
          <div
            key={idx}
            className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
          >
            <div className="flex items-center gap-4 flex-1">
              <span className="text-lg font-bold text-gray-400 w-8">{idx + 1}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold text-gray-900">{skill.skill_text}</h3>
                  {skill.type && (
                    <span
                      className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        skill.type === 'hard'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {skill.type === 'hard' ? 'Técnica' : 'Blanda'}
                    </span>
                  )}
                  {skill.esco_uri && (
                    <a
                      href={skill.esco_uri}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:text-blue-800"
                      title="Ver en ESCO"
                    >
                      ESCO →
                    </a>
                  )}
                </div>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">{skill.count.toLocaleString()}</p>
              <p className="text-sm text-gray-500">{skill.percentage.toFixed(2)}%</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// SKILLS BY TYPE TAB
// ============================================

function SkillsByTypeTab() {
  const [data, setData] = useState<SkillsByTypeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [country, setCountry] = useState<string>('');

  useEffect(() => {
    const fetchSkillsByType = async () => {
      setLoading(true);
      try {
        const result = await getSkillsByType({
          country: country || undefined,
        });
        setData(result);
        setError(null);
      } catch (err) {
        setError('Error al cargar distribución');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSkillsByType();
  }, [country]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando distribución...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h2 className="text-red-800 text-lg font-semibold mb-2">Error</h2>
        <p className="text-red-600">{error || 'Error al cargar distribución'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Country Filter */}
      <div className="max-w-xs">
        <label htmlFor="country-type-filter" className="block text-sm font-medium text-gray-700 mb-2">
          País
        </label>
        <select
          id="country-type-filter"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos</option>
          <option value="AR">Argentina</option>
          <option value="CO">Colombia</option>
          <option value="MX">México</option>
        </select>
      </div>

      {/* Total */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
        <p className="text-sm text-blue-600 font-medium">Total de Extracciones</p>
        <p className="text-4xl font-bold text-blue-900 mt-2">{data.total.toLocaleString()}</p>
      </div>

      {/* Type Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {data.by_type.map((typeData) => (
          <div
            key={typeData.type}
            className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:border-blue-500 transition"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-900 capitalize">
                {typeData.type === 'hard' ? 'Habilidades Técnicas' :
                 typeData.type === 'soft' ? 'Habilidades Blandas' :
                 typeData.type}
              </h3>
              <span
                className={`px-3 py-1 text-sm font-semibold rounded-full ${
                  typeData.type === 'hard'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-green-100 text-green-800'
                }`}
              >
                {typeData.percentage.toFixed(2)}%
              </span>
            </div>
            <p className="text-4xl font-bold text-gray-900">{typeData.count.toLocaleString()}</p>
            <p className="text-sm text-gray-500 mt-2">extracciones</p>

            {/* Progress Bar */}
            <div className="mt-4 bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full ${
                  typeData.type === 'hard' ? 'bg-blue-600' : 'bg-green-600'
                }`}
                style={{ width: `${typeData.percentage}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// SEARCH SKILLS TAB
// ============================================

function SearchSkillsTab() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Array<{ skill_text: string; count: number }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.length < 2) {
      setError('La búsqueda debe tener al menos 2 caracteres');
      return;
    }

    setLoading(true);
    setHasSearched(true);
    try {
      const result = await searchSkills(query);
      setResults(result.results);
      setError(null);
    } catch (err) {
      setError('Error al buscar habilidades');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar habilidad (ej: Python, Excel, Comunicación...)"
          className="flex-1 px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition font-medium"
        >
          Buscar
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-4 text-gray-600">Buscando...</p>
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && hasSearched && (
        <div>
          {results.length > 0 ? (
            <>
              <p className="text-sm text-gray-600 mb-4">
                {results.length} resultado{results.length !== 1 ? 's' : ''} para "{query}"
              </p>
              <div className="space-y-2">
                {results.map((skill, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                  >
                    <h3 className="text-lg font-semibold text-gray-900">{skill.skill_text}</h3>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-gray-900">{skill.count.toLocaleString()}</p>
                      <p className="text-sm text-gray-500">menciones</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">No se encontraron habilidades para "{query}"</p>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!loading && !hasSearched && (
        <div className="text-center py-12">
          <p className="text-gray-500">Ingresa un término para buscar habilidades</p>
        </div>
      )}
    </div>
  );
}
