import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';

interface PlaceholderProps {
  title: string;
  phase: string;
  description: string;
  workflowStep: string;
  upcomingFeatures: string[];
}

export const PlaceholderModulePage: React.FC<PlaceholderProps> = ({
  title,
  phase,
  description,
  workflowStep,
  upcomingFeatures,
}) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">{title}</h1>
            <Badge variant="purple">{phase}</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">{description}</p>
        </div>

        <Link to="/dashboard">
          <Button size="sm" variant="outline">
            Back to Dashboard
          </Button>
        </Link>
      </div>

      <Card className="border-l-2 border-l-indigo-500">
        <CardHeader
          title="Workflow Architecture Position"
          subtitle={`This component represents the "${workflowStep}" stage of the ControlSphere GRC pipeline.`}
        />

        <div className="space-y-4">
          <p className="text-xs text-slate-300 leading-relaxed">
            In accordance with the ControlSphere Master Engineering Directive, foundation security and database isolation are established first in Phase 1 before building out domain-specific GRC engines.
          </p>

          <div className="p-4 rounded bg-slate-950/70 border border-slate-800">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Planned Deliverables for {title} ({phase}):
            </h4>
            <ul className="space-y-2">
              {upcomingFeatures.map((feat, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                  <CheckCircle2 size={14} className="text-indigo-400 shrink-0 mt-0.5" />
                  <span>{feat}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
};