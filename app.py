import streamlit as st
from logic import processa_messaggio
from state import ProfiloUtente

# Configurazione Pagina
st.set_page_config(page_title="AI Kitchen Agent", layout="wide")

st.title("👨‍🍳 AI Kitchen Agent")
st.markdown("Dimmi cosa hai in frigo, e ti dirò cosa cucinare!")

# Inizializzazione Session State (Memoria Persistente Client-Side)
if "stato_profilo" not in st.session_state:
    st.session_state.stato_profilo = ProfiloUtente()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: LO STATO DELL'AGENTE ---
with st.sidebar:
    st.header("🧠 Memoria Agente")
    st.info("Qui vedi cosa l'AI ha 'capito' e memorizzato.")
    
    st.subheader("🛒 Dispensa Rilevata")
    if st.session_state.stato_profilo.ingredienti:
        for ing in st.session_state.stato_profilo.ingredienti:
            scadenza = "⚠️" if ing.scadenza_vicina else ""
            st.markdown(f"- **{ing.nome}** ({ing.quantita or 'qta ignota'}) {scadenza}")
    else:
        st.write("Nessun ingrediente rilevato.")
        
    st.subheader("🚫 Vincoli & Gusti")
    if st.session_state.stato_profilo.vincoli_alimentari:
        for v in st.session_state.stato_profilo.vincoli_alimentari:
            st.markdown(f"- {v}")
    else:
        st.write("Nessun vincolo noto.")
        
    st.divider()
    # Debug JSON raw
    with st.expander("Vedi JSON Raw"):
        st.json(st.session_state.stato_profilo.model_dump())

# --- CHAT INTERFACE ---
# Mostra cronologia
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input Utente
if prompt := st.chat_input("Es: Ho zucchine, uova e farina..."):
    # 1. Mostra messaggio utente
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Elaborazione Backend
    with st.spinner("L'agente sta ragionando..."):
        risposta_ai, nuovo_stato = processa_messaggio(prompt, st.session_state.stato_profilo)
        
        # Aggiorna lo stato in sessione
        st.session_state.stato_profilo = nuovo_stato

    # 3. Mostra risposta AI
    st.session_state.messages.append({"role": "assistant", "content": risposta_ai})
    with st.chat_message("assistant"):
        st.markdown(risposta_ai)
    
    # 4. Forza refresh per aggiornare la sidebar immediatamente
    st.rerun()