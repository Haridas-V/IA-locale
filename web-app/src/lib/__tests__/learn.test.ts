import { describe, expect, it } from 'vitest'
import {
  LIMITES_PAR_DEFAUT,
  apprendre,
  extraireTexte,
  extraireUrlsResultats,
  rechercherUrls,
  resumer,
} from '../learn'

describe('extraireTexte', () => {
  it('supprime scripts, styles et balises', () => {
    const html =
      '<html><head><title>Ma page</title><style>body{color:red}</style></head>' +
      '<body><script>var x=1;</script><h1>Titre</h1><p>Bonjour &amp; bienvenue</p></body></html>'
    const { texte, titre } = extraireTexte(html)
    expect(titre).toBe('Ma page')
    expect(texte).toContain('Bonjour & bienvenue')
    expect(texte).toContain('Titre')
    expect(texte).not.toContain('var x=1')
    expect(texte).not.toContain('color:red')
    expect(texte).not.toContain('<p>')
  })
})

describe('extraireUrlsResultats', () => {
  it('extrait les liens uddg= de DuckDuckGo et les liens directs, exclut les moteurs', () => {
    const html = [
      '<a rel="nofollow" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexemple.org%2Fa&rut=xyz">A</a>',
      '<a href="https://exemple.org/b">B</a>',
      '<a href="https://www.bing.com/search?q=x">bing</a>',
    ].join('')
    const urls = extraireUrlsResultats(html, 10)
    expect(urls).toContain('https://exemple.org/a')
    expect(urls).toContain('https://exemple.org/b')
    expect(urls.some((u) => u.includes('bing.com'))).toBe(false)
  })

  it('respecte maxUrls', () => {
    const html = Array.from({ length: 8 }, (_, i) => `<a href="https://e.org/${i}">x</a>`).join('')
    expect(extraireUrlsResultats(html, 3)).toHaveLength(3)
  })
})

describe('rechercherUrls', () => {
  it('essaie les moteurs dans l\'ordre et retourne les URL trouvées', async () => {
    const fetchImpl = async (url: string) => {
      if (url.includes('html.duckduckgo.com')) throw new Error('bloqué')
      return '<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexemple.org%2Fpage">ok</a>'
    }
    const urls = await rechercherUrls('sujet test', 5, fetchImpl)
    expect(urls).toEqual(['https://exemple.org/page'])
  })

  it('retourne [] si tous les moteurs échouent', async () => {
    const fetchImpl = async () => {
      throw new Error('offline')
    }
    expect(await rechercherUrls('x', 5, fetchImpl)).toEqual([])
  })
})

describe('resumer', () => {
  it('tronque strictement à la limite', () => {
    const sources = Array.from({ length: 10 }, (_, i) => ({
      url: `https://e.org/${i}`,
      titre: `S${i}`,
      extrait: 'mot '.repeat(500),
    }))
    const r = resumer('sujet', sources, 300)
    expect(r.length).toBeLessThanOrEqual(300)
    expect(r).toContain('tronqué')
  })
})

describe('apprendre (limites)', () => {
  it('respecte maxPages, max par page, max total et limite du résumé', async () => {
    const pages: Record<string, string> = {
      'https://e.org/p1': '<html><head><title>P1</title></head><body><p>' + 'alpha '.repeat(500) + '</p></body></html>',
      'https://e.org/p2': '<html><body><p>' + 'beta '.repeat(500) + '</p></body></html>',
      'https://e.org/p3': '<html><body><p>' + 'gamma '.repeat(500) + '</p></body></html>',
      'https://e.org/p4': '<html><body><p>' + 'delta '.repeat(500) + '</p></body></html>',
    }
    const fetchImpl = async (url: string) => {
      if (pages[url]) return pages[url]
      throw new Error('404')
    }
    const limites = { ...LIMITES_PAR_DEFAUT, maxPages: 2, maxCaracteresPage: 500, maxTotal: 800, limiteResume: 300, delaiS: 2 }
    const r = await apprendre('sujet test', Object.keys(pages), limites, undefined, fetchImpl)
    expect(r.sources).toHaveLength(2)
    expect(r.sources.reduce((n, s) => n + s.extrait.length, 0)).toBeLessThanOrEqual(800)
    for (const s of r.sources) expect(s.extrait.length).toBeLessThanOrEqual(500)
    expect(r.resume.length).toBeLessThanOrEqual(300)
    expect(r.sources[0].titre).toBe('P1')
  })

  it('ignore les pages en échec', async () => {
    const fetchImpl = async (url: string) => {
      if (url.includes('ok')) return '<html><body><p>contenu</p></body></html>'
      throw new Error('down')
    }
    const r = await apprendre('s', ['https://x/down', 'https://x/ok'], { ...LIMITES_PAR_DEFAUT, delaiS: 2 }, undefined, fetchImpl)
    expect(r.sources).toHaveLength(1)
    expect(r.sources[0].url).toBe('https://x/ok')
  })
})
