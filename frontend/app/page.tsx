'use client';

import { useEffect, useState } from 'react';
import { getStats, StatsResponse } from '@/lib/api';
import Link from 'next/link';

export default function Dashboard() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  if (!stats) {
    return null;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Panel Principal</h1>
        <p className="text-gray-600 mt-2">
          Resumen de datos del mercado laboral y análisis
        </p>
      </div>

      {/* Data Funnel Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Proceso de Datos</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-4xl font-bold text-blue-600">
              {stats.total_raw_jobs?.toLocaleString() || '0'}
            </div>
            <div className="text-sm text-gray-600 mt-2">Empleos Recolectados</div>
            <div className="text-xs text-gray-500">Datos crudos del scraping</div>
          </div>
          <div className="text-center flex flex-col justify-center">
            <div className="text-2xl text-gray-400 mb-2">→</div>
            <div className="text-4xl font-bold text-green-600">
              {stats.total_cleaned_jobs?.toLocaleString() || '0'}
            </div>
            <div className="text-sm text-gray-600 mt-2">Empleos Limpiados</div>
            <div className="text-xs text-gray-500">
              {stats.total_raw_jobs ? ((stats.total_cleaned_jobs / stats.total_raw_jobs) * 100).toFixed(1) : '0'}% retenido
            </div>
          </div>
          <div className="text-center flex flex-col justify-center">
            <div className="text-2xl text-gray-400 mb-2">→</div>
            <div className="text-4xl font-bold text-purple-600">
              {stats.total_jobs_with_skills?.toLocaleString() || '0'}
            </div>
            <div className="text-sm text-gray-600 mt-2">Con Habilidades</div>
            <div className="text-xs text-gray-500">
              {stats.total_cleaned_jobs ? ((stats.total_jobs_with_skills / stats.total_cleaned_jobs) * 100).toFixed(1) : '0'}% procesado
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Habilidades Extraídas"
          value={stats.total_skills?.toLocaleString() || '0'}
          subtitle={`${stats.total_unique_skills?.toLocaleString() || '0'} únicas`}
          icon="🎯"
          link="/skills"
        />
        <KPICard
          title="Pipeline A (NER + Regex)"
          value={stats.extraction_methods?.pipeline_a1?.toLocaleString() || '0'}
          subtitle="Extracción basada en reglas"
          icon="📝"
        />
        <KPICard
          title="Pipeline B (Gemma LLM)"
          value={stats.extraction_methods?.pipeline_b_gemma?.toLocaleString() || '0'}
          subtitle={`En ${stats.extraction_methods?.pipeline_b_jobs?.toLocaleString() || '0'} empleos`}
          icon="🤖"
        />
        <KPICard
          title="Países Analizados"
          value={stats.n_countries?.toString() || '0'}
          subtitle={stats.countries?.join(', ') || 'N/A'}
          icon="🌎"
        />
      </div>

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
                {stats.date_range?.start ? new Date(stats.date_range.start).toLocaleDateString('es-ES') : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Fecha Final:</span>
              <span className="font-semibold text-gray-900">
                {stats.date_range?.end ? new Date(stats.date_range.end).toLocaleDateString('es-ES') : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between items-center pt-3 border-t border-gray-200">
              <span className="text-gray-600">Último Scraping:</span>
              <span className="font-semibold text-gray-900">
                {stats.last_scraping ? new Date(stats.last_scraping).toLocaleString('es-ES') : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Distribución por Países
          </h3>
          <div className="space-y-3">
            {stats.countries?.map((country) => (
              <div key={country} className="flex items-center justify-between">
                <span className="text-gray-700 font-medium">{country}</span>
                <Link
                  href={`/jobs?country=${country}`}
                  className="text-blue-600 hover:text-blue-800 text-sm"
                >
                  Ver Empleos →
                </Link>
              </div>
            )) || <p className="text-gray-500">Sin datos</p>}
          </div>
        </div>
      </div>

      {/* Portals List */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Portales de Empleo Soportados
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          {stats.portals?.map((portal) => (
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
