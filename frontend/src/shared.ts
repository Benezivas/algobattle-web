import { reactive } from "vue";
import type { UserLogin, Team, Tournament, ServerSettings } from "@client";
import { DateTime } from "luxon";

export type ModelDict<T> = { [key: string]: T };

export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

export function formatDateTime(datetime: string): string {
  return DateTime.fromISO(datetime).toLocaleString(DateTime.DATETIME_SHORT);
}

export const store = reactive<{
  user: UserLogin | null;
  team: Team | "admin" | null;
  tournament: Tournament | null;
  serverSettings?: ServerSettings;
}>({
  user: null,
  team: null,
  tournament: null,
});
