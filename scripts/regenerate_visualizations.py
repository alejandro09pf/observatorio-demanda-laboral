#!/usr/bin/env python3
"""
Regenera visualizaciones mejoradas para exp8/exp14.
Usa los datos de exp8 (mejor calidad) pero con estrategias de visualización mejoradas.
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from adjustText import adjust_text
import warnings
warnings.filterwarnings('ignore')

# Configuración
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10

def load_experiment_data(exp_path):
    """Carga datos del experimento."""
    results_file = list(exp_path.glob('*_results.json'))[0]

    with open(results_file, 'r') as f:
        results = json.load(f)

    # Cargar embedding_2d (necesitamos reconstruirlo o cargarlo si está guardado)
    # Por ahora, asumimos que tenemos que recalcularlo
    return results

def improved_umap_scatter(results, output_path):
    """
    Visualización mejorada del scatter UMAP.
    Estrategia: Mostrar solo top 50 clusters con mejor distribución espacial.
    """
    print("\n🎨 Generando umap_scatter.png mejorado...")

    # Extraer datos
    clusters = results['clusters']
    n_clusters = results['metrics']['n_clusters']

    # Identificar top 50 clusters por frecuencia total
    cluster_freqs = []
    for c in clusters:
        total_freq = sum(results.get('cluster_frequencies', {}).get(str(c['cluster_id']), [0]))
        cluster_freqs.append({
            'cluster_id': c['cluster_id'],
            'size': c['size'],
            'total_freq': total_freq,
            'top_skills': c['top_skills']
        })

    top_clusters = sorted(cluster_freqs, key=lambda x: x['total_freq'], reverse=True)[:50]

    fig, ax = plt.subplots(figsize=(28, 20))

    # TODO: Necesitamos las coordenadas UMAP 2D
    # Por ahora, crear visualización conceptual

    ax.set_title(f'UMAP Projection - Top 50 Clusters (de {n_clusters} total)',
                 fontsize=20, fontweight='bold', pad=20)
    ax.set_xlabel('UMAP Dimension 1', fontsize=16)
    ax.set_ylabel('UMAP Dimension 2', fontsize=16)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   ✅ Guardado: {output_path}")


def improved_macro_centroids(results, output_path):
    """
    Visualización mejorada de centroides macro.
    Estrategia: Mejor distribución espacial, evitar sobreposición.
    """
    print("\n🎨 Generando umap_macro_centroids.png mejorado...")

    clusters = results['clusters']

    # Top 40 clusters
    cluster_data = []
    for c in clusters:
        cluster_data.append({
            'id': c['cluster_id'],
            'size': c['size'],
            'top_skills': c['top_skills']
        })

    top_clusters = sorted(cluster_data, key=lambda x: x['size'], reverse=True)[:40]

    fig, ax = plt.subplots(figsize=(26, 20))

    # TODO: Usar coordenadas reales y apply repulsion algorithm

    ax.set_title('Vista Macro: Top 40 Clusters (Centroides)',
                 fontsize=20, fontweight='bold', pad=20)
    ax.set_xlabel('UMAP Dimension 1', fontsize=16)
    ax.set_ylabel('UMAP Dimension 2', fontsize=16)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   ✅ Guardado: {output_path}")


def improved_fine_by_meta(results_exp14, output_path):
    """
    Visualización mejorada de fine clusters coloreados por meta-cluster.
    Usa exp14 que tiene 3 meta-clusters funcionales.
    Estrategia: Anotar top 8-10 skills por meta-cluster, priorizando tecnologías.
    """
    print("\n🎨 Generando umap_fine_by_meta.png mejorado...")

    clusters = results_exp14['clusters']
    n_meta = results_exp14['metrics']['n_meta_clusters']

    # Agrupar por meta-cluster
    meta_groups = {}
    for c in clusters:
        meta_id = c.get('meta_cluster', -1)
        if meta_id not in meta_groups:
            meta_groups[meta_id] = []
        meta_groups[meta_id].append(c)

    # Identificar skills tecnológicas vs soft skills
    tech_keywords = ['python', 'java', 'sql', 'aws', 'docker', 'kubernetes', 'react',
                     'node', 'git', 'api', 'cloud', 'data', 'machine learning',
                     'tensorflow', 'spark', 'kafka', 'redis', 'mongodb', 'postgresql',
                     '.net', 'c#', 'javascript', 'typescript', 'angular', 'vue',
                     'spring', 'django', 'flask', 'ci/cd', 'devops', 'microservices',
                     'azure', 'gcp', 'terraform', 'jenkins', 'power bi', 'tableau',
                     'pandas', 'numpy', 'scikit']

    fig, ax = plt.subplots(figsize=(30, 22))

    cmap = plt.colormaps.get_cmap('tab10')

    print(f"\nMeta-clusters detectados: {n_meta}")
    for meta_id in sorted(meta_groups.keys()):
        if meta_id == -1:
            continue

        clusters_in_meta = meta_groups[meta_id]
        n_clusters = len(clusters_in_meta)
        total_skills = sum(c['size'] for c in clusters_in_meta)

        print(f"\n  Meta-cluster {meta_id}: {n_clusters} fine clusters, {total_skills} skills")

        # Recopilar todas las skills del meta-cluster
        all_skills = []
        for c in clusters_in_meta:
            for skill in c['top_skills']:
                all_skills.append(skill)

        # Priorizar tecnologías
        tech_skills = [s for s in all_skills if any(kw in s.lower() for kw in tech_keywords)]
        soft_skills = [s for s in all_skills if s not in tech_skills]

        # Top 10: priorizar tecnologías
        top_skills_to_annotate = tech_skills[:7] + soft_skills[:3]

        print(f"    Anotando: {len(top_skills_to_annotate)} skills")
        for skill in top_skills_to_annotate[:5]:
            print(f"      • {skill}")

    # TODO: Plotear con coordenadas reales

    ax.set_title(f'Fine Clusters por Meta-Cluster ({n_meta} grupos macro)',
                 fontsize=20, fontweight='bold', pad=20)
    ax.set_xlabel('UMAP Dimension 1', fontsize=16)
    ax.set_ylabel('UMAP Dimension 2', fontsize=16)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   ✅ Guardado: {output_path}")


if __name__ == '__main__':
    print("=" * 80)
    print("REGENERACIÓN DE VISUALIZACIONES MEJORADAS")
    print("=" * 80)

    # Cargar datos
    exp8_path = Path('outputs/clustering/experiments/pipeline_b_300_post/exp8_local_leaf')
    exp14_path = Path('outputs/clustering/experiments/pipeline_b_300_post/exp14_better_meta_mcs3')

    print("\n📂 Cargando datos de exp8 (mejor calidad)...")
    results_exp8 = load_experiment_data(exp8_path)

    print("\n📂 Cargando datos de exp14 (mejor meta-clustering)...")
    results_exp14 = load_experiment_data(exp14_path)

    # Generar visualizaciones
    output_dir = exp8_path

    # 1. UMAP scatter mejorado
    improved_umap_scatter(results_exp8, output_dir / 'umap_scatter_v2.png')

    # 2. Macro centroids mejorado
    improved_macro_centroids(results_exp8, output_dir / 'umap_macro_centroids_v2.png')

    # 3. Fine by meta mejorado (usa exp14)
    improved_fine_by_meta(results_exp14, exp14_path / 'umap_fine_by_meta_v2.png')

    print("\n" + "=" * 80)
    print("✅ VISUALIZACIONES REGENERADAS")
    print("=" * 80)
    print(f"\nArchivos generados en:")
    print(f"  • {output_dir / 'umap_scatter_v2.png'}")
    print(f"  • {output_dir / 'umap_macro_centroids_v2.png'}")
    print(f"  • {exp14_path / 'umap_fine_by_meta_v2.png'}")
    print()
