import type {
    algobattle_web__models__Documentation__Schema,
    algobattle_web__models__File__Schema,
    algobattle_web__models__Problem__Schema,
    algobattle_web__models__Program__Schema,
    algobattle_web__models__ScheduledMatch__Schema,
    algobattle_web__models__Team__Schema,
    algobattle_web__models__Tournament__Schema,
    algobattle_web__models__UserSettings__Schema,
    algobattle_web__models__User__Schema,
} from "../typescript_client";

export type Documentation = algobattle_web__models__Documentation__Schema
export type DbFile = algobattle_web__models__File__Schema
export type Program = algobattle_web__models__Program__Schema
export type ScheduledMatch = algobattle_web__models__ScheduledMatch__Schema
export type Team = algobattle_web__models__Team__Schema
export type Tournament = algobattle_web__models__Tournament__Schema
export type User = algobattle_web__models__User__Schema
export type UserSettings = algobattle_web__models__UserSettings__Schema
export type Problem = algobattle_web__models__Problem__Schema

export type ModelDict<T> = {[key: string]: T}
export interface InputFileEvent extends InputEvent {
  target: HTMLInputElement;
}

export interface DbFileLoc extends DbFile{
    location: string,
}
