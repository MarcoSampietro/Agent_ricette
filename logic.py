import os
from dotenv import load_dotenv

# 1. Caricamento ambiente immediato
load_dotenv()

from typing import List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults
from state import ProfiloUtente, stato_to_text

# --- CONFIGURAZIONE TOOL ---
# Usiamo TavilySearchResults per massimizzare la compatibilità
search_tool = TavilySearchResults(
    max_results=5, 
    search_depth="advanced"
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

# --- 2. LOGICA CHEF (RAG ESPANSO) ---

# Fase A: Generatore di Query (Strategia: Cerca la categoria, non ogni singolo ingrediente)
prompt_search_query = ChatPromptTemplate.from_messages([
    ("system", """Sei un esperto di SEO culinaria. 
    L'utente vuole ricette Mediterranee con questi vincoli: {vincoli}.
    
    COMPITO: Genera una query di ricerca generica ma efficace per trovare ricette REALI su blog di cucina.
    Esempio: Se l'utente ha riso e verdure ed è vegano/celiaco, cerca 'migliori ricette mediterranee vegane e senza glutine con riso e legumi'.
    NON essere troppo specifico con tutti gli ingredienti o Tavily non troverà nulla."""),
])

# Fase B: Chef (Il "Sintetizzatore")
prompt_chef_final = ChatPromptTemplate.from_messages([
    ("system", """Sei lo Chef AI Mediterraneo. Il tuo compito è proporre ricette basate su RISULTATI WEB REALI.
    
    REGOLE DI GENERAZIONE:
    1. Prendi le ricette trovate nel 'CONTESTO DI RICERCA' e ADATTALE al 100% all'inventario dell'utente.
    2. Se un sito propone una ricetta con cipolla ma l'utente non ce l'ha, omettila e spiega l'adattamento.
    3. DEVI citare l'URL della fonte originale per ogni ricetta.
    4. Sii creativo: se trovi una ricetta di 'Paella vegetale', adattala usando i fagioli o le lenticchie dell'utente.
    
    INVENTARIO REALE (USA SOLO QUESTI): {inventario_reale}
    VINCOLI: {vincoli} per {n_persone} persone.
    
    CONTESTO DI RICERCA RECUPERATO:
    {context}
    """),
    ("user", "Proponi 3 ricette adattate dai risultati web.")
])

def run_chef_rag(stato: ProfiloUtente):
    nomi_ing = ", ".join([i.nome for i in stato.ingredienti])
    vincoli_str = ", ".join(stato.vincoli_alimentari) if stato.vincoli_alimentari else "Nessuno"
    
    # 1. GENERIAMO LA QUERY (Più ampia per garantire risultati)
    query_chain = prompt_search_query | llm
    search_query = query_chain.invoke({"vincoli": vincoli_str}).content
    print(f"\n[DEBUG] Query inviata a Tavily: {search_query}")

    # 2. ESEGUIAMO TAVILY
    context_block = ""
    try:
        raw_results = search_tool.invoke({"query": search_query})
        if raw_results:
            for i, res in enumerate(raw_results):
                if isinstance(res, dict):
                    context_block += f"\n--- FONTE {i+1} ---\nURL: {res.get('url')}\nCONTENUTO: {res.get('content')}\n"
                else:
                    context_block += f"\n--- FONTE {i+1} ---\nCONTENUTO: {str(res)}\n"
        else:
            context_block = "Nessun risultato trovato. (Nota per lo Chef: usa la tua conoscenza ma scusati per la mancanza di fonti)."
    except Exception as e:
        context_block = f"Errore tecnico: {e}"

    # 3. GENERAZIONE FINALE
    chef_chain = prompt_chef_final | llm
    risposta = chef_chain.invoke({
        "n_persone": stato.n_persone,
        "vincoli": vincoli_str,
        "inventario_reale": nomi_ing,
        "context": context_block
    })
    
    return risposta.content

# --- 3. INTERVISTATORE (Invariato) ---
def processa_messaggio(input_utente: str, stato_attuale: ProfiloUtente):
    try:
        nuovo_stato = chain_estrazione.invoke({
            "format_instructions": parser_stato.get_format_instructions(),
            "stato_precedente": stato_to_text(stato_attuale),
            "input_utente": input_utente
        })
    except:
        return "Non ho capito, puoi ripetere?", stato_attuale

    if nuovo_stato.n_persone and nuovo_stato.vincoli_alimentari_verificati and len(nuovo_stato.ingredienti) >= 2:
        return run_chef_rag(nuovo_stato), nuovo_stato
    else:
        risposta_domanda = llm.invoke(f"Sei un assistente di cucina. Lo stato è {stato_to_text(nuovo_stato)}. Fai una sola domanda per sapere persone o vincoli.")
        return risposta_domanda.content, nuovo_stato