import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from '@/i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card } from '@/components/ui/card'
import { IconRefresh, IconDeviceDesktop, IconQuestionMark } from '@tabler/icons-react'
import {
  applyHardwareProfile,
  defaultModelsDir,
  formatParams,
  formatTaille,
  getProfile,
  janDataFolder,
  loadProfiles,
  resolveHardwareProfile,
  saveProfile,
  scanModelsDir,
  type ComputeMode,
  type HardwareDecision,
  type HardwareProfile,
  type LocalModelInfo,
  DEFAULT_PROFILE,
} from '@/lib/localModels'

const MODES: ComputeMode[] = ['auto', 'cpu', 'gpu', 'hybride']
const CONTEXTES = [1024, 2048, 4096, 8192, 16384, 32768]

export default function LocalModelsPanel() {
  const { t } = useTranslation()
  const [dossier, setDossier] = useState('')
  const [modeles, setModeles] = useState<LocalModelInfo[]>([])
  const [selection, setSelection] = useState<LocalModelInfo | null>(null)
  const [profil, setProfil] = useState<HardwareProfile>(DEFAULT_PROFILE)
  const [decision, setDecision] = useState<HardwareDecision | null>(null)
  const [message, setMessage] = useState('')
  const [enCours, setEnCours] = useState(false)

  const actualiser = useCallback(async (dir?: string) => {
    const cible = dir ?? dossier
    if (!cible) return
    setEnCours(true)
    try {
      const trouves = await scanModelsDir(cible)
      setModeles(trouves)
    } catch (e) {
      setMessage(String(e))
    } finally {
      setEnCours(false)
    }
  }, [dossier])

  useEffect(() => {
    defaultModelsDir().then((d) => {
      setDossier(d)
      actualiser(d)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const choisir = async (m: LocalModelInfo) => {
    setSelection(m)
    setDecision(null)
    const p = await getProfile(m.id)
    setProfil(p)
    if (m.format === 'gguf') {
      try {
        setDecision(await resolveHardwareProfile(m.path, p))
      } catch {
        setDecision(null)
      }
    }
  }

  const recalculer = async (p: HardwareProfile) => {
    setProfil(p)
    if (selection?.format === 'gguf') {
      try {
        setDecision(await resolveHardwareProfile(selection.path, p))
      } catch {
        setDecision(null)
      }
    }
  }

  const enregistrer = async () => {
    if (!selection) return
    await saveProfile(selection.id, profil)
    setMessage(t('ia-locale:localModels.profilEnregistre', { nom: selection.name }))
  }

  const appliquer = async () => {
    if (!selection || !decision) return
    const data = await janDataFolder()
    const yml = `${data}/models/${selection.id}/model.yml`
    await applyHardwareProfile(yml, decision.gpuLayers, decision.ctxSize, decision.threads)
    setMessage(
      t('ia-locale:localModels.profilApplique', {
        path: yml,
        couches: decision.gpuLayers,
        ctx: decision.ctxSize,
        threads: decision.threads,
      })
    )
  }

  const maxCouches = selection?.layers ?? 80

  return (
    <Card className="p-4 mt-4">
      <div className="flex items-center gap-2 flex-wrap">
        <IconDeviceDesktop className="size-5 text-primary" />
        <h3 className="font-semibold">{t('ia-locale:localModels.title')}</h3>
        <span
          className="inline-flex items-center justify-center size-[18px] rounded-full border border-border text-[11px] font-bold text-primary cursor-help"
          title={t('ia-locale:localModels.description') + ' ' + t('ia-locale:localModels.aide')}
        >
          <IconQuestionMark className="size-3" />
        </span>
        <div className="flex-1" />
        <Button variant="outline" size="sm" onClick={() => actualiser()} disabled={enCours}>
          <IconRefresh className="size-4 mr-1" />
          {t('ia-locale:localModels.actualiser')}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground mt-1">
        {t('ia-locale:localModels.description')}
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        {t('ia-locale:localModels.dossier')} <code>{dossier}</code>
      </p>

      {modeles.length === 0 ? (
        <p className="text-sm text-muted-foreground mt-3">{t('ia-locale:localModels.aucun')}</p>
      ) : (
        <div className="mt-3 border rounded-md divide-y">
          <div className="grid grid-cols-5 gap-2 px-3 py-2 text-xs font-medium text-muted-foreground">
            <span>{t('ia-locale:localModels.colonnes.nom')}</span>
            <span>{t('ia-locale:localModels.colonnes.format')}</span>
            <span>{t('ia-locale:localModels.colonnes.taille')}</span>
            <span>{t('ia-locale:localModels.colonnes.params')}</span>
            <span>{t('ia-locale:localModels.colonnes.vram')}</span>
          </div>
          {modeles.map((m) => (
            <div
              key={m.id}
              className={`grid grid-cols-5 gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-accent/40 ${selection?.id === m.id ? 'bg-accent/40' : ''}`}
              onClick={() => choisir(m)}
            >
              <span className="font-medium truncate">{m.name}</span>
              <span>
                {m.format.toUpperCase()}
                {m.quantization ? ` (${m.quantization})` : ''}
              </span>
              <span>{formatTaille(m.sizeBytes)}</span>
              <span>~{formatParams(m.params)}</span>
              <span>{m.vramFullGo ? `${m.vramFullGo.toFixed(2)} Gio` : '—'}</span>
            </div>
          ))}
        </div>
      )}

      {selection && (
        <div className="mt-4 border-t pt-3 space-y-3">
          <h4 className="font-medium">
            {t('ia-locale:localModels.profilTitre')} — {selection.name}
          </h4>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>{t('ia-locale:localModels.mode')}</Label>
              <Select
                value={profil.mode}
                onValueChange={(v) => recalculer({ ...profil, mode: v as ComputeMode })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MODES.map((m) => (
                    <SelectItem key={m} value={m}>
                      {t(`ia-locale:localModels.modes.${m}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-[11px] text-muted-foreground mt-1">
                {t('ia-locale:localModels.modeAide')}
              </p>
            </div>
            <div>
              <Label>{t('ia-locale:localModels.contexte')}</Label>
              <Select
                value={String(profil.context)}
                onValueChange={(v) => recalculer({ ...profil, context: Number(v) })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONTEXTES.map((c) => (
                    <SelectItem key={c} value={String(c)}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{t('ia-locale:localModels.budgetVram')}</Label>
              <div className="flex items-center gap-2 mt-2">
                <Slider
                  className="flex-1"
                  min={1}
                  max={64}
                  step={0.5}
                  value={[profil.budgetVramGo]}
                  onValueChange={([v]) => recalculer({ ...profil, budgetVramGo: v })}
                />
                <span className="text-sm w-14 text-right">{profil.budgetVramGo.toFixed(1)}</span>
              </div>
            </div>
            <div>
              <Label>{t('ia-locale:localModels.budgetRam')}</Label>
              <div className="flex items-center gap-2 mt-2">
                <Slider
                  className="flex-1"
                  min={2}
                  max={128}
                  step={1}
                  value={[profil.budgetRamGo]}
                  onValueChange={([v]) => recalculer({ ...profil, budgetRamGo: v })}
                />
                <span className="text-sm w-14 text-right">{profil.budgetRamGo.toFixed(0)}</span>
              </div>
            </div>
            {selection.format === 'gguf' && (
              <div>
                <Label>{t('ia-locale:localModels.offload')}</Label>
                <div className="flex items-center gap-2 mt-2">
                  <Slider
                    className="flex-1"
                    min={0}
                    max={Math.max(maxCouches, 1)}
                    step={1}
                    value={[profil.offloadLayers < 0 ? Math.max(maxCouches, 1) : profil.offloadLayers]}
                    onValueChange={([v]) =>
                      recalculer({ ...profil, offloadLayers: v >= Math.max(maxCouches, 1) ? -1 : v })
                    }
                  />
                  <span className="text-sm w-36 text-right">
                    {profil.offloadLayers < 0
                      ? t('ia-locale:localModels.toutesCouches')
                      : t('ia-locale:localModels.couchesSur', { n: profil.offloadLayers })}
                  </span>
                </div>
              </div>
            )}
            <div>
              <Label>{t('ia-locale:localModels.threads')}</Label>
              <Input
                type="number"
                min={1}
                max={navigator.hardwareConcurrency || 64}
                className="mt-1"
                value={profil.threadsCpu}
                onChange={(e) => recalculer({ ...profil, threadsCpu: Math.max(1, Number(e.target.value)) })}
              />
            </div>
          </div>

          {decision && (
            <div className="text-xs rounded-md border p-2 bg-muted/40">
              <p>
                {t('ia-locale:localModels.modeResolu', { mode: decision.mode })}
                {' — '}
                {t('ia-locale:localModels.vramEstimee', {
                  vram: decision.vramGo.toFixed(2),
                  couches: decision.gpuLayers,
                  total: decision.totalLayers || '?',
                })}
              </p>
              {decision.warning && (
                <p className="text-amber-500 mt-1">{decision.warning}</p>
              )}
            </div>
          )}

          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={enregistrer}>
              {t('ia-locale:localModels.enregistrerProfil')}
            </Button>
            <Button size="sm" onClick={appliquer} disabled={!decision}>
              {t('ia-locale:localModels.appliquer')}
            </Button>
          </div>
          {message && <p className="text-xs text-green-500">{message}</p>}
        </div>
      )}
    </Card>
  )
}
