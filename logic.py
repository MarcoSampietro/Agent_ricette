import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from state import ProfiloUtente, stato_to_text
from dotenv import load_dotenv

load_dotenv()

# Setup Modello Leggero (Llama 3 8B)
llm = ChatGroq(
    temperature=0, 
    model_name="llama-3.3-70b-versatile", # Modello efficiente e veloce
    api_key=os.environ.get("GROQ_API_KEY")
)

# --- 1. ESTRATTORE (Aggiorna lo stato) ---
# Usa il pattern "Context Construction" del Cap. 6: prende lo stato vecchio + input nuovo -> stato nuovo
parser_stato = PydanticOutputParser(pydantic_object=ProfiloUtente)

prompt_estrazione = ChatPromptTemplate.from_messages([
    ("system", """Sei un assistente di cucina intelligente. Il tuo compito è aggiornare lo stato della dispensa e delle preferenze dell'utente basandoti sull'ultimo messaggio.
    
    REGOLE DI AGGIORNAMENTO:
    1. Mantieni gli ingredienti già presenti se non vengono contraddetti.
    2. Se l'utente specifica una quantità per un ingrediente esistente, aggiornala.
    3. Se l'utente menziona nuovi ingredienti, aggiungili.
    4. Cerca di capire se ci sono vincoli (es. "niente carne", "sono a dieta").
    5. Imposta 'obiettivo_raggiunto' a True SOLO se hai almeno 2-3 ingredienti principali e sai se ci sono vincoli, oppure se l'utente chiede esplicitamente di generare ricette.
    
    {format_instructions}
    """),
    ("user", "Stato Precedente: {stato_precedente}\n\nNuovo Input Utente: {input_utente}")
])

chain_estrazione = prompt_estrazione | llm | parser_stato

# --- 2. CHEF (Generatore Ricette) ---
prompt_chef = ChatPromptTemplate.from_messages([
    ("system", """Sei uno Chef esperto.
    Hai il seguente inventario e vincoli:
    {stato_corrente}
    
    Il tuo compito:
    Crea 3 ricette dettagliate basate ESCLUSIVAMENTE o PRINCIPALMENTE su questi ingredienti.
    Dai priorità agli ingredienti in scadenza.
    Rispetta rigorosamente i vincoli alimentari.
    
    Per ogni ricetta fornisci:
    - Nome del piatto
    - Tempo di preparazione
    - Ingredienti (con quantità stimate)
    - Procedimento passo passo
    """),
    ("user", "Proponi le 3 ricette ora.")
])

chain_chef = prompt_chef | llm

# --- 3. INTERVISTATORE (Fa domande se mancano info) ---
prompt_domanda = ChatPromptTemplate.from_messages([
    ("system", """Sei un assistente amichevole che deve aiutare l'utente a cucinare.
    Ecco cosa sai finora:
    {stato_corrente}
    
    Non hai ancora abbastanza informazioni per proporre una ricetta sicura.
    Fai UNA domanda breve e pertinente per scoprire:
    - Quantità degli ingredienti elencati (se mancano).
    - Altri ingredienti che potrebbero stare bene con quelli attuali.
    - Eventuali intolleranze o preferenze.
    
    Sii colloquiale e gentile.
    """),
    ("user", "Cosa devo chiedere dopo?")
])

chain_domanda = prompt_domanda | llm

# Funzione Master
def processa_messaggio(input_utente: str, stato_attuale: ProfiloUtente):
    # 1. Aggiorna lo stato
    stato_text_prev = stato_to_text(stato_attuale)
    try:
        nuovo_stato = chain_estrazione.invoke({
            "format_instructions": parser_stato.get_format_instructions(),
            "stato_precedente": stato_text_prev,
            "input_utente": input_utente
        })
    except Exception as e:
        # Fallback in caso di errore di parsing (succede con modelli piccoli)
        print(f"Errore parsing: {e}")
        return "Scusa, non ho capito bene. Puoi ripetere cosa hai in frigo?", stato_attuale

    # 2. Router: Ho abbastanza info?
    if nuovo_stato.obiettivo_raggiunto:
        risposta = chain_chef.invoke({"stato_corrente": stato_to_text(nuovo_stato)})
        return risposta.content, nuovo_stato
    else:
        risposta = chain_domanda.invoke({"stato_corrente": stato_to_text(nuovo_stato)})
        return risposta.content, nuovo_stato