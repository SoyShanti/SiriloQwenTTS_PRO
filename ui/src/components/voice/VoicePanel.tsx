import { useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { SingleVoiceSelector } from "./SingleVoiceSelector";
import { PodcastVoiceMapper } from "./PodcastVoiceMapper";
import { VoiceCreateDialog } from "./VoiceCreateDialog";
import { useEditorStore } from "@/stores/editor-store";
import { useVoiceStore } from "@/stores/voice-store";
import { fetchVoices } from "@/api/voices";

export function VoicePanel() {
  const format = useEditorStore((s) => s.format);
  const setAvailableVoices = useVoiceStore((s) => s.setAvailableVoices);

  // Load available voices on mount
  useEffect(() => {
    fetchVoices()
      .then((data) => setAvailableVoices(data.qwen_speakers, data.cloned_voices))
      .catch(() => {});
  }, [setAvailableVoices]);

  const isPodcast = format === "podcast_script";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Voz</CardTitle>
          <VoiceCreateDialog />
        </div>
      </CardHeader>
      <CardContent>
        {isPodcast ? <PodcastVoiceMapper /> : <SingleVoiceSelector />}
      </CardContent>
    </Card>
  );
}
