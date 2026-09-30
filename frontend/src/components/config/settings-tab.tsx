"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSaveSettings, useSettings } from "@/lib/api/config";

export function SettingsTab() {
  const settings = useSettings();
  const save = useSaveSettings();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    save.mutate(
      {
        entry_time_kitchen: String(form.get("entry_time_kitchen")),
        entry_time_other: String(form.get("entry_time_other")),
        tolerance_minutes: Number(form.get("tolerance_minutes")),
      },
      { onSuccess: () => toast.success("Horario guardado") },
    );
  }

  if (settings.isPending) return <Loading />;
  if (settings.isError) return <QueryError error={settings.error} onRetry={() => settings.refetch()} />;
  return (
    <form onSubmit={onSubmit} className="grid max-w-md gap-3">
      <div className="space-y-1">
        <Label htmlFor="entry_time_kitchen">Entrada cocina</Label>
        <Input id="entry_time_kitchen" name="entry_time_kitchen" type="time" required defaultValue={settings.data.entry_time_kitchen} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="entry_time_other">Entrada barra / servicio</Label>
        <Input id="entry_time_other" name="entry_time_other" type="time" required defaultValue={settings.data.entry_time_other} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="tolerance_minutes">Tolerancia (minutos)</Label>
        <Input
          id="tolerance_minutes"
          name="tolerance_minutes"
          type="number"
          min={0}
          max={60}
          required
          defaultValue={settings.data.tolerance_minutes}
        />
      </div>
      <FormError error={save.error} />
      <Button type="submit" disabled={save.isPending}>
        Guardar horario
      </Button>
    </form>
  );
}
