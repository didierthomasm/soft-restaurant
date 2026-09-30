"use client";

import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useImportEmployees, useSrPreview } from "@/lib/api/config";

export function ImportDialog() {
  const [open, setOpen] = useState(false);
  const preview = useSrPreview(open);
  const importer = useImportEmployees();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const ids = new FormData(event.currentTarget).getAll("sr_id").map(Number);
    if (ids.length === 0) return;
    importer.mutate(ids, {
      onSuccess: (created) => {
        toast.success(`Importados: ${created.length}`);
        setOpen(false);
      },
    });
  }

  const pending = preview.data?.filter((e) => !e.imported) ?? [];
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">Importar de SoftRestaurant</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Importar empleados</DialogTitle>
          <DialogDescription>Empleados de SoftRestaurant que aún no están aquí.</DialogDescription>
        </DialogHeader>
        {preview.isPending && <Loading />}
        {preview.isError && <QueryError error={preview.error} onRetry={() => preview.refetch()} />}
        {preview.data && (
          <form id="import-form" onSubmit={onSubmit} className="space-y-2">
            {pending.length === 0 && <p className="text-sm">Todos ya están importados.</p>}
            {pending.map((employee) => (
              <label key={employee.sr_id} className="flex items-center gap-2 text-sm">
                <Checkbox name="sr_id" value={String(employee.sr_id)} defaultChecked={employee.visible} />
                {employee.sr_id} · {employee.name}
              </label>
            ))}
          </form>
        )}
        <FormError error={importer.error} />
        <DialogFooter>
          <Button type="submit" form="import-form" disabled={importer.isPending || pending.length === 0}>
            Importar seleccionados
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
