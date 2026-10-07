/**
 * Estimation du nombre de tokens — version accent-aware.
 * Ratio 3.5 chars/token pour les textes à >2% de caractères accentués (FR),
 * 4.0 pour les textes à dominante ASCII (EN, code).
 * Source unique partagée entre ChatView et OptimiseurView.
 */
export function estimateTokens(text) {
  if (!text) return 0
  const accented = (text.match(/[éàùçèêîïôûüœæÉÀÙÇÈÊÎÏÔÛÜŒÆ]/g) || []).length
  const ratio = accented / text.length > 0.02 ? 3.5 : 4.0
  return Math.floor(text.length / ratio)
}
