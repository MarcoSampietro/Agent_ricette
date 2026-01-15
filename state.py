from pydantic import BaseModel, Field
from typing import List, Optional

class Ingrediente(BaseModel):
    nome: str = Field(description="Nome dell'ingrediente")
    quantita: Optional[str] = Field(description="Quantità (es. 200g, 2 pezzi)")
    scadenza_vicina: bool = Field(default=False)

class ProfiloUtente(BaseModel):
    ingredienti: List[Ingrediente] = Field(default_factory=list)
    vincoli_alimentari: List[str] = Field(default_factory=list)
    # Slot Obbligatori
    n_persone: Optional[int] = Field(None, description="Numero di commensali")
    vincoli_alimentari_verificati: bool = Field(False, description="True se è stato chiesto esplicitamente delle allergie")
    obiettivo_raggiunto: bool = Field(False)

def stato_to_text(p: ProfiloUtente) -> str:
    """Trasforma lo stato in testo leggibile per l'LLM"""
    text = f"STATO ATTUALE:\n"
    text += f"- Numero Persone: {p.n_persone if p.n_persone else 'Sconosciuto'}\n"
    text += f"- Vincoli Verificati: {'Sì' if p.vincoli_alimentari_verificati else 'No'}\n"
    
    if not p.ingredienti:
        text += "- Dispensa: Vuota.\n"
    else:
        text += " - Ingredienti:\n"
        for i in p.ingredienti:
            text += f"   * {i.nome} ({i.quantita or 'q.b.'})\n"
    
    text += f"- Allergie/Preferenze: {', '.join(p.vincoli_alimentari) if p.vincoli_alimentari else 'Nessuna nota'}\n"
    return text