import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { resilienceService } from '../../lib/resilienceService';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../ui/Table';
import type { BiaStatus, BusinessImpactAnalysis } from '../../types';
import {
  Archive,
  Edit2,
  History,
  Lock,
  ShieldCheck,
} from 'lucide-react';

interface BiaHistoryCardProps {
  processId: number;
  bias: BusinessImpactAnalysis[];
  onApproveClick: (bia: BusinessImpactAnalysis) => void;
  onEditClick: (bia: BusinessImpactAnalysis) => void;
  canManage: boolean;
  canApprove: boolean;
}

export const BiaHistoryCard: React.FC<BiaHistoryCardProps> = ({
  processId,
  bias,
  onApproveClick,
  onEditClick,
  canManage,
  canApprove,
}) => {
  const queryClient = useQueryClient();

  const archiveMutation = useMutation({
    mutationFn: (biaId: number) => resilienceService.archiveDraftBia(biaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-process', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-process-bias', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-processes'] });
    },
  });

  const getStatusBadge = (status: BiaStatus) => {
    switch (status) {
      case 'DRAFT':
        return <Badge variant="warning">DRAFT</Badge>;
      case 'ACTIVE':
        return <Badge variant="success">ACTIVE BASELINE</Badge>;
      case 'SUPERSEDED':
        return <Badge variant="default">SUPERSEDED</Badge>;
      case 'ARCHIVED':
        return <Badge variant="danger">ARCHIVED</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <Card className="border-slate-800 bg-slate-900/90 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <History className="h-5 w-5 text-indigo-400" />
          <div>
            <h3 className="text-sm font-semibold text-slate-100">
              BIA Version History &amp; Four-Eyes Audit Trail
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Active and superseded baselines are immutable records protected by cryptographic four-eyes governance.
            </p>
          </div>
        </div>
      </div>

      {bias.length === 0 ? (
        <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-800">
          <History className="h-8 w-8 text-slate-600 mx-auto mb-2" />
          <p className="text-xs text-slate-400 font-medium">No BIA records drafted for this business process yet.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Version</TableHeaderCell>
                <TableHeaderCell>Governance Status</TableHeaderCell>
                <TableHeaderCell>Recovery Targets</TableHeaderCell>
                <TableHeaderCell>Disruption Loss</TableHeaderCell>
                <TableHeaderCell>Requester &amp; Date</TableHeaderCell>
                <TableHeaderCell>Approver &amp; Date</TableHeaderCell>
                <TableHeaderCell className="text-right">Actions</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {bias.map((b) => {
                const isDraft = b.status === 'DRAFT';
                const isActive = b.status === 'ACTIVE';
                const isSuperseded = b.status === 'SUPERSEDED';

                return (
                  <TableRow key={b.id} className={isActive ? 'bg-indigo-950/20' : ''}>
                    <TableCell className="font-mono font-bold text-slate-200">
                      v{b.version}
                    </TableCell>

                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        {getStatusBadge(b.status)}
                        {(isActive || isSuperseded) && (
                          <span title="Immutable Baseline (Tamper Protected)">
                            <Lock className="h-3.5 w-3.5 text-slate-400" />
                          </span>
                        )}
                      </div>
                    </TableCell>

                    <TableCell className="text-xs font-mono">
                      <div>RTO: <span className="font-semibold text-slate-200">{b.rto_hours}h</span> | RPO: {b.rpo_hours}h</div>
                      <div className="text-slate-400 text-[11px]">MTD: {b.mtd_hours}h</div>
                    </TableCell>

                    <TableCell className="text-xs font-mono">
                      <div className="text-slate-200 font-semibold">${b.hourly_downtime_cost.toLocaleString()}/hr</div>
                      <div className="text-[11px] text-slate-400">Fixed: ${b.fixed_outage_cost.toLocaleString()}</div>
                    </TableCell>

                    <TableCell className="text-xs">
                      <div className="text-slate-300 font-medium">{b.requested_by?.full_name || `User #${b.requested_by_id}`}</div>
                      <div className="text-[10px] text-slate-500 font-mono">
                        {new Date(b.created_at).toLocaleDateString()}
                      </div>
                    </TableCell>

                    <TableCell className="text-xs">
                      {b.approved_by_id ? (
                        <>
                          <div className="text-emerald-400 font-medium flex items-center gap-1">
                            <ShieldCheck size={12} />
                            {b.approved_by?.full_name || `User #${b.approved_by_id}`}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            {b.approved_at ? new Date(b.approved_at).toLocaleDateString() : 'N/A'}
                          </div>
                        </>
                      ) : (
                        <span className="text-slate-500 italic text-[11px]">Pending Four-Eyes Approval</span>
                      )}
                    </TableCell>

                    <TableCell className="text-right">
                      {isDraft ? (
                        <div className="flex items-center justify-end gap-1.5">
                          {canManage && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => onEditClick(b)}
                              className="text-xs py-1 px-2"
                            >
                              <Edit2 size={12} className="mr-1" /> Edit
                            </Button>
                          )}

                          {canApprove && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => onApproveClick(b)}
                              className="text-xs py-1 px-2 bg-emerald-600 hover:bg-emerald-500"
                            >
                              <ShieldCheck size={12} className="mr-1" /> Approve
                            </Button>
                          )}

                          {canManage && (
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => archiveMutation.mutate(b.id)}
                              disabled={archiveMutation.isPending}
                              className="text-xs py-1 px-2"
                            >
                              <Archive size={12} />
                            </Button>
                          )}
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-1 text-[11px] text-slate-500 font-mono">
                          <Lock size={12} />
                          <span>Locked</span>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  );
};
