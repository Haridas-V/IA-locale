import { fetch } from '@tauri-apps/plugin-http'
import { load } from '@tauri-apps/plugin-store'

export interface LimitesApprentissage {
  maxPages: number
  maxCaracteresPage: number
  maxTotal: number
  limiteResume: number // limite de paramètres à la fin du learn
  delaiS: number
}

export const LIMITES_PAR_DEFAUT: LimitesApprentissage = {
  maxPages: 5,
  maxCaracteresPage: 20000,
  maxTotal: 100000,
  limiteResume: 4000,
  delaiS: 15,
}

export interface SourceApprise {
  url: string
  titre: string
  extrait: string
}

export interface ResultatApprentissage {
  sujet: string
  date: string
  sources: SourceApprise[]
  resume: string
}

type FetchImpl = (url: string, delaiS: number) => Promise<string>

const MOTEURS_RECHERCHE = [
  'https://html.duckduckgo.com/html/?q={q}',
  'https://lite.duckduckgo.com/lite/?q={q}',
  'https://www.bing.com/search?q={q}&count=20',
]
const HOTES_EXCLUS = ['duckduckgo.com', 'bing.com', 'microsoft.com', 'msn.com', 'live.com']

/** Extrait le texte lisible d'une page HTML (sans DOM requis, testable partout). */
export function extraireTexte(html: string): { texte: string; titre: string } {
  const titre = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(html)?.[1]?.trim() ?? ''
  let t = html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ')
    .replace(/<head[\s\S]*?<\/head>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
  t = t
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/[ \t]+/g, ' ')
    .replace(/\n\s*\n+/g, '\n\n')
  return { texte: t.trim(), titre }
}

/** Extrait les URLs utiles d'une page de résultats (gère les redirections uddg= de DuckDuckGo). */
export function extraireUrlsResultats(html: string, maxUrls: number): string[] {
  const urls: string[] = []
  const hrefs = html.match(/href="([^"]+)"/g) ?? []
  for (const h of hrefs) {
    const href = h.slice(6, -1)
    let cible = href
    const m = /[?&]uddg=([^&]+)/.exec(href)
    if (m) cible = decodeURIComponent(m[1])
    if (cible.startsWith('//')) cible = 'https:' + cible
    if (!cible.startsWith('http')) continue
    if (HOTES_EXCLUS.some((hote) => cible.includes(hote))) continue
    if (!urls.includes(cible)) urls.push(cible)
    if (urls.length >= maxUrls) break
  }
  return urls
}

async function fetchTexte(url: string, delaiS: number): Promise<string> {
  const res = await fetch(url, {
    method: 'GET',
    signal: AbortSignal.timeout(delaiS * 1000),
    headers: { 'User-Agent': 'IA-Locale/1.0 (apprentissage local; lecture seule)' },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.text()
}

/** Recherche d'URLs via plusieurs moteurs (DDG html/lite, Bing). */
export async function rechercherUrls(
  sujet: string,
  maxUrls: number,
  fetchImpl: FetchImpl = fetchTexte
): Promise<string[]> {
  const q = encodeURIComponent(sujet)
  for (const template of MOTEURS_RECHERCHE) {
    try {
      const html = await fetchImpl(template.replace('{q}', q), 15)
      const urls = extraireUrlsResultats(html, maxUrls)
      if (urls.length > 0) return urls
    } catch {
      // moteur suivant
    }
  }
  return []
}

/**
 * Lance un apprentissage : recherche (ou URLs fournies), téléchargement des pages
 * dans les limites fixées, puis résumé tronqué à `limiteResume` caractères.
 */
export async function apprendre(
  sujet: string,
  urls: string[] | undefined,
  limites: LimitesApprentissage,
  onProgression?: (i: number, n: number, url: string) => void,
  fetchImpl: FetchImpl = fetchTexte
): Promise<ResultatApprentissage> {
  let cibles = urls && urls.length > 0 ? urls : await rechercherUrls(sujet, limites.maxPages, fetchImpl)
  cibles = cibles.slice(0, limites.maxPages)
  const sources: SourceApprise[] = []
  let total = 0
  for (let i = 0; i < cibles.length; i++) {
    if (sources.length >= limites.maxPages || total >= limites.maxTotal) break
    onProgression?.(i + 1, cibles.length, cibles[i])
    try {
      const html = await fetchImpl(cibles[i], limites.delaiS)
      const { texte, titre } = extraireTexte(html)
      const reste = limites.maxTotal - total
      const extrait = texte.slice(0, Math.min(limites.maxCaracteresPage, Math.max(0, reste)))
      total += extrait.length
      sources.push({ url: cibles[i], titre: titre || cibles[i], extrait })
    } catch {
      onProgression?.(i + 1, cibles.length, `[échec] ${cibles[i]}`)
    }
  }
  const resume = resumer(sujet, sources, limites.limiteResume)
  return { sujet, date: new Date().toISOString(), sources, resume }
}

/** Résumé final strictement limité à `limite` caractères (limite de paramètres du learn). */
export function resumer(sujet: string, sources: SourceApprise[], limite: number): string {
  const morceaux = [`Sujet : ${sujet}`]
  for (const s of sources) morceaux.push(`Source : ${s.titre} (${s.url})\n${s.extrait}`)
  let texte = morceaux.join('\n\n---\n\n')
  const suffixe = '\n… [tronqué à la limite fixée]'
  if (texte.length > limite) texte = texte.slice(0, Math.max(0, limite - suffixe.length)) + suffixe
  return texte
}

const LEARN_STORE = 'ia-locale-apprentissages.json'

export async function sauvegarderDernierResume(resume: string): Promise<void> {
  const store = await load(LEARN_STORE, { autoSave: false })
  await store.set('dernier', { resume, date: new Date().toISOString() })
  await store.save()
}

export async function dernierResume(): Promise<string | null> {
  try {
    const store = await load(LEARN_STORE, { autoSave: false })
    const v = await store.get<{ resume: string }>('dernier')
    return v?.resume ?? null
  } catch {
    return null
  }
}
