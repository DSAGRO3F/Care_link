/**
 * Service API pour le module Catalogue.
 *
 * Endpoints backend : /api/v1/service-templates (global, pas de tenant)
 * Convention : un objet exporté par namespace (comme entity.service.ts).
 */

import api from './api';
import type {
  CategoryWithCounts,
  DomainWithCounts,
  ServiceTemplateCreate,
  ServiceTemplateFilters,
  ServiceTemplateList,
  ServiceTemplateResponse,
  ServiceTemplateSummary,
  ServiceTemplateUpdate,
} from '@/types';

const BASE = '/platform/catalog/service-templates';

// =============================================================================
// SERVICE TEMPLATES (Catalogue national)
// =============================================================================

export const catalogService = {
  /**
   * Liste paginée des service templates avec filtres.
   */
  async getAll(
    page = 1,
    size = 100,
    filters?: ServiceTemplateFilters,
  ): Promise<ServiceTemplateList> {
    const params: Record<string, string | number | boolean> = { page, size };

    if (filters?.domain) params.domain = filters.domain;
    if (filters?.category) params.category = filters.category;
    if (filters?.is_medical_act !== undefined && filters.is_medical_act !== null)
      params.is_medical_act = filters.is_medical_act;
    if (filters?.requires_prescription !== undefined && filters.requires_prescription !== null)
      params.requires_prescription = filters.requires_prescription;
    if (filters?.apa_eligible !== undefined && filters.apa_eligible !== null)
      params.apa_eligible = filters.apa_eligible;
    if (filters?.status) params.status = filters.status;
    if (filters?.search) params.search = filters.search;

    const { data } = await api.get<ServiceTemplateList>(BASE, { params });
    return data;
  },

  /**
   * Récupère un service template par ID.
   */
  async getById(id: number): Promise<ServiceTemplateResponse> {
    const { data } = await api.get<ServiceTemplateResponse>(`${BASE}/${id}`);
    return data;
  },

  /**
   * Récupère un service template par code.
   */
  async getByCode(code: string): Promise<ServiceTemplateResponse> {
    const { data } = await api.get<ServiceTemplateResponse>(`${BASE}/code/${code}`);
    return data;
  },

  /**
   * Liste des domaines SERAFIN-PH avec compteurs.
   */
  async getDomains(): Promise<DomainWithCounts[]> {
    const { data } = await api.get<{ domains: DomainWithCounts[] }>(`${BASE}/domains`);
    return data.domains;
  },

  /**
   * Liste des catégories SERAFIN-PH avec compteurs.
   */
  async getCategories(): Promise<CategoryWithCounts[]> {
    const { data } = await api.get<{ categories: CategoryWithCounts[] }>(`${BASE}/categories`);
    return data.categories;
  },

  /**
   * Services actifs par domaine.
   */
  async getByDomain(
    domain: string,
  ): Promise<{
    domain: string;
    domain_name: string;
    items: ServiceTemplateSummary[];
    total: number;
  }> {
    const { data } = await api.get<{
      domain: string;
      domain_name: string;
      items: ServiceTemplateSummary[];
      total: number;
    }>(`${BASE}/by-domain/${domain}`);
    return data;
  },

  /**
   * Services actifs par catégorie.
   */
  async getByCategory(category: string): Promise<{
    category: string;
    category_name: string;
    domain: string;
    items: ServiceTemplateSummary[];
    total: number;
  }> {
    const { data } = await api.get<{
      category: string;
      category_name: string;
      domain: string;
      items: ServiceTemplateSummary[];
      total: number;
    }>(`${BASE}/by-category/${category}`);
    return data;
  },

  /**
   * Crée un nouveau service template (super-admin).
   */
  async create(payload: ServiceTemplateCreate): Promise<ServiceTemplateResponse> {
    const { data } = await api.post<ServiceTemplateResponse>(BASE, payload);
    return data;
  },

  /**
   * Met à jour un service template (super-admin).
   */
  async update(id: number, payload: ServiceTemplateUpdate): Promise<ServiceTemplateResponse> {
    const { data } = await api.patch<ServiceTemplateResponse>(`${BASE}/${id}`, payload);
    return data;
  },

  /**
   * Désactive un service template (soft delete, super-admin).
   */
  async deactivate(id: number): Promise<void> {
    await api.delete(`${BASE}/${id}`);
  },
};
