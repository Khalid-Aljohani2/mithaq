/**
 * Where the project's own documents live, so a published number can link to
 * the reasoning behind it at the exact commit it came from.
 */
export const REPO_URL = "https://github.com/Khalid-Aljohani2/mithaq";

export function docAt(commit: string | undefined, file: string): string {
  return `${REPO_URL}/blob/${commit || "main"}/${file}`;
}
