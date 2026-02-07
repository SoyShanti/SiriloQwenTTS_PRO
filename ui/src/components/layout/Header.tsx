import { useEffect } from "react";
import { Cpu, Zap, ZapOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAppStore } from "@/stores/app-store";
import { fetchStatus } from "@/api/system";
import { unloadModels } from "@/api/system";
import { LANGUAGES } from "@/lib/constants";

export function Header() {
  const { language, modelVersion, gpuAvailable, modelLoaded, currentModel, setLanguage, setModelVersion, setGpuStatus } =
    useAppStore();

  useEffect(() => {
    const poll = () =>
      fetchStatus()
        .then((s) => setGpuStatus(s.gpu_available, s.model_loaded, s.current_model))
        .catch(() => {});
    poll();
    const id = setInterval(poll, 10_000);
    return () => clearInterval(id);
  }, [setGpuStatus]);

  const handleUnload = async () => {
    await unloadModels();
    setGpuStatus(gpuAvailable, false, null);
  };

  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-3">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-text-primary tracking-tight">SiriloQwenTTS</h1>
        <span className="text-xs font-medium text-brand bg-brand/10 px-2 py-0.5 rounded-full">PRO</span>
      </div>

      <div className="flex items-center gap-3">
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="w-32 h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LANGUAGES.map((l) => (
              <SelectItem key={l} value={l}>{l}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={modelVersion} onValueChange={setModelVersion}>
          <SelectTrigger className="w-36 h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {["0.6B", "1.7B", "1.7B-Base", "1.7B-VoiceDesign"].map((m) => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <Cpu className="h-3.5 w-3.5" />
          {gpuAvailable ? (
            <span className="text-success">GPU</span>
          ) : (
            <span className="text-danger">No GPU</span>
          )}
          {modelLoaded && currentModel && (
            <span className="text-text-secondary ml-1">({currentModel})</span>
          )}
        </div>

        {modelLoaded && (
          <Button variant="ghost" size="sm" onClick={handleUnload} title="Liberar GPU">
            {modelLoaded ? <ZapOff className="h-3.5 w-3.5" /> : <Zap className="h-3.5 w-3.5" />}
          </Button>
        )}
      </div>
    </header>
  );
}
