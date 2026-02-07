import { FileText, Mic, Palette, Play } from "lucide-react";
import { cn } from "@/lib/utils";

const icons = { FileText, Mic, Palette, Play };

const STEPS = [
  { id: "content", label: "Contenido", icon: "FileText" },
  { id: "voice", label: "Voz", icon: "Mic" },
  { id: "style", label: "Estilo", icon: "Palette" },
  { id: "generate", label: "Generar", icon: "Play" },
] as const;

interface WorkflowStepsProps {
  activeStep: string;
}

export function WorkflowSteps({ activeStep }: WorkflowStepsProps) {
  const activeIdx = STEPS.findIndex((s) => s.id === activeStep);

  return (
    <div className="flex items-center gap-1 px-6 py-3 border-b border-border overflow-x-auto">
      {STEPS.map((step, i) => {
        const Icon = icons[step.icon as keyof typeof icons];
        const isActive = step.id === activeStep;
        const isPast = i < activeIdx;

        return (
          <div key={step.id} className="flex items-center gap-1">
            {i > 0 && <div className={cn("w-8 h-px", isPast || isActive ? "bg-brand" : "bg-border")} />}
            <div
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors",
                isActive && "bg-brand/15 text-brand",
                isPast && "text-success",
                !isActive && !isPast && "text-text-muted",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{step.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
