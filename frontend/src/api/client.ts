import axios, { AxiosError } from "axios";
import type { ApiErrorBody } from "./types";

export const apiClient = axios.create({
  baseURL: "http://localhost:8000",
  withCredentials: true,
});

/** Extracts the backend's `{ detail: string }` message, falling back to a generic one. */
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const e = err as AxiosError<ApiErrorBody>;
    const detail = e.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (e.message) return e.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong. Please try again.";
}
