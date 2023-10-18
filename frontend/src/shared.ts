import { reactive } from "vue";
import type { UserLogin, Team, Tournament } from "@client";

export type ModelDict<T> = { [key: string]: T };

export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

export function formatDateTime(datetime: string): string {
  return new Date(datetime).toLocaleString();
}

export const store = reactive<{
  user: UserLogin | null;
  team: Team | "admin" | null;
  tournament: Tournament | null;
}>({
  user: null,
  team: null,
  tournament: null,
});
