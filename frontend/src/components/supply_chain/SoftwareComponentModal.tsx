import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { supplyChainService } from '../../lib/supplyChainService';
import type {
  LicenseRiskCategory,
  PackageEcosystem,
  SoftwareComponentCreate,
} from '../../types';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface SoftwareComponentModalProps {
  isOpen: boolean;
  onClose: () => void;
  sbomId: number;
  onSuccess: () => void;
}

export const SoftwareComponentModal: React.FC<SoftwareComponentModalProps> = ({
  isOpen,
  onClose,
  sbomId,
  onSuccess,
}) => {
  const [name, setName] = useState('');
  const [version, setVersion] = useState('');
  const [ecosystem, setEcosystem] = useState<PackageEcosystem>('NPM');
  const [purl, setPurl] = useState('');
  const [declaredLicense, setDeclaredLicense] = useState('MIT');
  const [licenseCategory, setLicenseCategory] = useState<LicenseRiskCategory>('PERMISSIVE');
  const [isDirect, setIsDirect] = useState(true);
  const [depth, setDepth] = useState(1);
  const [supplierName, setSupplierName] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setName('');
      setVersion('1.0.0');
      setEcosystem('NPM');
      setPurl('');
      setDeclaredLicense('MIT');
      setLicenseCategory('PERMISSIVE');
      setIsDirect(true);
      setDepth(1);
      setSupplierName('');
      setErrorMsg(null);
    }
  }, [isOpen]);

  const handleEcosystemOrNameChange = (newEco: PackageEcosystem, newName: string, newVer: string) => {
    if (newName.trim()) {
      const formattedPurl = `pkg:${newEco.toLowerCase()}/${newName.trim()}@${newVer.trim() || '1.0.0'}`;
      setPurl(formattedPurl);
    }
  };

  const mutation = useMutation({
    mutationFn: async () => {
      const createData: SoftwareComponentCreate = {
        name: name.trim(),
        version: version.trim(),
        ecosystem,
        purl: purl.trim() || null,
        declared_license: declaredLicense.trim() || null,
        license_category: licenseCategory,
        is_direct_dependency: isDirect,
        dependency_depth: isDirect ? 1 : Math.max(2, depth),
        is_license_prohibited: licenseCategory === 'PROHIBITED',
        supplier_name: supplierName.trim() || null,
      };

      return supplyChainService.addComponent(sbomId, createData);
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to add component to SBOM.';
      setErrorMsg(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg('Component / Package Name is required.');
      return;
    }
    if (!version.trim()) {
      setErrorMsg('Version string is required.');
      return;
    }
    setErrorMsg(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Catalog Software Component / Dependency"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-start gap-2.5 text-xs text-rose-400">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Package Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. lodash, cryptography, axios"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                handleEcosystemOrNameChange(ecosystem, e.target.value, version);
              }}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Version <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. 4.17.21"
              value={version}
              onChange={(e) => {
                setVersion(e.target.value);
                handleEcosystemOrNameChange(ecosystem, name, e.target.value);
              }}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Package Ecosystem <span className="text-rose-400">*</span>
            </label>
            <select
              value={ecosystem}
              onChange={(e) => {
                const eco = e.target.value as PackageEcosystem;
                setEcosystem(eco);
                handleEcosystemOrNameChange(eco, name, version);
              }}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="NPM">npm (JavaScript / Node)</option>
              <option value="PYPI">PyPI (Python)</option>
              <option value="MAVEN">Maven (Java / JVM)</option>
              <option value="GO">Go Modules</option>
              <option value="CARGO">Cargo (Rust)</option>
              <option value="NUGET">NuGet (.NET / C#)</option>
              <option value="RUBYGEMS">RubyGems (Ruby)</option>
              <option value="COMPOSER">Composer (PHP)</option>
              <option value="DOCKER">Docker / Container OCI</option>
              <option value="DEBIAN">Debian / dpkg</option>
              <option value="ALPINE">Alpine / apk</option>
              <option value="GENERIC">Generic Binary / Archive</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Supplier / Publisher
            </label>
            <input
              type="text"
              placeholder="e.g. Open Source Community"
              value={supplierName}
              onChange={(e) => setSupplierName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Package URL (PURL)
          </label>
          <input
            type="text"
            placeholder="pkg:npm/lodash@4.17.21"
            value={purl}
            onChange={(e) => setPurl(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Declared License
            </label>
            <input
              type="text"
              placeholder="e.g. MIT, Apache-2.0, GPL-3.0"
              value={declaredLicense}
              onChange={(e) => setDeclaredLicense(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              License Risk Category <span className="text-rose-400">*</span>
            </label>
            <select
              value={licenseCategory}
              onChange={(e) => setLicenseCategory(e.target.value as LicenseRiskCategory)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="PERMISSIVE">Permissive (MIT, Apache, BSD)</option>
              <option value="WEAK_COPYLEFT">Weak Copyleft (LGPL, MPL)</option>
              <option value="STRONG_COPYLEFT">Strong Copyleft (GPLv2/v3, AGPL)</option>
              <option value="PROHIBITED">Prohibited / Restricted</option>
              <option value="UNCLASSIFIED">Unclassified / Unknown</option>
            </select>
          </div>
        </div>

        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-3">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isDirectCheck"
              checked={isDirect}
              onChange={(e) => {
                setIsDirect(e.target.checked);
                if (e.target.checked) setDepth(1);
                else setDepth(2);
              }}
              className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="isDirectCheck" className="text-xs font-medium text-slate-200">
              Direct Top-Level Dependency (Depth = 1)
            </label>
          </div>

          {!isDirect && (
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Transitive Dependency Tree Depth (2 to 10)
              </label>
              <input
                type="number"
                min={2}
                max={10}
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={mutation.isPending} className="flex items-center gap-1.5">
            {mutation.isPending && <RefreshCw size={14} className="animate-spin" />}
            <span>Catalog Component</span>
          </Button>
        </div>
      </form>
    </Modal>
  );
};
