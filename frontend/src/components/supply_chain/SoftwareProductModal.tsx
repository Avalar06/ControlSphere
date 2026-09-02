import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { supplyChainService } from '../../lib/supplyChainService';
import type {
  BusinessCriticality,
  SoftwareProduct,
  SoftwareProductCreate,
  SoftwareProductType,
  SoftwareProductUpdate,
} from '../../types';
import { AlertCircle, RefreshCw, Package } from 'lucide-react';

interface SoftwareProductModalProps {
  isOpen: boolean;
  onClose: () => void;
  product?: SoftwareProduct | null;
  onSuccess: () => void;
}

export const SoftwareProductModal: React.FC<SoftwareProductModalProps> = ({
  isOpen,
  onClose,
  product,
  onSuccess,
}) => {
  const isEdit = Boolean(product);

  const [productCode, setProductCode] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [productType, setProductType] = useState<SoftwareProductType>('INTERNAL_APPLICATION');
  const [criticalityTier, setCriticalityTier] = useState<BusinessCriticality>('HIGH');
  const [versionTag, setVersionTag] = useState('1.0.0');
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [buildPipelineUrl, setBuildPipelineUrl] = useState('');
  const [businessProcessId, setBusinessProcessId] = useState<string>('');
  const [aiSystemId, setAiSystemId] = useState<string>('');
  const [vendorId, setVendorId] = useState<string>('');
  const [remediationPlanId, setRemediationPlanId] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (product) {
      setProductCode(product.product_code);
      setName(product.name);
      setDescription(product.description || '');
      setProductType(product.product_type);
      setCriticalityTier(product.criticality_tier);
      setVersionTag(product.version_tag);
      setRepositoryUrl(product.repository_url || '');
      setBuildPipelineUrl(product.build_pipeline_url || '');
      setBusinessProcessId(product.business_process_id ? String(product.business_process_id) : '');
      setAiSystemId(product.ai_system_id ? String(product.ai_system_id) : '');
      setVendorId(product.vendor_id ? String(product.vendor_id) : '');
      setRemediationPlanId(product.remediation_plan_id ? String(product.remediation_plan_id) : '');
    } else {
      setProductCode('');
      setName('');
      setDescription('');
      setProductType('INTERNAL_APPLICATION');
      setCriticalityTier('HIGH');
      setVersionTag('1.0.0');
      setRepositoryUrl('');
      setBuildPipelineUrl('');
      setBusinessProcessId('');
      setAiSystemId('');
      setVendorId('');
      setRemediationPlanId('');
    }
    setErrorMsg(null);
  }, [product, isOpen]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (isEdit && product) {
        const updateData: SoftwareProductUpdate = {
          name: name.trim(),
          description: description.trim() || null,
          criticality_tier: criticalityTier,
          version_tag: versionTag.trim(),
          repository_url: repositoryUrl.trim() || null,
          build_pipeline_url: buildPipelineUrl.trim() || null,
          business_process_id: businessProcessId ? Number(businessProcessId) : null,
          ai_system_id: aiSystemId ? Number(aiSystemId) : null,
          vendor_id: vendorId ? Number(vendorId) : null,
          remediation_plan_id: remediationPlanId ? Number(remediationPlanId) : null,
        };
        return supplyChainService.updateProduct(product.id, updateData);
      } else {
        const createData: SoftwareProductCreate = {
          product_code: productCode.trim().toUpperCase(),
          name: name.trim(),
          description: description.trim() || null,
          product_type: productType,
          criticality_tier: criticalityTier,
          version_tag: versionTag.trim(),
          repository_url: repositoryUrl.trim() || null,
          build_pipeline_url: buildPipelineUrl.trim() || null,
          business_process_id: businessProcessId ? Number(businessProcessId) : null,
          ai_system_id: aiSystemId ? Number(aiSystemId) : null,
          vendor_id: vendorId ? Number(vendorId) : null,
          remediation_plan_id: remediationPlanId ? Number(remediationPlanId) : null,
        };
        return supplyChainService.createProduct(createData);
      }
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to save Software Product. Please verify input requirements.';
      setErrorMsg(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg('Product Name is required.');
      return;
    }
    if (!isEdit && !productCode.trim()) {
      setErrorMsg('Product Code is required.');
      return;
    }
    if (!versionTag.trim()) {
      setErrorMsg('Version Tag is required.');
      return;
    }
    setErrorMsg(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Software Product: ${product?.product_code}` : 'Catalog New Software Product'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-start gap-2.5 text-xs text-rose-400">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Product Code <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              disabled={isEdit}
              placeholder="e.g. PROD-CORE-001"
              value={productCode}
              onChange={(e) => setProductCode(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 disabled:opacity-50 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Version Tag <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. 2.4.1"
              value={versionTag}
              onChange={(e) => setVersionTag(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Product Name <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            placeholder="e.g. Customer Authentication Gateway"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Description
          </label>
          <textarea
            rows={2}
            placeholder="Purpose, operational architecture, and security boundaries..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Product Type <span className="text-rose-400">*</span>
            </label>
            <select
              value={productType}
              onChange={(e) => setProductType(e.target.value as SoftwareProductType)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="INTERNAL_APPLICATION">Internal Application</option>
              <option value="MICROSERVICE">Microservice</option>
              <option value="COTS_SOFTWARE">Commercial Off-The-Shelf (COTS)</option>
              <option value="OPEN_SOURCE_LIBRARY">Open-Source Library</option>
              <option value="EMBEDDED_FIRMWARE">Embedded Firmware</option>
              <option value="CLOUD_SERVICE">Cloud Service / SaaS</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Criticality Tier <span className="text-rose-400">*</span>
            </label>
            <select
              value={criticalityTier}
              onChange={(e) => setCriticalityTier(e.target.value as BusinessCriticality)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="CRITICAL">Tier 1: Critical</option>
              <option value="HIGH">Tier 2: High</option>
              <option value="MEDIUM">Tier 3: Medium</option>
              <option value="LOW">Tier 4: Low</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Source Repository URL
            </label>
            <input
              type="text"
              placeholder="e.g. https://github.com/org/auth-service"
              value={repositoryUrl}
              onChange={(e) => setRepositoryUrl(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              CI/CD Build Pipeline URL
            </label>
            <input
              type="text"
              placeholder="e.g. https://ci.internal.org/builds/auth"
              value={buildPipelineUrl}
              onChange={(e) => setBuildPipelineUrl(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono text-xs"
            />
          </div>
        </div>

        {/* Cross-Module Lineage Integration */}
        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
            <Package size={14} className="text-indigo-400" />
            <span>Cross-Module GRC Lineage Links</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Business Process ID (Phase 13)
              </label>
              <input
                type="number"
                placeholder="e.g. 1"
                value={businessProcessId}
                onChange={(e) => setBusinessProcessId(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                AI System ID (Phase 15)
              </label>
              <input
                type="number"
                placeholder="e.g. 2"
                value={aiSystemId}
                onChange={(e) => setAiSystemId(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Third-Party Vendor ID (Phase 9)
              </label>
              <input
                type="number"
                placeholder="e.g. 3"
                value={vendorId}
                onChange={(e) => setVendorId(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                CAPA Remediation Plan ID (Phase 11)
              </label>
              <input
                type="number"
                placeholder="e.g. 4"
                value={remediationPlanId}
                onChange={(e) => setRemediationPlanId(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={mutation.isPending} className="flex items-center gap-1.5">
            {mutation.isPending && <RefreshCw size={14} className="animate-spin" />}
            <span>{isEdit ? 'Update Product' : 'Create Product'}</span>
          </Button>
        </div>
      </form>
    </Modal>
  );
};
