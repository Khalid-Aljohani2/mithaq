/**
 * The inline <head> script for display preferences. Kept out of the client
 * module so the server layout can import it as a plain string.
 */

export const THEME_KEY = "mithaqai.theme";
export const LANG_KEY = "mithaqai.lang";

/**
 * Sets data-theme only when the viewer chose one, so the default keeps
 * following the system; sets lang and dir from the stored language, and hides
 * the page until React has rendered English, so neither flashes on load.
 */
export const PREFS_SCRIPT = `(function(){var d=document.documentElement;try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")d.setAttribute("data-theme",t);var l=localStorage.getItem("${LANG_KEY}");if(l==="en"){d.lang="en";d.dir="ltr";d.setAttribute("data-lang-pending","")}}catch(e){}})();`;
