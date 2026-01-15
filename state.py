from pydantic import BaseModel, Field
from typing import List, Optional

class Ingrediente(BaseModel):
    nome: str = Field(description="Nome dell'ingrediente (es. pasta, uova)")
    quantita: Optional[str] = Field(description="Quantità approssimativa (es. 500g, un pacco, un po')")
    scadenza_vicina: bool = Field(default=False, description="True se l'utente indica che sta per scadere")

class ProfiloUtente(BaseModel):
    ingredienti: List[Ingrediente] = Field(default_factory=list, description="Lista degli ingredienti disponibili")
    vincoli_alimentari: List[str] = Field(default_factory=list, description="Allergie, diete o cibi non graditi")
    obiettivo_raggiunto: bool = Field(default=False, description="True se abbiamo abbastanza info per le ricette")

# Funzione helper per convertire lo stato in testo per l'LLM
def stato_to_text(profilo: ProfiloUtente) -> str:
    text = "STATO ATTUALE:\n"
    if not profilo.ingredienti:
        text += "- Nessun ingrediente noto.\n"
    else:
        text += "Ingredienti:\n"
        for i in profilo.ingredienti:
            scadenza = " (IN SCADENZA)" if i.scadenza_vicina else ""
            qty = f", qta: {i.quantita}" if i.quantita else ""
            text += f"- {i.nome}{qty}{scadenza}\n"
    
    if profilo.vincoli_alimentari:
        text += f"Vincoli/Preferenze: {', '.join(profilo.vincoli_alimentari)}\n"
    else:
        text += "Vincoli: Nessuno specificato.\n"
    return text