//! Commandes Tauri pour IA Locale (fork Jan) :
//! - scan d'un dossier `models/` (GGUF + Transformers)
//! - estimation VRAM et résolution du profil matériel (auto/cpu/gpu/hybride)
//! - application du profil dans le `model.yml` du modèle (n_gpu_layers, ctx_size, threads)

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Manager};

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct LocalModelInfo {
    pub id: String,
    pub name: String,
    pub path: String,
    pub format: String,
    pub size_bytes: u64,
    pub params: u64,
    pub quantization: Option<String>,
    pub layers: Option<u64>,
    pub vram_full_go: Option<f64>,
    pub model_type: Option<String>,
    pub architectures: Vec<String>,
}

#[derive(Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct HardwareProfileInput {
    pub mode: String,
    pub budget_vram_go: f64,
    pub budget_ram_go: f64,
    pub offload_layers: i64,
    pub threads_cpu: i64,
    pub context: u64,
}

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct HardwareDecision {
    pub mode: String,
    pub gpu_layers: u64,
    pub total_layers: u64,
    pub vram_go: f64,
    pub warning: Option<String>,
    pub ctx_size: u64,
    pub threads: i64,
}

const CONTEXTE_PAR_DEFAUT: u64 = 4096;

/// Dossier models/ par défaut : `models/` à côté de l'exécutable s'il existe,
/// sinon `<app_data>/models`.
#[tauri::command]
pub fn default_models_dir(app: AppHandle) -> String {
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let candidat = parent.join("models");
            if candidat.is_dir() {
                return candidat.to_string_lossy().into_owned();
            }
        }
    }
    let base = app
        .path()
        .app_data_dir()
        .unwrap_or_else(|_| PathBuf::from("."));
    base.join("models").to_string_lossy().into_owned()
}

fn scanner_dossier(dir: &Path, racine: &Path, out: &mut Vec<LocalModelInfo>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    for entree in entries.flatten() {
        let chemin = entree.path();
        let nom = entree.file_name().to_string_lossy().into_owned();
        if nom.starts_with('.') {
            continue;
        }
        if chemin.is_dir() {
            if chemin.join("config.json").is_file() {
                if let Some(m) = scanner_transformers(&chemin, racine) {
                    out.push(m);
                }
            }
            scanner_dossier(&chemin, racine, out);
        } else if chemin
            .extension()
            .map(|e| e.to_string_lossy().to_lowercase() == "gguf")
            .unwrap_or(false)
        {
            if let Some(m) = scanner_gguf(&chemin, racine) {
                out.push(m);
            }
        }
    }
}

fn scanner_gguf(chemin: &Path, racine: &Path) -> Option<LocalModelInfo> {
    let taille = fs::metadata(chemin).ok()?.len();
    let fichier = fs::File::open(chemin).ok()?;
    let meta = gguf_meta::lire_meta_depuis_fichier(fichier).ok()?;
    let vram = if meta.blocks.unwrap_or(0) > 0 {
        Some(gguf_meta::estimer_vram_go(
            &meta,
            taille,
            CONTEXTE_PAR_DEFAUT,
            meta.blocks.unwrap_or(0),
        ))
    } else {
        None
    };
    let quant = Pfer::quantisation_depuis_nom(chemin);
    let id = chemin
        .strip_prefix(racine)
        .unwrap_or(chemin)
        .to_string_lossy()
        .replace('\\', "/");
    Some(LocalModelInfo {
        name: if meta.name.is_empty() {
            chemin.file_stem().unwrap_or_default().to_string_lossy().into_owned()
        } else {
            meta.name.clone()
        },
        id,
        path: chemin.to_string_lossy().into_owned(),
        format: "gguf".into(),
        size_bytes: taille,
        params: meta.params(),
        quantization: quant,
        layers: meta.blocks,
        vram_full_go: vram,
        model_type: None,
        architectures: vec![],
    })
}

fn scanner_transformers(dir: &Path, racine: &Path) -> Option<LocalModelInfo> {
    let config: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(dir.join("config.json")).ok()?).ok()?;
    let mut taille: u64 = 0;
    for motif in ["*.safetensors", "*.bin", "*.pt", "*.pth"] {
        for entree in glob_simple(dir, motif) {
            if let Ok(m) = fs::metadata(&entree) {
                taille += m.len();
            }
        }
    }
    let archs = config
        .get("architectures")
        .and_then(|a| a.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default();
    let id = dir
        .strip_prefix(racine)
        .unwrap_or(dir)
        .to_string_lossy()
        .replace('\\', "/");
    Some(LocalModelInfo {
        id,
        name: dir.file_name()?.to_string_lossy().into_owned(),
        path: dir.to_string_lossy().into_owned(),
        format: "transformers".into(),
        size_bytes: taille,
        params: taille / 2,
        quantization: None,
        layers: None,
        vram_full_go: None,
        model_type: config.get("model_type").and_then(|m| m.as_str()).map(|s| s.to_string()),
        architectures: archs,
    })
}

fn glob_simple(dir: &Path, motif: &str) -> Vec<PathBuf> {
    let mut out = Vec::new();
    let Ok(entries) = fs::read_dir(dir) else { return out };
    for e in entries.flatten() {
        let p = e.path();
        if p.is_file() && p.to_string_lossy().ends_with(&motif[1..]) {
            out.push(p);
        }
    }
    out
}

struct Pfer;
impl Pfer {
    fn quantisation_depuis_nom(chemin: &Path) -> Option<String> {
        let nom = chemin.file_stem()?.to_string_lossy().to_lowercase();
        let re = regex_lite(&nom);
        re
    }
}

fn regex_lite(nom: &str) -> Option<String> {
    for motif in ["q8_0", "q6_k", "q5_k_m", "q5_k_s", "q4_k_m", "q4_k_s", "q4_0", "q3_k_m", "q2_k", "f16", "f32", "bf16"] {
        if nom.contains(motif) {
            return Some(motif.to_uppercase().replace('-', "_"));
        }
    }
    None
}

/// Scanne un dossier models/ et retourne les modèles détectés.
#[tauri::command]
pub fn scan_models_dir(dir: String) -> Result<Vec<LocalModelInfo>, String> {
    let racine = PathBuf::from(&dir);
    if !racine.is_dir() {
        return Ok(vec![]);
    }
    let mut out = Vec::new();
    scanner_dossier(&racine, &racine, &mut out);
    out.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    Ok(out)
}

/// Résout le profil matériel demandé pour un fichier GGUF.
#[tauri::command]
pub fn resolve_hardware_profile(
    model_path: String,
    profile: HardwareProfileInput,
) -> Result<HardwareDecision, String> {
    let taille = fs::metadata(&model_path).map_err(|e| e.to_string())?.len();
    let fichier = fs::File::open(&model_path).map_err(|e| e.to_string())?;
    let meta = gguf_meta::lire_meta_depuis_fichier(fichier)?;
    let mode = gguf_meta::ModeCalcul::parse(&profile.mode);
    let d = gguf_meta::choisir_mode(
        &meta,
        taille,
        profile.context.max(1024),
        mode,
        profile.budget_vram_go,
        profile.offload_layers,
    );
    Ok(HardwareDecision {
        mode: d.mode.as_str().to_string(),
        gpu_layers: d.couches_gpu,
        total_layers: d.couches_totales,
        vram_go: d.vram_estimee_go,
        warning: d.avertissement,
        ctx_size: profile.context.max(1024),
        threads: profile.threads_cpu.max(1) as i64,
    })
}

/// Écrit le profil matériel dans le model.yml du modèle (n_gpu_layers, ctx_size, threads).
#[tauri::command]
pub fn apply_hardware_profile(
    model_yml_path: String,
    gpu_layers: u64,
    ctx_size: u64,
    threads: i64,
) -> Result<(), String> {
    let chemin = PathBuf::from(&model_yml_path);
    let contenu = fs::read_to_string(&chemin).map_err(|e| e.to_string())?;
    let mut doc: serde_yaml::Value =
        serde_yaml::from_str(&contenu).map_err(|e| format!("yaml invalide : {e}"))?;
    if !doc.is_mapping() {
        doc = serde_yaml::Value::Mapping(serde_yaml::Mapping::new());
    }
    let map = doc.as_mapping_mut().unwrap();
    let set = |map: &mut serde_yaml::Mapping, cle: &str, val: serde_yaml::Value| {
        map.insert(serde_yaml::Value::String(cle.to_string()), val);
    };
    set(map, "n_gpu_layers", serde_yaml::Value::Number(gpu_layers.into()));
    set(map, "ctx_size", serde_yaml::Value::Number(ctx_size.into()));
    set(map, "threads", serde_yaml::Value::Number(threads.into()));
    let sortie = serde_yaml::to_string(&doc).map_err(|e| e.to_string())?;
    fs::write(&chemin, sortie).map_err(|e| e.to_string())?;
    Ok(())
}
