import os
from dotenv import load_dotenv

# 1. Caricamento ambiente immediato
load_dotenv()

from typing import List, Union, Dict
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults
from state import ProfiloUtente, stato_to_text

# --- CONFIGURAZIONE TOOL TAVILY ---
search_tool = TavilySearchResults(
    max_results=3,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=False
)

# --- SETUP LLM ---
llm = ChatGroq(
    temperature=0, 
    model_name="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY")
)

# --- 1. ESTRATTORE ---
parser_stato = PydanticOutputParser(pydantic_object=ProfiloUtente)
prompt_estrazione = ChatPromptTemplate.from_messages([
    ("system", "Analista culinario: aggiorna lo stato estraendo ingredienti, n_persone e verificando i vincoli. {format_instructions}"),
    ("user", "Stato Precedente: {stato_precedente}\nInput: {input_utente}")
])
chain_estrazione = prompt_estrazione | llm | parser_stato

# --- 2. LOGICA CHEF CON RAG MANDATORIO ---

prompt_search_query = ChatPromptTemplate.from_messages([
    ("system", "Genera una query Google per trovare RICETTE MEDITERRANEE REALI. Ingredienti: {ingredienti}. Vincoli: {vincoli}."),
])

prompt_chef_final = ChatPromptTemplate.from_messages([
    ("system", """Sei lo Chef AI Mediterraneo. 
    REGOLE DI FERRO:
    1. Usa SOLO le informazioni nel 'CONTESTO DI RICERCA'.
    2. Ogni ricetta DEVE avere un URL (se presente nel contesto).
    3. Se il CONTESTO non ha ricette valide per {vincoli}, di' chiaramente che non hai trovato fonti web.
    
    CONTESTO DI RICERCA RECUPERATO:
    {context}
    """),
    ("user", "Proponi 3 ricette per {n_persone} persone con questi ingredienti: {ingredienti}")
])

def run_chef_rag(stato: ProfiloUtente):
    nomi_ing = ", ".join([i.nome for i in stato.ingredienti])
    vincoli_str = ", ".join(stato.vincoli_alimentari) if stato.vincoli_alimentari else "Nessuno"
    
    # A. Genera Query
    query_chain = prompt_search_query | llm
    search_query = query_chain.invoke({"ingredienti": nomi_ing, "vincoli": vincoli_str}).content
    print(f"\n[DEBUG] Query: {search_query}")

    # B. Esecuzione Tavily con Parsing Robusto (Fix TypeError)
    context_block = ""
    try:
        raw_results = search_tool.invoke({"query": search_query})
        
        if not raw_results:
            context_block = "NESSUN RISULTATO TROVATO."
        elif isinstance(raw_results, list):
            for i, res in enumerate(raw_results):
                context_block += f"\n--- FONTE {i+1} ---\n"
                # Se è un dizionario (ha URL e Content)
                if isinstance(res, dict):
                    context_block += f"URL: {res.get('url', 'N/D')}\n"
                    context_block += f"CONTENUTO: {res.get('content', 'N/D')}\n"
                # Se è una stringa (testo nudo)
                elif isinstance(res, str):
                    context_block += f"CONTENUTO: {res}\n"
            print(f"[DEBUG] Trovati {len(raw_results)} risultati.")
        else:
            context_block = str(raw_results)
            
    except Exception as e:
        context_block = f"ERRORE RICERCA: {str(e)}"
        print(f"[ERROR] Tavily: {e}")

    # C. Generazione Finale
    chef_chain = prompt_chef_final | llm
    risposta = chef_chain.invoke({
        "n_persone": stato.n_persone,
        "vincoli": vincoli_str,
        "context": context_block,
        "ingredienti": nomi_ing
    })
    return risposta.content

# --- 3. INTERVISTATORE ---
prompt_domanda = ChatPromptTemplate.from_messages([
    ("system", "Chiedi n_persone o vincoli mancanti. Stato attuale: {stato_corrente}"),
    ("user", "Cosa chiedere?")
])
chain_domanda = prompt_domanda | llm

# --- MASTER FUNCTION ---
def processa_messaggio(input_utente: str, stato_attuale: ProfiloUtente):
    try:
        nuovo_stato = chain_estrazione.invoke({
            "format_instructions": parser_stato.get_format_instructions(),
            "stato_precedente": stato_to_text(stato_attuale),
            "input_utente": input_utente
        })
    except:
        return "Non ho capito, puoi ripetere?", stato_attuale

    # Router: Check Mandatory Slots
    info_ok = (nuovo_stato.n_persone and 
               nuovo_stato.vincoli_alimentari_verificati and 
               len(nuovo_stato.ingredienti) >= 2)

    if info_ok:
        return run_chef_rag(nuovo_stato), nuovo_stato
    else:
        risposta = chain_domanda.invoke({"stato_corrente": stato_to_text(nuovo_stato)})
        return risposta.content, nuovo_stato