import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { createVoice } from "@/api/voices";
import { useVoiceStore } from "@/stores/voice-store";
import { fetchVoices } from "@/api/voices";
import { LANGUAGES } from "@/lib/constants";

export function VoiceCreateDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("Spanish");
  const [autoTranscribe, setAutoTranscribe] = useState(true);
  const [transcript, setTranscript] = useState("");
  const [tags, setTags] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const setAvailableVoices = useVoiceStore((s) => s.setAvailableVoices);

  const handleSubmit = async () => {
    if (!name.trim() || !file) {
      setError("Nombre y audio son requeridos");
      return;
    }

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("name", name.trim());
    formData.append("language", language);
    formData.append("auto_transcribe", String(autoTranscribe));
    formData.append("transcript", transcript);
    formData.append("style_tags", tags);
    formData.append("audio", file);

    try {
      await createVoice(formData);
      // Reload voices
      const voices = await fetchVoices();
      setAvailableVoices(voices.qwen_speakers, voices.cloned_voices);
      setOpen(false);
      setName("");
      setFile(null);
      setTranscript("");
      setTags("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al crear voz");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus className="h-3.5 w-3.5 mr-1" />
          Crear voz
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Crear perfil de voz</DialogTitle>
          <DialogDescription>Sube un audio de referencia para clonar una voz.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <div className="space-y-1.5">
            <Label>Nombre</Label>
            <Input placeholder="Nombre de la voz" value={name} onChange={(e) => setName(e.target.value)} />
          </div>

          <div className="space-y-1.5">
            <Label>Audio de referencia</Label>
            <Input
              type="file"
              accept="audio/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Idioma</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGES.map((l) => (
                  <SelectItem key={l} value={l}>{l}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto-transcribe"
              checked={autoTranscribe}
              onChange={(e) => setAutoTranscribe(e.target.checked)}
              className="rounded border-border"
            />
            <Label htmlFor="auto-transcribe">Auto-transcribir con ASR</Label>
          </div>

          {!autoTranscribe && (
            <div className="space-y-1.5">
              <Label>Transcripcion manual</Label>
              <Textarea
                placeholder="Texto exacto del audio..."
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
              />
            </div>
          )}

          <div className="space-y-1.5">
            <Label>Tags de estilo (separados por coma)</Label>
            <Input placeholder="formal, calido, joven" value={tags} onChange={(e) => setTags(e.target.value)} />
          </div>

          {error && <p className="text-xs text-danger">{error}</p>}

          <Button className="w-full" onClick={handleSubmit} disabled={loading}>
            {loading ? "Creando..." : "Crear voz"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
