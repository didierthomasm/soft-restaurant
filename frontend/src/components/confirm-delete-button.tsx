"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

type Props = {
  onConfirm: () => void;
  /** Accessible name of the initial button, ideally identifying the row. */
  label?: string;
  pending?: boolean;
};

/** Two-step inline delete: "Eliminar" first, then "Confirmar" / "Cancelar". */
export function ConfirmDeleteButton({ onConfirm, label = "Eliminar", pending = false }: Props) {
  const [confirming, setConfirming] = useState(false);
  const subject = label.replace(/^Eliminar\s*/, "");

  if (!confirming) {
    return (
      <Button size="sm" variant="ghost" aria-label={label} onClick={() => setConfirming(true)}>
        Eliminar
      </Button>
    );
  }
  return (
    <span className="inline-flex gap-1">
      <Button
        size="sm"
        variant="destructive"
        disabled={pending}
        aria-label={`Confirmar eliminar ${subject}`.trim()}
        onClick={() => {
          setConfirming(false);
          onConfirm();
        }}
      >
        Confirmar
      </Button>
      <Button
        size="sm"
        variant="ghost"
        aria-label={`Cancelar eliminar ${subject}`.trim()}
        onClick={() => setConfirming(false)}
      >
        Cancelar
      </Button>
    </span>
  );
}
