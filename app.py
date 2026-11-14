import psycopg2
import base64
import streamlit as st

MENHELY_JELSZO = "menhely2026"

def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

def save_dog(name, size, energy, garden, kids, exp, shelter_name, shelter_contact, image_base64):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dogs (name, size, energy_level, needs_garden, kid_friendly, experience_required, shelter_name, shelter_contact, image_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (name, size, energy, garden, kids, exp, shelter_name, shelter_contact, image_base64))
    conn.commit()
    cursor.close()
    conn.close()

def delete_dog(dog_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dogs WHERE id = %s", (dog_id,))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_dogs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, size, energy_level, needs_garden, kid_friendly, 
               experience_required, shelter_name, shelter_contact, image_data 
        FROM dogs ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    dogs = []
    for d_id, name, size, energy, garden, kids, exp, s_name, s_contact, img in rows:
        dogs.append({
            "id": d_id,
            "name": name,
            "size": size,
            "energy_level": energy,
            "needs_garden": garden,
            "kid_friendly": kids,
            "experience_required": exp,
            "shelter_name": s_name if s_name else "Nincs megadva",
            "shelter_contact": s_contact if s_contact else "Nincs megadva",
            "image_data": img
        })
    return dogs

def calculate_match_score(dog, app_housing, app_work, app_garden, app_kids, app_exp):
    score = 0
    total_criteria = 5

    if dog["needs_garden"] and not app_garden:
        return 0
    score += 1

    if dog["experience_required"] and not app_exp:
        return 0
    score += 1

    if app_kids and not dog["kid_friendly"]:
        return 0
    score += 1

    if dog["energy_level"] >= 4 and app_work > 6 and app_housing == "Lakás":
        pass
    else:
        score += 1

    if dog["size"] == "Nagy (L)" and app_housing == "Lakás" and not app_garden:
        pass
    else:
        score += 1

    return int((score / total_criteria) * 100)

def main():
    st.set_page_config(page_title="Intelligens Állatmentő Rendszer", page_icon="🐾", layout="centered")

    if "demo_dogs" not in st.session_state:
        st.session_state.demo_dogs = [
            {
                "name": "Morzsi (Demó Minta)",
                "size": "Kicsi (S)",
                "energy_level": 2,
                "needs_garden": False,
                "kid_friendly": True,
                "experience_required": False,
                "shelter_name": "Minta Állatmenhely",
                "shelter_contact": "+36 30 000 0000",
                "image_data": None
            },
            {
                "name": "Villám (Demó Minta)",
                "size": "Nagy (L)",
                "energy_level": 5,
                "needs_garden": True,
                "kid_friendly": False,
                "experience_required": True,
                "shelter_name": "Minta Állatmenhely",
                "shelter_contact": "+36 30 000 0000",
                "image_data": None
            }
        ]

    st.title("🐾 Intelligens Állatmentő & Párosító Rendszer")
    st.write("Nyugati mintára épült menhelyi menedzsment és gazdi-matching szoftver.")

    tab1, tab2, tab3 = st.tabs([
        "📋 Gazdi Kereső (Éles)", 
        "🧪 Demó Mód (Menhelyi kipróbálás)", 
        "🔒 Menhelyi Nyilvántartás (Admin)"
    ])

    with tab1:
        st.header("Találd meg a tökéletes társat!")
        st.write("Töltsd ki az élethelyzeted, és az algoritmus megmutatja a hozzád illő gazdikereső kutyákat.")

        col1, col2 = st.columns(2)
        with col1:
            app_name = st.text_input("Jelentkező neve", "Kovács Péter", key="live_name")
            app_housing = st.selectbox("Lakóhely típusa", ["Lakás", "Kertes ház"], key="live_house")
            app_work = st.slider("Mennyi időt töltesz távol otthonról naponta? (óra)", 0, 12, 4, key="live_work")
        
        with col2:
            app_garden = st.checkbox("Van saját, biztonságos kertem", value=False, key="live_garden")
            app_kids = st.checkbox("Van kisgyermek a családban", value=False, key="live_kids")
            app_exp = st.checkbox("Tapasztalt kutyatartó vagyok (volt már problémás/nagytestű kutyám)", value=False, key="live_exp")

        if st.button("🔍 Hozzám illő kutyák keresése", type="primary", key="live_search"):
            dogs = get_all_dogs()
            if not dogs:
                st.info("Az éles menhelyi adatbázis jelenleg üres. Próbáld ki a rendszert a középső **Demó Mód** fülön!")
            else:
                st.subheader(f"✨ Riport: {app_name} részére")
                
                matches = []
                for dog in dogs:
                    score = calculate_match_score(dog, app_housing, app_work, app_garden, app_kids, app_exp)
                    if score >= 60:
                        matches.append((score, dog))
                
                matches.sort(key=lambda item: item[0], reverse=True)

                if not matches:
                    st.warning("⚠️ Sajnos jelenleg nincs olyan kutyánk, aki biztonsággal passzolna az élethelyzetedhez.")
                else:
                    for score, dog in matches:
                        badge = "🥇 Tökéletes párosítás!" if score == 100 else "👍 Jó választás lehet"
                        
                        with st.container(border=True):
                            c_img, c_info = st.columns([1, 2])
                            with c_img:
                                if dog["image_data"]:
                                    st.image(base64.b64decode(dog["image_data"]), use_container_width=True)
                                else:
                                    st.markdown("🐕\n*(Nincs feltöltött fotó)*")
                            with c_info:
                                st.subheader(f"{dog['name']} — {score}% ({badge})")
                                st.write(f"**Méret:** {dog['size']} | **Energiaszint:** {dog['energy_level']}/5")
                                st.write(f"**Kert igény:** {'Igen' if dog['needs_garden'] else 'Nem'} | "
                                         f"**Gyerekbarát:** {'Igen' if dog['kid_friendly'] else 'Nem'} | "
                                         f"**Tapasztalatot igényel:** {'Igen' if dog['experience_required'] else 'Nem'}")
                                st.success(f"🏠 **Menhely / Szervezet:** {dog['shelter_name']}\n\n📞 **Elérhetőség:** {dog['shelter_contact']}")

    with tab2:
        st.header("🧪 Interaktív Demó Mód (Jelszó nélkül)")
        st.info("ℹ️ **Kedves Állatvédők!** Itt jelszó nélkül, szabadon kipróbálhatják a rendszer működését. Az itt feltöltött tesztkutyák nem kerülnek be az éles adatbázisba, csak az Önök böngészőjében jelennek meg a teszt erejéig.")

        with st.expander("➕ 1. Lépés: Próbakutya feltöltése (Kattintson a lenyitáshoz)", expanded=True):
            with st.form("demo_dog_form", clear_on_submit=True):
                d_name = st.text_input("Tesztkutya neve", placeholder="Pl.: Buksi")
                col_ds1, col_ds2 = st.columns(2)
                with col_ds1:
                    d_shelter = st.text_input("Szervezet neve", "Teszt Menhely")
                with col_ds2:
                    d_contact = st.text_input("Elérhetőség", "+36 20 111 2222")

                d_size = st.selectbox("Kutya mérete", ["Kicsi (S)", "Közepes (M)", "Nagy (L)"])
                d_energy = st.slider("Energiaszint", 1, 5, 3)
                d_file = st.file_uploader("Tesztfotó feltöltése (opcionális)", type=["jpg", "jpeg", "png"])
                
                d_garden = st.checkbox("Kizárólag kertes házba költözhet")
                d_kids = st.checkbox("Gyerekbarát")
                d_exp = st.checkbox("Tapasztalt gazdit igényel")

                if st.form_submit_button("🧪 Próbakutya hozzáadása a teszthez"):
                    if d_name.strip() == "":
                        st.error("Adjon meg egy nevet a tesztkutyának!")
                    else:
                        d_img = base64.b64encode(d_file.read()).decode("utf-8") if d_file else None
                        st.session_state.demo_dogs.insert(0, {
                            "name": d_name,
                            "size": d_size,
                            "energy_level": d_energy,
                            "needs_garden": d_garden,
                            "kid_friendly": d_kids,
                            "experience_required": d_exp,
                            "shelter_name": d_shelter,
                            "shelter_contact": d_contact,
                            "image_data": d_img
                        })
                        st.success(f"🎉 **{d_name}** bekerült a demó listába! Tesztelje le lejjebb a párosítást!")

        st.divider()
        st.subheader("🔍 2. Lépés: Tesztelje a párosító algoritmust!")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            demo_housing = st.selectbox("Teszt gazdi lakóhelye", ["Lakás", "Kertes ház"])
            demo_work = st.slider("Napi távol töltött órák", 0, 12, 4)
        with col_d2:
            demo_garden = st.checkbox("Van saját kertje")
            demo_kids = st.checkbox("Van kisgyermeke")
            demo_exp = st.checkbox("Tapasztalt kutyatartó")

        if st.button("🚀 Demó párosítás indítása", type="primary"):
            demo_matches = []
            for dog in st.session_state.demo_dogs:
