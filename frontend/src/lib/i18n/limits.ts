/**
 * limits strings. Arabic is the source; English must carry exactly the same
 * keys, which the `typeof ar` annotation enforces.
 */

const ar = {};

const en: typeof ar = {};

export const limits = { ar, en };
