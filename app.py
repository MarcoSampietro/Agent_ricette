import streamlit as st
from logic import processa_messaggio
from state import ProfiloUtente

st.set_page_config(page_title="Mediterranean Agent", layout="wide", page_icon="🍅")

if "stato_profilo" not in st.session_state:
    st.session_state.stato_profilo = ProfiloUtente()

if "messages" not in st.session_state:
    st.session_state.messages = []

# SIDEBAR: Monitoraggio Slot
with st.sidebar:
    st.header("🧠 Memoria Agente")
    
    # Mandatory Slots Check
    p = st.session_state.stato_profilo
    st.metric("Commensali", p.n_persone if p.n_persone else "???")
    
    status_vincoli = "✅ Verificati" if p.vincoli_alimentari_verificati else "❌ Da chiedere"
    st.write(f"**Vincoli:** {status_vincoli}")
    
    st.divider()
    st.subheader("🛒 Dispensa")
    for ing in p.ingredienti:
        st.caption(f"- {ing.nome} ({ing.quantita or 'q.b.'})")
    
    if st.button("Pulisci Memoria"):
        st.session_state.stato_profilo = ProfiloUtente()
        st.rerun()

# CHAT
st.title("👨‍🍳 AI Mediterranean Chef")
st.info("Fornisci ingredienti, numero di persone e allergie per sbloccare la ricerca ricette.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Es: Ho pasta e tonno, siamo in 2 e nessuna allergia"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Ragionando..."):
        risposta, nuovo_stato = processa_messaggio(prompt, st.session_state.stato_profilo)
        st.session_state.stato_profilo = nuovo_stato
        
        st.session_state.messages.append({"role": "assistant", "content": risposta})
        with st.chat_message("assistant"):
            st.markdown(risposta)
            
    st.rerun()