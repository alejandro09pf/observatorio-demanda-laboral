'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getJobById, JobDetail } from '@/lib/api';
import Link from 'next/link';

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJob = async () => {
      if (!jobId) return;

      setLoading(true);
      try {
        const data = await getJobById(jobId);
        setJob(data);
        setError(null);
      } catch (err) {
        setError('Error al cargar el empleo');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchJob();
  }, [jobId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando empleo...</p>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="space-y-6">
        <Link href="/jobs" className="text-blue-600 hover:text-blue-800">
          ← Volver a Empleos
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-red-800 text-lg font-semibold mb-2">Error</h2>
          <p className="text-red-600">{error || 'Error al cargar el empleo'}</p>
        </div>
      </div>
    );
  }

  // Separate skills by type and extraction method
  const hardSkills = job.extracted_skills?.filter(s => s.skill_type === 'hard') || [];
  const softSkills = job.extracted_skills?.filter(s => s.skill_type === 'soft') || [];

  const nerSkills = job.extracted_skills?.filter(s => s.extraction_method === 'ner') || [];
  const regexSkills = job.extracted_skills?.filter(s => s.extraction_method === 'regex') || [];
  const llmSkills = job.extracted_skills?.filter(s => s.extraction_method?.includes('llm') || s.extraction_method?.includes('gemma')) || [];

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link href="/jobs" className="inline-flex items-center text-blue-600 hover:text-blue-800">
        ← Volver a Empleos
      </Link>

      {/* Job Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{job.title}</h1>
            <p className="text-xl text-gray-600">{job.company || 'Empresa confidencial'}</p>
          </div>
          <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
            {job.portal}
          </span>
        </div>

        {/* Job Meta Information */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-gray-200">
          <div>
            <p className="text-sm text-gray-500">Ubicación</p>
            <p className="text-sm font-medium text-gray-900">{job.location || 'No especificado'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">País</p>
            <p className="text-sm font-medium text-gray-900">{job.country}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Fecha de Publicación</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(job.posted_date).toLocaleDateString('es-ES')}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Recolectado</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(job.scraped_at).toLocaleDateString('es-ES')}
            </p>
          </div>
        </div>

        {/* Additional Meta */}
        {(job.salary_raw || job.contract_type || job.remote_type) && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 mt-4 border-t border-gray-200">
            {job.salary_raw && (
              <div>
                <p className="text-sm text-gray-500">Salario</p>
                <p className="text-sm font-medium text-gray-900">{job.salary_raw}</p>
              </div>
            )}
            {job.contract_type && (
              <div>
                <p className="text-sm text-gray-500">Tipo de Contrato</p>
                <p className="text-sm font-medium text-gray-900">{job.contract_type}</p>
              </div>
            )}
            {job.remote_type && (
              <div>
                <p className="text-sm text-gray-500">Modalidad</p>
                <p className="text-sm font-medium text-gray-900">{job.remote_type}</p>
              </div>
            )}
          </div>
        )}

        {/* External Link */}
        {job.url && (
          <div className="pt-4 mt-4 border-t border-gray-200">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-blue-600 hover:text-blue-800"
            >
              Ver oferta original →
            </a>
          </div>
        )}
      </div>

      {/* Job Description */}
      {job.description && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Descripción</h2>
          <div className="prose prose-sm max-w-none">
            <p className="text-gray-700 whitespace-pre-wrap">{job.description}</p>
          </div>
        </div>
      )}

      {/* Requirements */}
      {job.requirements && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Requisitos</h2>
          <div className="prose prose-sm max-w-none">
            <p className="text-gray-700 whitespace-pre-wrap">{job.requirements}</p>
          </div>
        </div>
      )}

      {/* Extracted Skills */}
      {job.extracted_skills && job.extracted_skills.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Habilidades Extraídas ({job.extracted_skills.length})
          </h2>

          {/* By Type */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Por Tipo</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Hard Skills */}
              {hardSkills.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">
                    Habilidades Técnicas ({hardSkills.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {hardSkills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                      >
                        {skill.skill_text}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Soft Skills */}
              {softSkills.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">
                    Habilidades Blandas ({softSkills.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {softSkills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm"
                      >
                        {skill.skill_text}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* By Extraction Method */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Por Método de Extracción</h3>
            <div className="space-y-4">
              {/* NER Skills */}
              {nerSkills.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">
                    NER ({nerSkills.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {nerSkills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm"
                        title={`Confianza: ${(skill.confidence_score * 100).toFixed(0)}%`}
                      >
                        {skill.skill_text}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Regex Skills */}
              {regexSkills.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">
                    Regex ({regexSkills.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {regexSkills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm"
                      >
                        {skill.skill_text}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* LLM Skills */}
              {llmSkills.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">
                    LLM (Gemma) ({llmSkills.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {llmSkills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-pink-100 text-pink-800 rounded-full text-sm font-semibold"
                      >
                        {skill.skill_text}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ESCO Links if any */}
          {job.extracted_skills.some(s => s.esco_uri) && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Enlaces ESCO</h3>
              <div className="space-y-2">
                {job.extracted_skills
                  .filter(s => s.esco_uri)
                  .map((skill, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{skill.skill_text}</span>
                      <a
                        href={skill.esco_uri}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        Ver en ESCO →
                      </a>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
