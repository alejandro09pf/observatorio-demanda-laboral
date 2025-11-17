'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { getJobById, JobDetail, ExtractedSkill } from '@/lib/api';
import Link from 'next/link';

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.jobId as string;

  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters for skills
  const [skillTypeFilter, setSkillTypeFilter] = useState<string>('all');
  const [extractionMethodFilter, setExtractionMethodFilter] = useState<string>('all');
  const [mappingStatusFilter, setMappingStatusFilter] = useState<string>('all');

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

  // Combine all skills from all sources
  const allSkills = useMemo(() => {
    if (!job) return [];

    const skills: ExtractedSkill[] = [
      ...(job.extracted_skills || []),
      ...(job.enhanced_skills || []),
      ...(job.manual_skills || [])
    ];

    return skills;
  }, [job]);

  // Filter skills based on selected filters
  const filteredSkills = useMemo(() => {
    return allSkills.filter(skill => {
      if (skillTypeFilter !== 'all' && skill.skill_type !== skillTypeFilter) return false;
      if (extractionMethodFilter !== 'all') {
        if (extractionMethodFilter === 'manual' && skill.extraction_method !== 'manual') return false;
        if (extractionMethodFilter === 'pipeline_a' && !['ner', 'regex'].includes(skill.extraction_method)) return false;
        if (extractionMethodFilter === 'pipeline_b' && skill.extraction_method !== 'pipeline_b') return false;
        if (extractionMethodFilter === 'ner' && skill.extraction_method !== 'ner') return false;
        if (extractionMethodFilter === 'regex' && skill.extraction_method !== 'regex') return false;
      }
      if (mappingStatusFilter === 'esco_mapped' && !skill.esco_uri) return false;
      if (mappingStatusFilter === 'unmapped' && skill.esco_uri) return false;
      return true;
    });
  }, [allSkills, skillTypeFilter, extractionMethodFilter, mappingStatusFilter]);

  // Group filtered skills by type
  const hardSkills = filteredSkills.filter(s => s.skill_type === 'hard');
  const softSkills = filteredSkills.filter(s => s.skill_type === 'soft');

  const hasActiveFilters = skillTypeFilter !== 'all' || extractionMethodFilter !== 'all' || mappingStatusFilter !== 'all';

  const clearFilters = () => {
    setSkillTypeFilter('all');
    setExtractionMethodFilter('all');
    setMappingStatusFilter('all');
  };

  // Get skill method badge
  const getMethodBadge = (method: string) => {
    switch (method) {
      case 'manual':
        return <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-800">Manual</span>;
      case 'ner':
        return <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">NER</span>;
      case 'regex':
        return <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-800">Regex</span>;
      case 'pipeline_b':
        return <span className="text-xs px-1.5 py-0.5 rounded bg-pink-100 text-pink-800">Pipeline B</span>;
      default:
        return null;
    }
  };

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

  return (
    <div className="space-y-4">
      {/* Back Button */}
      <Link href="/jobs" className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm">
        ← Volver a Empleos
      </Link>

      {/* Job Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{job.title}</h1>
            <p className="text-lg text-gray-600">{job.company || 'Empresa confidencial'}</p>
          </div>
          <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
            {job.portal}
          </span>
        </div>

        {/* Job Meta Information */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-3 border-t border-gray-200">
          <div>
            <p className="text-xs text-gray-500">Ubicación</p>
            <p className="text-sm font-medium text-gray-900">{job.location || 'No especificado'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">País</p>
            <p className="text-sm font-medium text-gray-900">{job.country}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Publicado</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(job.posted_date).toLocaleDateString('es-ES')}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Recolectado</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date(job.scraped_at).toLocaleDateString('es-ES')}
            </p>
          </div>
        </div>

        {/* Additional Meta */}
        {(job.salary_raw || job.contract_type || job.remote_type) && (
          <div className="grid grid-cols-3 gap-3 pt-3 mt-3 border-t border-gray-200">
            {job.salary_raw && (
              <div>
                <p className="text-xs text-gray-500">Salario</p>
                <p className="text-sm font-medium text-gray-900">{job.salary_raw}</p>
              </div>
            )}
            {job.contract_type && (
              <div>
                <p className="text-xs text-gray-500">Tipo de Contrato</p>
                <p className="text-sm font-medium text-gray-900">{job.contract_type}</p>
              </div>
            )}
            {job.remote_type && (
              <div>
                <p className="text-xs text-gray-500">Modalidad</p>
                <p className="text-sm font-medium text-gray-900">{job.remote_type}</p>
              </div>
            )}
          </div>
        )}

        {/* External Link */}
        {job.url && (
          <div className="pt-3 mt-3 border-t border-gray-200">
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800"
            >
              Ver oferta original →
            </a>
          </div>
        )}
      </div>

      {/* Job Description */}
      {job.description && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">Descripción</h2>
          <div className="prose prose-sm max-w-none">
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{job.description}</p>
          </div>
        </div>
      )}

      {/* Requirements */}
      {job.requirements && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">Requisitos</h2>
          <div className="prose prose-sm max-w-none">
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{job.requirements}</p>
          </div>
        </div>
      )}

      {/* Extracted Skills */}
      {allSkills.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between gap-6 mb-4">
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                Habilidades Extraídas ({filteredSkills.length})
              </h2>
              <p className="text-xs text-gray-600 mt-1">
                {job.manual_skills && job.manual_skills.length > 0 && `${job.manual_skills.length} manual`}
                {job.enhanced_skills && job.enhanced_skills.length > 0 && ` • ${job.enhanced_skills.length} Pipeline B`}
                {job.extracted_skills && job.extracted_skills.length > 0 && ` • ${job.extracted_skills.length} Pipeline A`}
              </p>
            </div>

            {/* Compact Filters */}
            <div className="bg-gray-50 rounded-lg p-3 min-w-[500px]">
              <div className="grid grid-cols-3 gap-2.5">
                <div>
                  <label htmlFor="type-filter" className="block text-xs font-medium text-gray-600 mb-1">
                    Tipo
                  </label>
                  <select
                    id="type-filter"
                    value={skillTypeFilter}
                    onChange={(e) => setSkillTypeFilter(e.target.value)}
                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="all">Todas</option>
                    <option value="hard">Hard</option>
                    <option value="soft">Soft</option>
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
                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="all">Todos</option>
                    <option value="manual">Manual</option>
                    <option value="pipeline_a">Pipeline A</option>
                    <option value="pipeline_b">Pipeline B</option>
                    <option value="ner">NER</option>
                    <option value="regex">Regex</option>
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
                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="all">Todas</option>
                    <option value="esco_mapped">ESCO</option>
                    <option value="unmapped">Emergentes</option>
                  </select>
                </div>
              </div>

              {hasActiveFilters && (
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={clearFilters}
                    className="px-2 py-1 text-xs bg-white text-gray-700 rounded hover:bg-gray-100 border border-gray-300"
                  >
                    Limpiar filtros
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Skills by Type */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Hard Skills */}
            {hardSkills.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-800 mb-2">
                  Habilidades Técnicas ({hardSkills.length})
                </h3>
                <div className="space-y-1.5">
                  {hardSkills.map((skill, idx) => (
                    <Link
                      key={idx}
                      href={`/skills/${encodeURIComponent(skill.skill_text)}`}
                      className="flex items-center justify-between p-2 bg-blue-50 rounded hover:bg-blue-100 transition cursor-pointer border border-transparent hover:border-blue-300"
                    >
                      <div className="flex items-center gap-2 flex-1">
                        <span className="text-sm text-gray-900 hover:text-blue-600">{skill.skill_text}</span>
                        {getMethodBadge(skill.extraction_method)}
                      </div>
                      {skill.esco_uri && (
                        <a
                          href={skill.esco_uri}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 whitespace-nowrap ml-2"
                          onClick={(e) => e.stopPropagation()}
                        >
                          ESCO →
                        </a>
                      )}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Soft Skills */}
            {softSkills.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-800 mb-2">
                  Habilidades Blandas ({softSkills.length})
                </h3>
                <div className="space-y-1.5">
                  {softSkills.map((skill, idx) => (
                    <Link
                      key={idx}
                      href={`/skills/${encodeURIComponent(skill.skill_text)}`}
                      className="flex items-center justify-between p-2 bg-purple-50 rounded hover:bg-purple-100 transition cursor-pointer border border-transparent hover:border-purple-300"
                    >
                      <div className="flex items-center gap-2 flex-1">
                        <span className="text-sm text-gray-900 hover:text-purple-600">{skill.skill_text}</span>
                        {getMethodBadge(skill.extraction_method)}
                      </div>
                      {skill.esco_uri && (
                        <a
                          href={skill.esco_uri}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 whitespace-nowrap ml-2"
                          onClick={(e) => e.stopPropagation()}
                        >
                          ESCO →
                        </a>
                      )}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* No results message */}
          {filteredSkills.length === 0 && (
            <div className="text-center py-8 text-gray-500 text-sm">
              No se encontraron habilidades con los filtros seleccionados
            </div>
          )}
        </div>
      )}
    </div>
  );
}
