import { invoke } from '@tauri-apps/api/core'
import { load } from '@tauri-apps/plugin-store'

export type ComputeMode = 'auto' | 'cpu' | 'gpu' | 'hybride'

export interface LocalModelInfo {
  id: string
  name: string
  path: string
  format: 'gguf' | 'transformers' | string
  sizeBytes: number
  params: number
  quantization?: string | null
  layers?: number | null
  vramFullGo?: number | null
  modelType?: string | null
  architectures: string[]
}

export interface HardwareProfile {
  mode: ComputeMode
  budgetVramGo: number
  budgetRamGo: number
  offloadLayers: number // -1 = toutes les couches
  threadsCpu: number
  context: number
}

export const DEFAULT_PROFILE: HardwareProfile = {
  mode: 'auto',
  budgetVramGo: 6,
  budgetRamGo: 16,
  offloadLayers: -1,
  threadsCpu: Math.max(1, Math.floor((navigator.hardwareConcurrency || 4) / 2)),
  context: 4096,
}

export interface HardwareDecision {
  mode: string
  gpuLayers: number
  totalLayers: number
  vramGo: number
  warning?: string | null
  ctxSize: number
  threads: number
}

export async function defaultModelsDir(): Promise<string> {
  return invoke<string>('default_models_dir')
}

export async function scanModelsDir(dir: string): Promise<LocalModelInfo[]> {
  return invoke<LocalModelInfo[]>('scan_models_dir', { dir })
}

export async function resolveHardwareProfile(
  modelPath: string,
  profile: HardwareProfile
): Promise<HardwareDecision> {
  return invoke<HardwareDecision>('resolve_hardware_profile', {
    modelPath,
    profile: {
      mode: profile.mode,
      budgetVramGo: profile.budgetVramGo,
      budgetRamGo: profile.budgetRamGo,
      offloadLayers: profile.offloadLayers,
      threadsCpu: profile.threadsCpu,
      context: profile.context,
    },
  })
}

export async function applyHardwareProfile(
  modelYmlPath: string,
  gpuLayers: number,
  ctxSize: number,
  threads: number
): Promise<void> {
  await invoke('apply_hardware_profile', { modelYmlPath, gpuLayers, ctxSize, threads })
}

export async function janDataFolder(): Promise<string> {
  return invoke<string>('get_jan_data_folder_path')
}

const PROFILES_STORE = 'ia-locale-profils.json'

async function readStore(): Promise<Record<string, HardwareProfile>> {
  try {
    const store = await load(PROFILES_STORE, { autoSave: false })
    const brut = await store.get<Record<string, HardwareProfile>>('profils')
    return brut && typeof brut === 'object' ? brut : {}
  } catch {
    return {}
  }
}

export async function loadProfiles(): Promise<Record<string, HardwareProfile>> {
  return readStore()
}

export async function getProfile(modelId: string): Promise<HardwareProfile> {
  const tous = await readStore()
  return { ...DEFAULT_PROFILE, ...(tous[modelId] ?? {}) }
}

export async function saveProfile(modelId: string, profile: HardwareProfile): Promise<void> {
  const store = await load(PROFILES_STORE, { autoSave: false })
  const tous = await readStore()
  tous[modelId] = profile
  await store.set('profils', tous)
  await store.save()
}

export function formatTaille(octets: number): string {
  const unites = ['o', 'Kio', 'Mio', 'Gio', 'Tio']
  let v = octets
  let i = 0
  while (v >= 1024 && i < unites.length - 1) {
    v /= 1024
    i++
  }
  return i === 0 ? `${v} ${unites[i]}` : `${v.toFixed(1)} ${unites[i]}`
}

export function formatParams(p: number): string {
  if (!p) return '?'
  if (p >= 1e9) return `${(p / 1e9).toFixed(1)} Md`
  if (p >= 1e6) return `${(p / 1e6).toFixed(1)} M`
  return `${p}`
}
