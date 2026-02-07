import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectSeparator, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useVoiceStore } from "@/stores/voice-store";

export function SingleVoiceSelector() {
  const { selectedVoice, qwenSpeakers, clonedVoices, setSelectedVoice } = useVoiceStore();

  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-text-secondary">Voz</label>
      <Select value={selectedVoice} onValueChange={setSelectedVoice}>
        <SelectTrigger>
          <SelectValue placeholder="Selecciona una voz" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Qwen Speakers</SelectLabel>
            {qwenSpeakers.map((s) => (
              <SelectItem key={`qwen-${s}`} value={`qwen:${s}`}>
                {s}
              </SelectItem>
            ))}
          </SelectGroup>
          {clonedVoices.length > 0 && (
            <>
              <SelectSeparator />
              <SelectGroup>
                <SelectLabel>Voces Clonadas</SelectLabel>
                {clonedVoices.map((v) => (
                  <SelectItem key={`clone-${v.name}`} value={`clone:${v.name}`}>
                    {v.name} ({v.language})
                  </SelectItem>
                ))}
              </SelectGroup>
            </>
          )}
        </SelectContent>
      </Select>
    </div>
  );
}
