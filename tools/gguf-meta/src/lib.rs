//! Lecture d'en-tête GGUF (v1-v3) et estimation de la VRAM avec marge pour le contexte.
//! Pur std, testé unitairement.

use std::io::{Read, Seek, SeekFrom};

pub const GGUF_MAGIC: &[u8; 4] = b"GGUF";

pub const MARGE_PROPORTIONNELLE: f64 = 0.12;
pub const MARGE_FIXE_MO: f64 = 256.0;

#[derive(Debug, Clone, Default)]
pub struct GgufMeta {
    pub version: u32,
    pub architecture: String,
    pub name: String,
    pub tensor_count: u64,
    pub tensor_bytes: u64,
    pub blocks: Option<u64>,
    pub embedding: Option<u64>,
    pub heads: Option<u64>,
    pub kv_heads: Option<u64>,
    pub head_dim: Option<u64>,
    pub params_declared: Option<u64>,
}

impl GgufMeta {
    pub fn params(&self) -> u64 {
        self.params_declared
            .filter(|p| *p > 0)
            .unwrap_or(self.tensor_bytes / 2)
    }
}

struct Lecteur<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> Lecteur<'a> {
    fn lire(&mut self, n: usize) -> Result<&'a [u8], String> {
        if self.pos + n > self.data.len() {
            return Err("fin de fichier inattendue".into());
        }
        let m = &self.data[self.pos..self.pos + n];
        self.pos += n;
        Ok(m)
    }
    fn u32(&mut self) -> Result<u32, String> {
        Ok(u32::from_le_bytes(self.lire(4)?.try_into().unwrap()))
    }
    fn u64(&mut self) -> Result<u64, String> {
        Ok(u64::from_le_bytes(self.lire(8)?.try_into().unwrap()))
    }
    fn chaine(&mut self) -> Result<String, String> {
        let n = self.u64()? as usize;
        let b = self.lire(n)?;
        Ok(String::from_utf8_lossy(b).into_owned())
    }
    fn valeur(&mut self, t: u32) -> Result<Valeur, String> {
        match t {
            0 | 1 | 7 => Ok(Valeur::Entier(self.lire(1)?[0] as u64)),
            2 | 3 => Ok(Valeur::Entier(u16::from_le_bytes(self.lire(2)?.try_into().unwrap()) as u64)),
            4 | 5 => Ok(Valeur::Entier(u32::from_le_bytes(self.lire(4)?.try_into().unwrap()) as u64)),
            6 => {
                self.lire(4)?;
                Ok(Valeur::Autre)
            }
            10 | 11 => Ok(Valeur::Entier(u64::from_le_bytes(self.lire(8)?.try_into().unwrap()))),
            12 => {
                self.lire(8)?;
                Ok(Valeur::Autre)
            }
            8 => Ok(Valeur::Chaine(self.chaine()?)),
            9 => {
                let elem = self.u32()?;
                let n = self.u64()?;
                for _ in 0..n {
                    self.valeur(elem)?;
                }
                Ok(Valeur::Autre)
            }
            _ => Err(format!("type de valeur inconnu : {t}")),
        }
    }
}

enum Valeur {
    Entier(u64),
    Chaine(String),
    Autre,
}

const TAILLE_TENSEUR: [u64; 32] = [
    1, 1, 2, 2, 4, 4, 4, 4, 2, 2, 2, 4, 4, 4, 1, 1, 2, 2, 4, 4, 8, 8, 8, 8, 8, 8, 4, 4, 8, 8, 4, 4,
];

/// Lit l'en-tête GGUF d'un fichier (seulement les premiers octets utiles).
pub fn lire_meta_depuis_fichier<R: Read + Seek>(mut f: R) -> Result<GgufMeta, String> {
    let mut tete = vec![0u8; 8 * 1024 * 1024];
    let lus = f.read(&mut tete).map_err(|e| e.to_string())?;
    tete.truncate(lus);
    let _ = f.seek(SeekFrom::Start(0));
    lire_meta(&tete)
}

pub fn lire_meta(data: &[u8]) -> Result<GgufMeta, String> {
    let mut l = Lecteur { data, pos: 0 };
    if l.lire(4)? != GGUF_MAGIC {
        return Err("pas un fichier GGUF (magie manquante)".into());
    }
    let version = l.u32()?;
    if !(1..=3).contains(&version) {
        return Err(format!("version GGUF non supportée : {version}"));
    }
    let nb_tensors = if version >= 3 { l.u64()? } else { l.u32()? as u64 };
    let nb_meta = if version >= 3 { l.u64()? } else { l.u32()? as u64 };

    let mut meta = GgufMeta {
        version,
        ..Default::default()
    };
    for _ in 0..nb_meta {
        let cle = l.chaine()?;
        let t = l.u32()?;
        match l.valeur(t)? {
            Valeur::Entier(v) => {
                if cle == "general.parameter_count" {
                    meta.params_declared = Some(v);
                }
                if let Some(rest) = cle.strip_prefix("llama.") {
                    match rest {
                        "block_count" => meta.blocks = Some(v),
                        "embedding_length" => meta.embedding = Some(v),
                        "attention.head_count" => meta.heads = Some(v),
                        "attention.head_count_kv" => meta.kv_heads = Some(v),
                        "attention.key_length" => meta.head_dim = Some(v),
                        _ => {}
                    }
                }
            }
            Valeur::Chaine(s) => {
                if cle == "general.architecture" {
                    meta.architecture = s;
                } else if cle == "general.name" {
                    meta.name = s;
                }
            }
            Valeur::Autre => {}
        }
    }

    let mut octets_tensors: u64 = 0;
    for _ in 0..nb_tensors {
        let _nom = l.chaine()?;
        let n_dims = l.u32()? as usize;
        let mut produit: u64 = 1;
        for _ in 0..n_dims {
            let d = l.u64()?;
            produit = produit.saturating_mul(d);
        }
        let type_t = l.u32()? as usize;
        let _offset = l.u64()?;
        let taille = TAILLE_TENSEUR.get(type_t).copied().unwrap_or(4);
        octets_tensors = octets_tensors.saturating_add(produit.saturating_mul(taille));
    }
    meta.tensor_count = nb_tensors;
    meta.tensor_bytes = octets_tensors;
    Ok(meta)
}

/// Cache KV par couche en Gio (2 tenseurs K et V, 16 bits).
pub fn kv_par_couche_go(ctx: u64, kv_heads: u64, head_dim: u64) -> f64 {
    2.0 * ctx as f64 * kv_heads as f64 * head_dim as f64 * 2.0 / (1024.0_f64.powi(3))
}

/// Estimation VRAM en Gio : poids des couches GPU + cache KV + marge (contexte incluse).
pub fn estimer_vram_go(meta: &GgufMeta, taille_fichier: u64, ctx: u64, couches_gpu: u64) -> f64 {
    let n = meta.blocks.unwrap_or(0).max(1);
    let couches_gpu = couches_gpu.min(n);
    let poids_total_go = (if meta.tensor_bytes > 0 { meta.tensor_bytes } else { taille_fichier }) as f64
        / 1024.0_f64.powi(3);
    let kv_heads = meta.kv_heads.or(meta.heads).unwrap_or(1).max(1);
    let head_dim = meta.head_dim.unwrap_or_else(|| {
        match (meta.embedding, meta.heads) {
            (Some(e), Some(h)) if h > 0 => e / h,
            _ => 0,
        }
    });
    let kv_couche = kv_par_couche_go(ctx, kv_heads, head_dim);
    let fraction = couches_gpu as f64 / n as f64;
    let poids = poids_total_go * fraction;
    let kv = kv_couche * couches_gpu as f64;
    poids + kv + (poids + kv) * MARGE_PROPORTIONNELLE + MARGE_FIXE_MO / 1024.0
}

/// Nombre maximal de couches déchargeables dans le budget VRAM (Gio).
pub fn couches_dans_budget(meta: &GgufMeta, taille_fichier: u64, ctx: u64, budget_go: f64) -> u64 {
    let n = meta.blocks.unwrap_or(0);
    if n == 0 || budget_go <= 0.0 {
        return 0;
    }
    let mut k = n;
    while k > 0 {
        if estimer_vram_go(meta, taille_fichier, ctx, k) <= budget_go {
            return k;
        }
        k -= 1;
    }
    0
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModeCalcul {
    Auto,
    Cpu,
    Gpu,
    Hybride,
}

impl ModeCalcul {
    pub fn parse(s: &str) -> ModeCalcul {
        match s.to_ascii_lowercase().as_str() {
            "cpu" => ModeCalcul::Cpu,
            "gpu" => ModeCalcul::Gpu,
            "hybride" => ModeCalcul::Hybride,
            _ => ModeCalcul::Auto,
        }
    }
    pub fn as_str(&self) -> &'static str {
        match self {
            ModeCalcul::Auto => "auto",
            ModeCalcul::Cpu => "cpu",
            ModeCalcul::Gpu => "gpu",
            ModeCalcul::Hybride => "hybride",
        }
    }
}

#[derive(Debug, Clone)]
pub struct DecisionMaterielle {
    pub mode: ModeCalcul,
    pub couches_gpu: u64,
    pub couches_totales: u64,
    pub vram_estimee_go: f64,
    pub avertissement: Option<String>,
}

/// Applique le mode demandé (auto/cpu/gpu/hybride) avec le budget VRAM.
pub fn choisir_mode(
    meta: &GgufMeta,
    taille_fichier: u64,
    ctx: u64,
    mode: ModeCalcul,
    budget_go: f64,
    offload_demande: i64,
) -> DecisionMaterielle {
    let n = meta.blocks.unwrap_or(0);
    if mode == ModeCalcul::Cpu {
        return DecisionMaterielle {
            mode: ModeCalcul::Cpu,
            couches_gpu: 0,
            couches_totales: n,
            vram_estimee_go: 0.0,
            avertissement: None,
        };
    }
    let tout = estimer_vram_go(meta, taille_fichier, ctx, n);
    if mode == ModeCalcul::Gpu {
        if tout <= budget_go {
            return DecisionMaterielle {
                mode: ModeCalcul::Gpu,
                couches_gpu: n,
                couches_totales: n,
                vram_estimee_go: tout,
                avertissement: None,
            };
        }
        let possibles = couches_dans_budget(meta, taille_fichier, ctx, budget_go);
        if possibles == 0 {
            return DecisionMaterielle {
                mode: ModeCalcul::Cpu,
                couches_gpu: 0,
                couches_totales: n,
                vram_estimee_go: 0.0,
                avertissement: Some(format!(
                    "Le modèle complet (~{tout:.1} Gio) dépasse le budget GPU ({budget_go:.1} Gio) : calcul CPU."
                )),
            };
        }
        return DecisionMaterielle {
            mode: ModeCalcul::Hybride,
            couches_gpu: possibles,
            couches_totales: n,
            vram_estimee_go: estimer_vram_go(meta, taille_fichier, ctx, possibles),
            avertissement: Some(format!(
                "Le modèle complet (~{tout:.1} Gio) dépasse le budget GPU ({budget_go:.1} Gio) : {possibles}/{n} couches sur GPU."
            )),
        };
    }
    if mode == ModeCalcul::Hybride {
        let demandees = if offload_demande < 0 { n } else { offload_demande as u64 };
        let demandees = demandees.min(n);
        let possibles = couches_dans_budget(meta, taille_fichier, ctx, budget_go);
        let couches = demandees.min(possibles);
        if couches == 0 {
            return DecisionMaterielle {
                mode: ModeCalcul::Cpu,
                couches_gpu: 0,
                couches_totales: n,
                vram_estimee_go: 0.0,
                avertissement: Some("Aucune couche ne tient dans le budget GPU : calcul CPU.".into()),
            };
        }
        return DecisionMaterielle {
            mode: ModeCalcul::Hybride,
            couches_gpu: couches,
            couches_totales: n,
            vram_estimee_go: estimer_vram_go(meta, taille_fichier, ctx, couches),
            avertissement: None,
        };
    }
    // auto
    if tout <= budget_go {
        return DecisionMaterielle {
            mode: ModeCalcul::Gpu,
            couches_gpu: n,
            couches_totales: n,
            vram_estimee_go: tout,
            avertissement: None,
        };
    }
    let possibles = couches_dans_budget(meta, taille_fichier, ctx, budget_go);
    if possibles > 0 {
        return DecisionMaterielle {
            mode: ModeCalcul::Hybride,
            couches_gpu: possibles,
            couches_totales: n,
            vram_estimee_go: estimer_vram_go(meta, taille_fichier, ctx, possibles),
            avertissement: None,
        };
    }
    DecisionMaterielle {
        mode: ModeCalcul::Cpu,
        couches_gpu: 0,
        couches_totales: n,
        vram_estimee_go: 0.0,
        avertissement: Some(format!(
            "VRAM estimée ~{tout:.1} Gio > budget {budget_go:.1} Gio : calcul CPU."
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entete_gguf_test() -> Vec<u8> {
        let mut out = Vec::new();
        out.extend_from_slice(b"GGUF");
        out.extend_from_slice(&3u32.to_le_bytes());
        out.extend_from_slice(&1u64.to_le_bytes()); // 1 tenseur
        let kv = [
            ("general.architecture", 8u32, b"llama".to_vec()),
            ("general.name", 8, b"Modele Test".to_vec()),
            ("general.parameter_count", 10, 7_000_000_000u64.to_le_bytes().to_vec()),
            ("llama.block_count", 4, 32u32.to_le_bytes().to_vec()),
            ("llama.embedding_length", 4, 4096u32.to_le_bytes().to_vec()),
            ("llama.attention.head_count_kv", 4, 8u32.to_le_bytes().to_vec()),
            ("llama.attention.key_length", 4, 128u32.to_le_bytes().to_vec()),
        ];
        let entrees: Vec<(&str, u32, Vec<u8>)> = kv.to_vec();
        out.extend_from_slice(&(entrees.len() as u64).to_le_bytes()); // métadonnées
        for (cle, t, val) in entrees {
            out.extend_from_slice(&(cle.len() as u64).to_le_bytes());
            out.extend_from_slice(cle.as_bytes());
            out.extend_from_slice(&t.to_le_bytes());
            if t == 8 {
                out.extend_from_slice(&(val.len() as u64).to_le_bytes());
            }
            out.extend_from_slice(&val);
        }
        // 1 tenseur : nom + 2 dims + type F32(6) + offset
        out.extend_from_slice(&(4u64).to_le_bytes());
        out.extend_from_slice(b"abcd");
        out.extend_from_slice(&2u32.to_le_bytes());
        out.extend_from_slice(&32768u64.to_le_bytes()); // 32768*32768*4 o = 4 Gio
        out.extend_from_slice(&32768u64.to_le_bytes());
        out.extend_from_slice(&6u32.to_le_bytes());
        out.extend_from_slice(&0u64.to_le_bytes());
        out
    }

    #[test]
    fn parse_entete() {
        let meta = lire_meta(&entete_gguf_test()).unwrap();
        assert_eq!(meta.architecture, "llama");
        assert_eq!(meta.name, "Modele Test");
        assert_eq!(meta.blocks, Some(32));
        assert_eq!(meta.embedding, Some(4096));
        assert_eq!(meta.kv_heads, Some(8));
        assert_eq!(meta.head_dim, Some(128));
        assert_eq!(meta.params_declared, Some(7_000_000_000));
        assert_eq!(meta.tensor_bytes, 32768 * 32768 * 4);
    }

    #[test]
    fn vram_contient_marge_contexte() {
        let meta = lire_meta(&entete_gguf_test()).unwrap();
        let taille = 4 * 1024u64.pow(3);
        let e = estimer_vram_go(&meta, taille, 4096, 32);
        assert!(e > 4.0);
        let e2 = estimer_vram_go(&meta, taille, 32768, 32);
        assert!(e2 > e);
    }

    #[test]
    fn couches_dans_budget_et_modes() {
        let meta = lire_meta(&entete_gguf_test()).unwrap();
        let taille = 4 * 1024u64.pow(3);
        assert_eq!(couches_dans_budget(&meta, taille, 4096, 100.0), 32);
        let c = couches_dans_budget(&meta, taille, 4096, 1.0);
        assert!(c > 0 && c < 32);
        assert_eq!(couches_dans_budget(&meta, taille, 4096, 0.1), 0);
        let d = choisir_mode(&meta, taille, 4096, ModeCalcul::Auto, 100.0, -1);
        assert_eq!(d.mode, ModeCalcul::Gpu);
        let d = choisir_mode(&meta, taille, 4096, ModeCalcul::Auto, 1.0, -1);
        assert_eq!(d.mode, ModeCalcul::Hybride);
        let d = choisir_mode(&meta, taille, 4096, ModeCalcul::Auto, 0.1, -1);
        assert_eq!(d.mode, ModeCalcul::Cpu);
        assert!(d.avertissement.is_some());
        let d = choisir_mode(&meta, taille, 4096, ModeCalcul::Hybride, 100.0, 10);
        assert_eq!(d.couches_gpu, 10);
    }
}
