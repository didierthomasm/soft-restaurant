"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useReviewSettings, useSaveReviewSettings } from "@/lib/api/reviews";

const FIELDS = [
  { name: "streak_days", label: "Días seguidos sin checar para marcar una racha", max: 7 },
  { name: "late_week", label: "Retardos sin justificar en la semana para marcar retardos repetidos", max: 7 },
  { name: "late_weeks", label: "Semanas con retardo (de las últimas 5) para marcar retardos repetidos", max: 5 },
] as const;

export function ReviewSettingsTab() {
  const settings = useReviewSettings();
  const save = useSaveReviewSettings();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    save.mutate(
      {
        streak_days: Number(form.get("streak_days")),
        late_week: Number(form.get("late_week")),
        late_weeks: Number(form.get("late_weeks")),
      },
      { onSuccess: () => toast.success("Umbrales guardados") },
    );
  }

  if (settings.isPending) return <Loading />;
  if (settings.isError) return <QueryError error={settings.error} onRetry={() => settings.refetch()} />;
  return (
    <form onSubmit={onSubmit} className="grid max-w-md gap-3">
      <p className="text-sm text-muted-foreground">
        Cuándo el borrador semanal marca un hallazgo. Aplican al siguiente borrador que se genere.
      </p>
      {FIELDS.map((field) => (
        <div key={field.name} className="space-y-1">
          <Label htmlFor={field.name}>{field.label}</Label>
          <Input
            id={field.name}
            name={field.name}
            type="number"
            min={1}
            max={field.max}
            required
            defaultValue={settings.data[field.name]}
          />
        </div>
      ))}
      <FormError error={save.error} />
      <Button type="submit" disabled={save.isPending}>
        Guardar umbrales
      </Button>
    </form>
  );
}
