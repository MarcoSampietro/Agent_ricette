from logic import processa_messaggio
from state import ProfiloUtente

def test_flusso():
    print("--- INIZIO TEST AGENTE ---")
    
    # Stato iniziale vuoto
    stato = ProfiloUtente()
    
    # Turno 1
    input1 = "Ciao, ho della pasta e dei pomodori che stanno per scadere."
    print(f"\nUser: {input1}")
    risposta, stato = processa_messaggio(input1, stato)
    print(f"Agent: {risposta}")
    print(f"[DEBUG STATO]: {stato.model_dump_json(indent=2)}")
    
    # Turno 2
    input2 = "Ho anche delle uova, ne ho 4. Non mi piace l'aglio."
    print(f"\nUser: {input2}")
    risposta, stato = processa_messaggio(input2, stato)
    print(f"Agent: {risposta}")
    print(f"[DEBUG STATO]: {stato.model_dump_json(indent=2)}")

    # Turno 3 (Forziamo la generazione)
    input3 = "Cosa posso cucinare? Genera le ricette."
    print(f"\nUser: {input3}")
    risposta, stato = processa_messaggio(input3, stato)
    print(f"Agent: {risposta}")

if __name__ == "__main__":
    test_flusso()