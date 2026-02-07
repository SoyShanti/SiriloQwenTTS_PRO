import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useStyleStore } from "@/stores/style-store";

export function PresetSelector() {
  const { preset, presets, setPreset, setComputedInstruct, setSelectedModality } = useStyleStore();

  const handleChange = (value: string) => {
    setPreset(value);
    setSelectedModality(null);
    if (value !== "(custom)") {
      const found = presets.find((p) => p.name === value);
      if (found) setComputedInstruct(found.instruct);
    }
  };

  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-text-secondary">Preset</label>
      <Select value={preset} onValueChange={handleChange}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="(custom)">(custom)</SelectItem>
          {presets.map((p) => (
            <SelectItem key={p.name} value={p.name}>
              {p.name} — {p.description}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
