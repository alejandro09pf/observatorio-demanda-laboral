'use client';

import { useEffect, useState } from 'react';
import { getJobs, JobListResponse, Job, getStats, StatsResponse } from '@/lib/api';
import Link from 'next/link';

export default function JobsPage() {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [country, setCountry] = useState<string>('all');
  const [portal, setPortal] = useState<string>('all');
  const [jobStatus, setJobStatus] = useState<string>('all');
  const [search, setSearch] = useState<string>('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

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

  useEffect(() => {
    const fetchJobs = async () => {
      setLoading(true);
      try {
        const result = await getJobs({
          country: country !== 'all' ? country : undefined,
          portal: portal !== 'all' ? portal : undefined,
          job_status: jobStatus !== 'all' ? jobStatus : undefined,
          search: search || undefined,
          limit: pageSize,
          offset: (page - 1) * pageSize,
        });
        setData(result);
        setError(null);
      } catch (err) {
        setError('Error al cargar empleos');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();
  }, [country, portal, jobStatus, search, page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1); // Reset to first page when searching
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  const hasActiveFilters = country !== 'all' || portal !== 'all' || jobStatus !== 'all' || search !== '';

  const clearFilters = () => {
    setCountry('all');
    setPortal('all');
    setJobStatus('all');
    setSearch('');
    setPage(1);
  };

  return (
    <div className="space-y-4">
      {/* Header with Filters */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Empleos</h1>
          <p className="text-gray-600 mt-1">
            Explora las ofertas laborales recolectadas
          </p>
        </div>

        {/* Compact Filters */}
        <div className="bg-white rounded-lg shadow p-4 min-w-[600px]">
          <div className="grid grid-cols-3 gap-2.5 mb-3">
            <div>
              <label htmlFor="country-filter" className="block text-xs font-medium text-gray-600 mb-1">
                País
              </label>
              <select
                id="country-filter"
                value={country}
                onChange={(e) => {
                  setCountry(e.target.value);
                  setPage(1);
                }}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todos</option>
                {stats?.countries?.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="portal-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Portal
              </label>
              <select
                id="portal-filter"
                value={portal}
                onChange={(e) => {
                  setPortal(e.target.value);
                  setPage(1);
                }}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todos</option>
                {stats?.portals?.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="job-status-filter" className="block text-xs font-medium text-gray-600 mb-1">
                Estado
              </label>
              <select
                id="job-status-filter"
                value={jobStatus}
                onChange={(e) => {
                  setJobStatus(e.target.value);
                  setPage(1);
                }}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Todos</option>
                <option value="raw">Raw</option>
                <option value="cleaned">Cleaned</option>
                <option value="golden">Golden</option>
              </select>
            </div>
          </div>

          <div className="mb-3">
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Buscar por título o descripción..."
              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
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

      {/* Results Count */}
      {data && !loading && (
        <div className="text-sm text-gray-600">
          Mostrando {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, data.total)} de {data.total.toLocaleString()} empleos
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-4 text-gray-600">Cargando empleos...</p>
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

      {/* Jobs Table */}
      {data && !loading && !error && (
        <>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Título
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Empresa
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      País
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Portal
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fecha
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {data.jobs.map((job) => (
                    <tr key={job.job_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900 line-clamp-2">
                          {job.title}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-500">{job.company || 'N/A'}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">{job.country}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
                          {job.portal}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {new Date(job.posted_date).toLocaleDateString('es-ES')}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <Link
                          href={`/jobs/${job.job_id}`}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Ver Detalle →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between bg-white px-6 py-4 rounded-lg shadow">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anterior
              </button>

              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-700">
                  Página {page} de {totalPages}
                </span>
              </div>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Siguiente
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
