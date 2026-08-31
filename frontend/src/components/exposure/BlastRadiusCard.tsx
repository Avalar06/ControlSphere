import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../ui/Table';
import type { ExposureAssetLink, VulnerabilityExposure } from '../../types';
import {
  Activity,
  Building2,
  Cpu,
  Layers,
  Plus,
  Shield,
  Trash2,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface BlastRadiusCardProps {
  exposure: VulnerabilityExposure;
  assetLinks: ExposureAssetLink[];
  onOpenLinkModal: () => void;
  onUnlinkAsset: (linkId: number) => void;
  canManage: boolean;
  isResolved: boolean;
}

export const BlastRadiusCard: React.FC<BlastRadiusCardProps> = ({
  exposure,
  assetLinks,
  onOpenLinkModal,
  onUnlinkAsset,
  canManage,
  isResolved,
}) => {
  // Determine highest tier for display context
  const tiers = assetLinks
    .map((l) => l.process_tier)
    .filter((t): t is NonNullable<typeof t> => !!t);

  let highestTier: string = 'STANDARD (1.00×)';
  let tierBadgeVariant: 'danger' | 'warning' | 'info' | 'default' = 'default';

  if (tiers.includes('TIER_1')) {
    highestTier = 'TIER 1 CRITICAL PROCESS (1.25×)';
    tierBadgeVariant = 'danger';
  } else if (tiers.includes('TIER_2')) {
    highestTier = 'TIER 2 HIGH PROCESS (1.15×)';
    tierBadgeVariant = 'warning';
  } else if (tiers.includes('TIER_3')) {
    highestTier = 'TIER 3 MODERATE PROCESS (1.05×)';
    tierBadgeVariant = 'info';
  }

  return (
    <Card className="p-6 space-y-6 bg-slate-900/60 border-slate-800">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-indigo-400" />
            <h3 className="text-base font-bold text-slate-100">
              Blast Radius & Technical Asset Exposure
            </h3>
          </div>
          <p className="text-xs text-slate-400">
            Technical assets linked to {exposure.cve_id} and their upstream business process impact multipliers.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Criticality Multiplier:</span>
            <Badge variant={tierBadgeVariant}>{highestTier}</Badge>
          </div>
          {canManage && !isResolved && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onOpenLinkModal}
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              Link Asset
            </Button>
          )}
        </div>
      </div>

      {assetLinks.length === 0 ? (
        <div className="py-8 text-center space-y-3 bg-slate-950/40 rounded-xl border border-dashed border-slate-800">
          <Layers className="h-8 w-8 text-slate-500 mx-auto" />
          <p className="text-xs text-slate-400">
            No technical assets currently associated with this vulnerability exposure.
          </p>
          {canManage && !isResolved && (
            <Button variant="outline" size="sm" onClick={onOpenLinkModal}>
              Link First Asset
            </Button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Asset Identifier</TableHeaderCell>
                <TableHeaderCell>Type & Env</TableHeaderCell>
                <TableHeaderCell>Linked Process (Phase 13)</TableHeaderCell>
                <TableHeaderCell>Linked Vendor (Phase 9)</TableHeaderCell>
                <TableHeaderCell>Linked Control (Phase 2)</TableHeaderCell>
                {canManage && !isResolved && <TableHeaderCell className="text-right">Actions</TableHeaderCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {assetLinks.map((link) => (
                <TableRow key={link.id} className="hover:bg-slate-800/30">
                  <TableCell className="font-mono text-xs font-semibold text-slate-200">
                    {link.asset_identifier}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <Badge variant="default">{link.asset_type}</Badge>
                      <span className="text-xs text-slate-500">•</span>
                      <span className="text-xs text-slate-400">{link.environment}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {link.process_id ? (
                      <Link
                        to={`/resilience/processes/${link.process_id}`}
                        className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        <Activity className="h-3.5 w-3.5" />
                        <span>{link.process_name || `Process #${link.process_id}`}</span>
                        {link.process_tier && (
                          <Badge variant="info" className="ml-1 text-[10px]">
                            {link.process_tier}
                          </Badge>
                        )}
                      </Link>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {link.vendor_id ? (
                      <Link
                        to={`/vendors/${link.vendor_id}`}
                        className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors"
                      >
                        <Building2 className="h-3.5 w-3.5" />
                        <span>{link.vendor_name || `Vendor #${link.vendor_id}`}</span>
                      </Link>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {link.control_id ? (
                      <Link
                        to="/controls"
                        className="inline-flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
                      >
                        <Shield className="h-3.5 w-3.5" />
                        <span>{link.control_title || `Control #${link.control_id}`}</span>
                      </Link>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </TableCell>
                  {canManage && !isResolved && (
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onUnlinkAsset(link.id)}
                        className="text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 p-1 h-7 w-7"
                        title="Unlink asset"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  );
};
