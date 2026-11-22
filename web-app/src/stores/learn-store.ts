import { create } from 'zustand'

type LearnState = {
  /** Connaissances apprises (mode learn) à injecter dans le contexte de la discussion. */
  connaissances: string | null
  setConnaissances: (texte: string | null) => void
}

export const useLearnStore = create<LearnState>((set) => ({
  connaissances: null,
  setConnaissances: (texte) => set({ connaissances: texte }),
}))
