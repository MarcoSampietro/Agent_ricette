from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class Ingrediente(BaseModel):
    nome: str = Field(description="Nome dell'ingrediente")
    quantita: Optional[str] = Field(description="Quantità")
    scadenza_vicina: bool = Field(default=False)

class ProfiloUtente(BaseModel):
    ingredienti: List[Ingrediente] = Field(default_factory=list)
    vincoli_alimentari: List[str] = Field(default_factory=list)
    n_persone: Optional[int] = Field(None)
    vincoli_alimentari_verificati: bool = Field(False)
    obiettivo_raggiunto: bool = Field(False)
    
    # --- MONITORAGGIO TOKEN ---
    token_totali: int = Field(0, description="Token totali usati nella sessione")
    ultima_risposta_costo: int = Field(0)
    budget_token: int = Field(20000, description="Limite massimo per sessione")

def stato_to_text(p: ProfiloUtente) -> str:
    text = f"STATO ATTUALE (Persone: {p.n_persone or '?'}, Vincoli: {', '.join(p.vincoli_alimentari) if p.vincoli_alimentari else 'Nessuno'})\n"
    text += "Ingredienti Disponibili: " + ", ".join([f"{i.nome} ({i.quantita or 'q.b.'})" for i in p.ingredienti])
    return text