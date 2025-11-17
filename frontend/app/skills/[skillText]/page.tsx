'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getSkillDetail, SkillDetailResponse } from '@/lib/api';
import Link from 'next/link';

export default function SkillDetailPage() {
  const params = useParams();
  const router = useRouter();
  const skillText = decodeURIComponent(params.skillText as string);

  const [data, setData] = useState<SkillDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSkillDetail = async () => {
      if (!skillText) return;

      setLoading(true);
      try {
        const result = await getSkillDetail(skillText, {
          limit_jobs: 20,
          limit_cooccurring: 15
        });
        setData(result);
        setError(null);
      } catch (err) {
        setError('Error al cargar detalles de la habilidad');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSkillDetail();
  }, [skillText]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando habilidad...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <Link href="/skills" className="text-blue-600 hover:text-blue-800">
          ← Volver a Habilidades
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 text-lg font-semibold mb-2">Error</h2>
          <p className="text-red-600">{error || 'Error al cargar la habilidad'}</p>
        </div>
      </div>
    );
  }

  const { skill, cooccurring_skills, jobs, total_jobs, country_distribution } = data;

  return (
    <div className="space-y-4">
      {/* Back Button */}
      <Link href="/skills" className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm">
        ← Volver a Habilidades
      </Link>

      {/* Skill Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{skill.skill_text}</h1>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full capitalize ${
                skill.skill_type === 'hard' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
              }`}>
                {skill.skill_type === 'hard' ? 'Habilidad Técnica' : 'Habilidad Blanda'}
              </span>
              {skill.esco_uri && skill.esco_uri.startsWith('http') && (
                <a
                  href={skill.esco_uri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800 hover:bg-green-200"
                >
                  ESCO →
                </a>
              )}
              {skill.esco_uri && !skill.esco_uri.startsWith('http') && (
                <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                  ESCO
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
          <div className="text-center">
            <p className="text-sm text-gray-500">Apariciones Totales</p>
            <p className="text-2xl font-bold text-gray-900">{skill.total_count.toLocaleString()}</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-500">Empleos Únicos</p>
            <p className="text-2xl font-bold text-gray-900">{total_jobs.toLocaleString()}</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-500">Países</p>
            <p className="text-2xl font-bold text-gray-900">{country_distribution.length}</p>
          </div>
        </div>
      </div>

      {/* Country Distribution */}
      {country_distribution.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Distribución por País</h2>
          <div className="space-y-2">
            {country_distribution.map((item) => {
              const percentage = (item.count / total_jobs) * 100;
              return (
                <div key={item.country}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900">{item.country}</span>
                    <span className="text-sm text-gray-600">
                      {item.count.toLocaleString()} empleos ({percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Co-occurring Skills */}
      {cooccurring_skills.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Habilidades que Aparecen Frecuentemente Juntas ({cooccurring_skills.length})
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Otras habilidades que suelen aparecer en los mismos empleos
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {cooccurring_skills.map((coSkill, idx) => (
              <Link
                key={idx}
                href={`/skills/${encodeURIComponent(coSkill.skill_text)}`}
                className={`flex items-center justify-between p-3 rounded hover:shadow-md transition border ${
                  coSkill.skill_type === 'hard'
                    ? 'bg-blue-50 border-blue-200 hover:bg-blue-100'
                    : 'bg-purple-50 border-purple-200 hover:bg-purple-100'
                }`}
              >
                <span className="text-sm font-medium text-gray-900">{coSkill.skill_text}</span>
                <span className="text-xs text-gray-600 bg-white px-2 py-1 rounded">
                  {coSkill.cooccurrence_count}x
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Jobs List */}
      {jobs.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Empleos que Requieren esta Habilidad ({Math.min(jobs.length, total_jobs)} de {total_jobs})
          </h2>
          <div className="space-y-3">
            {jobs.map((job) => (
              <Link
                key={job.job_id}
                href={`/jobs/${job.job_id}`}
                className="block p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:shadow-md transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 hover:text-blue-600">
                      {job.title}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {job.company || 'Empresa confidencial'} • {job.location || job.country}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
                      {job.portal}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(job.posted_date).toLocaleDateString('es-ES')}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {total_jobs > jobs.length && (
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Mostrando {jobs.length} de {total_jobs} empleos totales
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
