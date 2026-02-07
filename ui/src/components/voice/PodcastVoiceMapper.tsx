import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectSeparator, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useEditorStore } from "@/stores/editor-store";
import { useVoiceStore } from "@/stores/voice-store";

export function PodcastVoiceMapper() {
  const speakers = useEditorStore((s) => s.detectedSpeakers);
  const { speakerVoiceMap, qwenSpeakers, clonedVoices, setSpeakerVoice } = useVoiceStore();

  if (speakers.length === 0) {
    return <p className="text-sm text-text-muted">No se detectaron speakers en el script.</p>;
  }

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-text-secondary">Asignar voces a speakers</label>
      {speakers.map((speaker) => (
        <div key={speaker} className="flex items-center gap-3">
          <span className="text-sm font-medium text-text-primary w-24 truncate">{speaker}</span>
          <Select
            value={speakerVoiceMap[speaker] ?? ""}
            onValueChange={(v) => setSpeakerVoice(speaker, v)}
          >
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Selecciona voz" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectLabel>Qwen</SelectLabel>
                {qwenSpeakers.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectGroup>
              {clonedVoices.length > 0 && (
                <>
                  <SelectSeparator />
                  <SelectGroup>
                    <SelectLabel>Clonadas</SelectLabel>
                    {clonedVoices.map((v) => (
                      <SelectItem key={v.name} value={v.name}>{v.name}</SelectItem>
                    ))}
                  </SelectGroup>
                </>
              )}
            </SelectContent>
          </Select>
        </div>
      ))}
    </div>
  );
}
