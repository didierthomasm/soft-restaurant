"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { EmployeesTab } from "./employees-tab";
import { ExceptionsTab } from "./exceptions-tab";
import { RestRulesTab } from "./rest-rules-tab";
import { ReviewSettingsTab } from "./review-settings-tab";
import { SettingsTab } from "./settings-tab";

export function ConfigView() {
  return (
    <Tabs defaultValue="employees" className="space-y-4">
      <TabsList>
        <TabsTrigger value="employees">Empleados</TabsTrigger>
        <TabsTrigger value="rest">Descansos</TabsTrigger>
        <TabsTrigger value="exceptions">Excepciones y cierres</TabsTrigger>
        <TabsTrigger value="settings">Horario</TabsTrigger>
        <TabsTrigger value="review">Revisión semanal</TabsTrigger>
      </TabsList>
      <TabsContent value="employees">
        <EmployeesTab />
      </TabsContent>
      <TabsContent value="rest">
        <RestRulesTab />
      </TabsContent>
      <TabsContent value="exceptions">
        <ExceptionsTab />
      </TabsContent>
      <TabsContent value="settings">
        <SettingsTab />
      </TabsContent>
      <TabsContent value="review">
        <ReviewSettingsTab />
      </TabsContent>
    </Tabs>
  );
}
