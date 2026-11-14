import streamlit as st

st.set_page_config(page_title="Intelligens Állatmentő", page_icon="🐾")
st.title("🐾 Intelligens Állatmentő & Párosító Rendszer")
st.success("Siker! Az élő weboldal és a Demó Mód hibátlanul működik!")

tab1, tab2 = st.tabs(("📋 Gazdi Kereső", "🧪 Demó Mód"))

with tab1:
    st.write("Itt fognak megjelenni a gazdikereső kutyák.")

with tab2:
    st.header("Demó Mód kipróbálása")
    nev = st.text_input("Kutya neve", "Bodri")
    if st.button("Teszt mentés"):
        st.balloons()
        st.info(f"{nev} sikeresen tesztelve!")
