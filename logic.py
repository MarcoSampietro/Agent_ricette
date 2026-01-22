import os
from dotenv import load_dotenv
from typing import List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_tavily import TavilySearch
from state import ProfiloUtente, stato_to_text

load_dotenv()

# --- SETUP MODELLI ---
# LLM 1: Lo Chef e Ricercatore (Llama 3.3 70B)
llm_chef = ChatGroq(
    temperature=0.1, 
    model_name="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# LLM 2: Il Critico Gastronomico (GPT-OSS 120B come richiesto)
llm_critic = ChatGroq(
    temperature=0, 
    model_name="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY")
)

# Tool di ricerca
search_tool = TavilySearch(max_results=3)

# --- TOKEN TRACKING ---
def track_tokens(stato: ProfiloUtente, response):
    if hasattr(response, 'response_metadata'):
        usage = response.response_metadata.get('token_usage', {})
        tokens = usage.get('total_tokens', 0)
        stato.token_totali += tokens
        stato.ultima_risposta_costo = tokens
    return stato

# --- AGENTE 1: ESTRATTORE ---
parser_stato = PydanticOutputParser(pydantic_object=ProfiloUtente)
prompt_estrazione = ChatPromptTemplate.from_messages([
    ("system", "Sei un analista dati. Aggiorna lo stato Pydantic. Se l'utente specifica vincoli (vegano, celiaco), imposta 'vincoli_alimentari_verificati' = True. {format_instructions}"),
    ("user", "STATO PRECEDENTE: {stato_precedente}\nINPUT: {input_utente}")
])

# --- AGENTE 2: CRITICO (GPT-OSS 120B) ---
prompt_critico = ChatPromptTemplate.from_messages([
    ("system", """Sei un Critico Gastronomico Infallibile (Modello 120B). 
    Analizza la ricetta confrontandola rigorosamente con l'INVENTARIO REALE.

    CRITERI DI BOCCIATURA (DEVI ESSERE SPIETATO):
    1. MANCANZA INGREDIENTI: Se la ricetta usa 'Riso' ma non è in inventario, o 'Cipolla' ma non c'è, BOCCIA.
    2. VIOLAZIONE VINCOLI: Pasta di grano per celiaci? BOCCIA. Latticini/Carne per vegani? BOCCIA.
    3. COERENZA: Risotto senza riso tra gli ingredienti? BOCCIA.

    Rispondi solo: 'APPROVATA' oppure 'BOCCIATA: [motivo analitico]'."""),
    ("user", "INVENTARIO: {inventario}\nVINCOLI: {vincoli}\nRICETTA: {ricetta}")
])

# --- AGENTE 3: CHEF (Llama 3.3 70B + RAG) ---
prompt_chef = ChatPromptTemplate.from_messages([
    ("system", """Sei lo Chef Mediterraneo. 
    REGOLE: 
    1. Usa SOLO gli ingredienti in inventario.
    2. Basati sui RISULTATI WEB per i passaggi, ma adatta gli ingredienti.
    3. Se sei per celiaci, usa il Riso (se presente) invece della pasta di grano.
    
    INVENTARIO: {inventario}
    RISULTATI WEB: {context}"""),
    ("user", "Proponi 3 ricette per {n_persone} persone (Vincoli: {vincoli}).")
])

def run_chef_rag_and_critic(stato: ProfiloUtente):
    # 1. WEB SEARCH
    nomi_ing = ", ".join([i.nome for i in stato.ingredienti[:4]])
    query = f"ricette mediterranee vegane e gluten-free con {nomi_ing}"
    try:
        search_res = search_tool.invoke(query)
        context = str(search_res)
    except:
        context = "Nessun risultato web trovato."

    # 2. GENERAZIONE CHEF (Llama 70B)
    chef_input = prompt_chef.format(
        inventario=stato_to_text(stato),
        context=context,
        n_persone=stato.n_persone,
        vincoli=", ".join(stato.vincoli_alimentari)
    )
    res_chef = llm_chef.invoke(chef_input)
    track_tokens(stato, res_chef)
    ricetta = res_chef.content

    # 3. REVISIONE CRITICO (GPT 120B)
    critic_input = prompt_critico.format(
        inventario=stato_to_text(stato),
        vincoli=", ".join(stato.vincoli_alimentari),
        ricetta=ricetta
    )
    res_critic = llm_critic.invoke(critic_input)
    track_tokens(stato, res_critic)
    
    if "BOCCIATA" in res_critic.content:
        # Retry logic forzando lo Chef a correggere
        repair_input = f"IL CRITICO HA BOCCIATO LA RICETTA: {res_critic.content}\nCORREGGI RIGOROSAMENTE usando SOLO l'inventario: {stato_to_text(stato)}"
        res_repair = llm_chef.invoke(repair_input)
        track_tokens(stato, res_repair)
        return f"*(Revisione Critico 120B: {res_critic.content})*\n\n{res_repair.content}"
    
    return ricetta

def processa_messaggio(input_utente: str, stato_attuale: ProfiloUtente):
    if stato_attuale.token_totali > stato_attuale.budget_token:
        return "🛑 Budget token esaurito.", stato_attuale

    try:
        # ESTRAZIONE
        raw_extraction = llm_chef.invoke(prompt_estrazione.format(
            format_instructions=parser_stato.get_format_instructions(),
            stato_precedente=stato_to_text(stato_attuale),
            input_utente=input_utente
        ))
        track_tokens(stato_attuale, raw_extraction)
        nuovo_stato = parser_stato.parse(raw_extraction.content)
        nuovo_stato.token_totali = stato_attuale.token_totali
        nuovo_stato.budget_token = stato_attuale.budget_token

        # ROUTER
        info_complete = (nuovo_stato.n_persone and nuovo_stato.vincoli_alimentari_verificati)
        
        if info_complete or "ricetta" in input_utente.lower():
            risposta = run_chef_rag_and_critic(nuovo_stato)
            return risposta, nuovo_stato
        else:
            res_domanda = llm_chef.invoke(f"Fai una domanda per sapere commensali o allergie. Stato: {stato_to_text(nuovo_stato)}")
            track_tokens(nuovo_stato, res_domanda)
            return res_domanda.content, nuovo_stato

    except Exception as e:
        return f"Errore tecnico: {str(e)}", stato_attuale