import { useMemo } from "react";
import { Header } from "@/components/layout/Header";
import { WorkflowSteps } from "@/components/layout/WorkflowSteps";
import { UniversalEditor } from "@/components/editor/UniversalEditor";
import { VoicePanel } from "@/components/voice/VoicePanel";
import { StylePanel } from "@/components/style/StylePanel";
import { GenerateButton } from "@/components/production/GenerateButton";
import { useEditorStore } from "@/stores/editor-store";
import { useVoiceStore } from "@/stores/voice-store";
import { useProductionStore } from "@/stores/production-store";

function App() {
  const content = useEditorStore((s) => s.content);
  const selectedVoice = useVoiceStore((s) => s.selectedVoice);
  const status = useProductionStore((s) => s.status);

  const activeStep = useMemo(() => {
    if (status === "running" || status === "pending") return "generate";
    if (status === "completed") return "generate";
    if (selectedVoice) return "style";
    if (content.trim()) return "voice";
    return "content";
  }, [content, selectedVoice, status]);

  return (
    <div className="flex flex-col h-screen bg-background">
      <Header />
      <WorkflowSteps activeStep={activeStep} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto p-6 space-y-4">
          <UniversalEditor />
          <VoicePanel />
          <StylePanel />
          <GenerateButton />
        </div>
      </main>
    </div>
  );
}

export default App;
