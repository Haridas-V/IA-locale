import { useState } from 'react'
import { useTranslation } from '@/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { IconBook, IconPlayerPlay, IconTrash, IconQuestionMark } from '@tabler/icons-react'
import {
  LIMITES_PAR_DEFAUT,
  apprendre,
  dernierResume,
  sauvegarderDernierResume,
  type LimitesApprentissage,
  type ResultatApprentissage,
} from '@/lib/learn'
import { useLearnStore } from '@/stores/learn-store'

export default function LearnPanel() {
  const { t } = useTranslation()
  const setConnaissances = useLearnStore((s) => s.setConnaissances)
  const [sujet, setSujet] = useState('')
  const [urls, setUrls] = useState('')
  const [limites, setLimites] = useState<LimitesApprentissage>(LIMITES_PAR_DEFAUT)
  const [enCours, setEnCours] = useState(false)
  const [progression, setProgression] = useState('')
  const [resultat, setResultat] = useState<ResultatApprentissage | null>(null)
  const [message, setMessage] = useState('')

  const lancer = async () => {
    if (!sujet.trim() && !urls.trim()) return
    setEnCours(true)
    setResultat(null)
    setMessage('')
    try {
      const listeUrls = urls
        .split('\n')
        .map((u) => u.trim())
        .filter(Boolean)
      const r = await apprendre(
        sujet.trim() || 'apprentissage',
        listeUrls.length ? listeUrls : undefined,
        limites,
        (i, n, url) => setProgression(t('ia-locale:learn.enCours', { i, n, url: url.slice(0, 120) }))
      )
      setResultat(r)
      await sauvegarderDernierResume(r.resume)
      setProgression(
        t('ia-locale:learn.termine', {
          count: r.sources.length,
          len: r.resume.length,
          limite: limites.limiteResume,
        }) + (r.sources.length === 0 && !listeUrls.length ? ' ' + t('ia-locale:learn.aucunePage') : '')
      )
    } catch (e) {
      setProgression(t('ia-locale:learn.erreur', { message: String(e) }))
    } finally {
      setEnCours(false)
    }
  }

  const utiliser = () => {
    if (resultat) {
      setConnaissances(resultat.resume)
      setMessage(t('ia-locale:learn.enregistre'))
    }
  }

  const supprimer = async () => {
    setConnaissances(null)
    setResultat(null)
    const store = await import('@tauri-apps/plugin-store').then((m) => m.load('ia-locale-apprentissages.json', { autoSave: false }))
    await store.delete('dernier')
    await store.save()
    setMessage(t('ia-locale:learn.supprime'))
  }

  const champ = (cle: keyof LimitesApprentissage, label: string) => (
    <div key={cle}>
      <Label className="text-xs">{label}</Label>
      <Input
        type="number"
        className="mt-1"
        value={limites[cle]}
        min={1}
        onChange={(e) => setLimites({ ...limites, [cle]: Math.max(1, Number(e.target.value)) })}
      />
    </div>
  )

  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 flex-wrap">
        <IconBook className="size-5 text-primary" />
        <h3 className="font-semibold">{t('ia-locale:learn.title')}</h3>
        <span
          className="inline-flex items-center justify-center size-[18px] rounded-full border border-border text-[11px] font-bold text-primary cursor-help"
          title={t('ia-locale:learn.description')}
        >
          <IconQuestionMark className="size-3" />
        </span>
      </div>
      <p className="text-xs text-muted-foreground mt-1">{t('ia-locale:learn.description')}</p>

      <div className="grid grid-cols-2 gap-3 mt-3">
        <div className="col-span-2">
          <Label>{t('ia-locale:learn.sujet')}</Label>
          <Input
            className="mt-1"
            placeholder={t('ia-locale:learn.sujetPlaceholder')}
            value={sujet}
            onChange={(e) => setSujet(e.target.value)}
          />
        </div>
        <div className="col-span-2">
          <Label>{t('ia-locale:learn.urls')}</Label>
          <Textarea
            className="mt-1 h-16 font-mono text-xs"
            placeholder={t('ia-locale:learn.urlsPlaceholder')}
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
          />
        </div>
        {champ('maxPages', t('ia-locale:learn.maxPages'))}
        {champ('maxCaracteresPage', t('ia-locale:learn.maxPage'))}
        {champ('maxTotal', t('ia-locale:learn.maxTotal'))}
        {champ('limiteResume', t('ia-locale:learn.limiteResume'))}
      </div>

      <div className="flex gap-2 mt-3">
        <Button size="sm" onClick={lancer} disabled={enCours}>
          <IconPlayerPlay className="size-4 mr-1" />
          {t('ia-locale:learn.lancer')}
        </Button>
        <Button size="sm" variant="outline" onClick={utiliser} disabled={!resultat}>
          {t('ia-locale:learn.utiliser')}
        </Button>
        <Button size="sm" variant="ghost" onClick={supprimer}>
          <IconTrash className="size-4 mr-1" />
          {t('ia-locale:learn.supprimer')}
        </Button>
      </div>

      {progression && <p className="text-xs text-muted-foreground mt-2">{progression}</p>}
      {message && <p className="text-xs text-green-500 mt-1">{message}</p>}

      {resultat && (
        <div className="mt-3">
          <Label className="text-xs">{t('ia-locale:learn.resume')}</Label>
          <Textarea className="mt-1 h-40 text-xs" readOnly value={resultat.resume} />
        </div>
      )}
    </Card>
  )
}

export async function connaissancesDisponibles(): Promise<boolean> {
  return (await dernierResume()) !== null
}
