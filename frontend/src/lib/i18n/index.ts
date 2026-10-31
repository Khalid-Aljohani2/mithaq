/**
 * One dictionary per language, assembled from one file per area so that
 * areas can be edited independently. `en` is typed as `Dict`, the shape of
 * the Arabic dictionary, so a missing or extra English key is a type error.
 */

import { audit } from "./audit";
import { caseFile } from "./case";
import { common } from "./common";
import { demo } from "./demo";
import { evaluation } from "./evaluation";
import { forms } from "./forms";
import { home } from "./home";
import { limits } from "./limits";
import { shell } from "./shell";
import { vo } from "./vo";
import { workspace } from "./workspace";

export type Lang = "ar" | "en";

export const ar = {
  common: common.ar,
  shell: shell.ar,
  home: home.ar,
  demo: demo.ar,
  workspace: workspace.ar,
  case: caseFile.ar,
  limits: limits.ar,
  vo: vo.ar,
  audit: audit.ar,
  evaluation: evaluation.ar,
  forms: forms.ar,
};

export type Dict = typeof ar;

export const en: Dict = {
  common: common.en,
  shell: shell.en,
  home: home.en,
  demo: demo.en,
  workspace: workspace.en,
  case: caseFile.en,
  limits: limits.en,
  vo: vo.en,
  audit: audit.en,
  evaluation: evaluation.en,
  forms: forms.en,
};

export const DICTS: Record<Lang, Dict> = { ar, en };
