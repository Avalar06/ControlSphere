import React from 'react';
import { FileText, Download, Hash } from 'lucide-react';
import { executiveService } from '../../lib/executiveService';
import type { ExecutiveExportArtifact } from '../../types';

interface ExportArtifactCardProps {
  artifact: ExecutiveExportArtifact;
}

export const ExportArtifactCard: React.FC<ExportArtifactCardProps> = ({ artifact }) => {
  const [downloading, setDownloading] = React.useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await executiveService.downloadExport(artifact.id, artifact.original_filename);
    } catch (err) {
      console.error('Failed to download artifact:', err);
    } finally {
      setDownloading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between hover:border-indigo-500/50 transition-colors">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white truncate max-w-[200px] sm:max-w-xs">
                {artifact.original_filename}
              </h4>
              <span className="text-[11px] text-slate-400">
                Format: <span className="font-semibold text-slate-600 dark:text-slate-300">{artifact.export_format}</span> • {formatFileSize(artifact.file_size_bytes)}
              </span>
            </div>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 uppercase">
            {artifact.artifact_type.replace('_', ' ')}
          </span>
        </div>

        <div className="mt-3 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 font-mono flex items-center gap-1.5 truncate">
          <Hash className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="truncate">SHA-256: {artifact.sha256_checksum}</span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-400">
        <span>{new Date(artifact.generated_at).toLocaleString()}</span>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-sm disabled:opacity-50"
        >
          <Download className="h-3.5 w-3.5" />
          {downloading ? 'Downloading...' : 'Download'}
        </button>
      </div>
    </div>
  );
};
