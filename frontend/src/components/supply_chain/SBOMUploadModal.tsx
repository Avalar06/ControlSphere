import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { supplyChainService } from '../../lib/supplyChainService';
import type { SBOMDocumentCreate, SBOMFormat, SoftwareProduct } from '../../types';
import { AlertCircle, RefreshCw, CheckCircle2 } from 'lucide-react';

interface SBOMUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  productId: number;
  product?: SoftwareProduct | null;
  onSuccess: () => void;
}

export const SBOMUploadModal: React.FC<SBOMUploadModalProps> = ({
  isOpen,
  onClose,
  productId,
  product,
  onSuccess,
}) => {
  const [sbomCode, setSbomCode] = useState('');
  const [format, setFormat] = useState<SBOMFormat>('CYCLONEDX_JSON');
  const [specVersion, setSpecVersion] = useState('1.5');
  const [authorName, setAuthorName] = useState('');
  const [toolName, setToolName] = useState('ControlSphere Ingestion Pipeline');
  const [sha256Hash, setSha256Hash] = useState('');
  const [rawJsonText, setRawJsonText] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const codeSuffix = Math.random().toString(36).substring(2, 7).toUpperCase();
      setSbomCode(`SBOM-${product?.product_code || 'PROD'}-${codeSuffix}`);
      setFormat('CYCLONEDX_JSON');
      setSpecVersion('1.5');
      setAuthorName('SecOps Build Agent');
      setToolName('ControlSphere CycloneDX Parser 1.0');
      setSha256Hash('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
      setRawJsonText('{\n  "bomFormat": "CycloneDX",\n  "specVersion": "1.5",\n  "version": 1,\n  "components": []\n}');
      setErrorMsg(null);
    }
  }, [isOpen, product]);

  const mutation = useMutation({
    mutationFn: async () => {
      let parsedPayload: Record<string, any> | null = null;
      if (rawJsonText.trim()) {
        try {
          parsedPayload = JSON.parse(rawJsonText);
        } catch (e: any) {
          throw new Error(`Invalid JSON syntax in SBOM Payload: ${e.message}`);
        }
      }

      const createData: SBOMDocumentCreate = {
        sbom_code: sbomCode.trim().toUpperCase(),
        format,
        spec_version: specVersion.trim(),
        author_name: authorName.trim() || null,
        tool_name: toolName.trim() || null,
        sha256_hash: sha256Hash.trim().toLowerCase(),
        raw_payload: parsedPayload,
      };

      return supplyChainService.ingestSBOM(productId, createData);
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to ingest SBOM document.';
      setErrorMsg(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sbomCode.trim()) {
      setErrorMsg('SBOM Code is required.');
      return;
    }
    if (!specVersion.trim()) {
      setErrorMsg('Specification Version is required.');
      return;
    }
    if (sha256Hash.trim().length !== 64) {
      setErrorMsg('Cryptographic SHA-256 Digest must be exactly 64 hexadecimal characters.');
      return;
    }
    setErrorMsg(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Ingest Software Bill of Materials (SBOM): ${product?.name || `Product #${productId}`}`}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-start gap-2.5 text-xs text-rose-400">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-xs text-indigo-300 flex items-start gap-2">
          <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-indigo-400" />
          <span>
            Ingesting this manifest will catalog its components and automatically supersede any previously active SBOM for this Software Product.
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              SBOM Code <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. SBOM-PROD-001-A"
              value={sbomCode}
              onChange={(e) => setSbomCode(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Format Standard <span className="text-rose-400">*</span>
            </label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as SBOMFormat)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="CYCLONEDX_JSON">CycloneDX (JSON)</option>
              <option value="SPDX_JSON">SPDX (JSON)</option>
              <option value="SWID_XML">SWID (XML)</option>
              <option value="CUSTOM_JSON">Custom JSON Manifest</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Spec Version <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. 1.5 or 2.3"
              value={specVersion}
              onChange={(e) => setSpecVersion(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Author / Maintainer
            </label>
            <input
              type="text"
              placeholder="e.g. SecOps Automation"
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Generating Tool
            </label>
            <input
              type="text"
              placeholder="e.g. Syft v0.98.0"
              value={toolName}
              onChange={(e) => setToolName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Cryptographic SHA-256 Hash (64 hex characters) <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            placeholder="e.g. a1b2c3...64-char-hex-digest"
            value={sha256Hash}
            onChange={(e) => setSha256Hash(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Raw Manifest Payload (JSON)
          </label>
          <textarea
            rows={5}
            placeholder="Paste CycloneDX / SPDX JSON content here..."
            value={rawJsonText}
            onChange={(e) => setRawJsonText(e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 font-mono placeholder-slate-600 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={mutation.isPending} className="flex items-center gap-1.5">
            {mutation.isPending && <RefreshCw size={14} className="animate-spin" />}
            <span>Ingest Manifest</span>
          </Button>
        </div>
      </form>
    </Modal>
  );
};
