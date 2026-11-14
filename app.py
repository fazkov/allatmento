import psycopg2
import base64
import streamlit as st

# --- BEÁLLÍTÁSOK ---
MENHELY_JELSZO = "menhely2026" # Ezt a jelszót bármikor átírhatod!

# --- FELHŐS ADATBÁZIS KEZELÉS (Supabase / PostgreSQL) ---
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
    for row in rows:
        dogs.append({
            "id": row[0],
            "name": row[1],
            "size": row[2],
            "energy_level": row[3],
            "needs_garden": row[4],
            "kid_friendly": row[5],
            "experience_required": row[6],
            "shelter_name": row[7] if row[7] else "Nincs megadva",
            "shelter_contact": row[8] if row[8] else "Nincs megadva",
            "image_data": row[9]
        })
    return dogs

# --- PÁROSÍTÓ ALGORITMUS ---
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

# --- WEBFELÜLET ---
def main():
    st.set_page_config(page_title="Intelligens Állatmentő Rendszer", page_icon="🐾", layout="centered")

    st.title("🐾 Intelligens Állatmentő & Párosító Rendszer")
    st.write("Nyugati mintára épült menhelyi menedzsment és gazdi-matching szoftver.")

    tab1, tab2 = st.tabs(["📋 Gazdi Kereső (Matching)", "🔒 Menhelyi Nyilvántartás (Admin)"])

    # --- 1. FÜL: PUBLIKUS GAZDI KERESŐ ---
    with tab1:
        st.header("Találd meg a tökéletes társat!")
        st.write("Töltsd ki az élethelyzeted, és az algoritmus megmutatja a hozzád illő kutyákat.")

        col1, col2 = st.columns(2)
        with col1:
            app_name = st.text_input("Jelentkező neve", "Kovács Péter")
            app_housing = st.selectbox("Lakóhely típusa", ["Lakás", "Kertes ház"])
            app_work = st.slider("Mennyi időt töltesz távol otthonról naponta? (óra)", 0, 12, 4)
        
        with col2:
            app_garden = st.checkbox("Van saját, biztonságos kertem", value=False)
            app_kids = st.checkbox("Van kisgyermek a családban", value=False)
            app_exp = st.checkbox("Tapasztalt kutyatartó vagyok (volt már problémás/nagytestű kutyám)", value=False)

        if st.button("🔍 Hozzám illő kutyák keresése", type="primary"):
            dogs = get_all_dogs()
            if not dogs:
                st.info("A menhely adatbázisa jelenleg üres. A menhelyi munkatársak hamarosan feltöltik a védenceket!")
            else:
                st.subheader(f"✨ Riport: {app_name} részére")
                
                matches = []
                for dog in dogs:
                    score = calculate_match_score(dog, app_housing, app_work, app_garden, app_kids, app_exp)
                    if score >= 60:
                        matches.append((dog, score))
                
                matches.sort(key=lambda x: x[1], reverse=True)

                if not matches:
                    st.warning("⚠️ Sajnos jelenleg nincs olyan kutyánk, aki biztonsággal passzolna az élethelyzetedhez.")
                else:
                    for dog, score in matches:
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

    # --- 2. FÜL: JELSZÓVAL VÉDETT MENHELYI ADMIN ---
    with tab2:
        st.header("Menhelyi munkatársi felület")
        password_input = st.text_input("Add meg a menhelyi jelszót a szerkesztéshez:", type="password")

        if password_input == MENHELY_JELSZO:
            st.success("🔓 Sikeres bejelentkezés!")
            
            st.subheader("➕ Új mentett kutya regisztrálása")
            with st.form("dog_form", clear_on_submit=True):
                dog_name = st.text_input("Kutya neve / azonosítója", placeholder="Pl.: Bodri, Rex, 12-es kennel")
                
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    shelter_name = st.text_input("Menhely / Alapítvány neve", placeholder="Pl.: Érdi Állatvédők")
                with col_s2:
                    shelter_contact = st.text_input("Elérhetőség (Telefon / E-mail)", placeholder="Pl.: +36 30 123 4567")

                dog_size = st.selectbox("Kutya mérete", ["Kicsi (S)", "Közepes (M)", "Nagy (L)"])
                dog_energy = st.slider("Energiaszint (1: lusta/idős - 5: hiperaktív)", 1, 5, 3)
                uploaded_file = st.file_uploader("Kutya fotójának feltöltése (JPG, PNG)", type=["jpg", "jpeg", "png"])
                
                st.write("Speciális igények:")
                dog_garden = st.checkbox("Kizárólag kertes házba költözhet")
                dog_kids = st.checkbox("Gyerekbarát (kisgyerekes családba is vihető)")
                dog_exp = st.checkbox("Tapasztalt gazdit igényel")

                submitted = st.form_submit_button("💾 Kutya és adatok mentése")
                if submitted:
                    if dog_name.strip() == "":
                        st.error("Kérjük, adj meg egy nevet a kutyának!")
                    else:
                        img_b64 = None
                        if uploaded_file is not None:
                            img_b64 = base64.b64encode(uploaded_file.read()).decode("utf-8")
                        save_dog(dog_name, dog_size, dog_energy, dog_garden, dog_kids, dog_exp, shelter_name, shelter_contact, img_b64)
                        st.success(f"🎉 **{dog_name}** sikeresen elmentve a felhős adatbázisba!")

            st.divider()
            st.subheader("🏠 Jelenlegi állomány kezelése (Törlés / Gazdisodás)")
            current_dogs = get_all_dogs()
            if not current_dogs:
                st.text("Az adatbázis még nem tartalmaz kutyát.")
            else:
                for d in current_dogs:
                    col_name, col_del = st.columns([4, 1])
                    with col_name:
                        st.write(f"🐾 **{d['name']}** — *{d['shelter_name']}* ({d['size']})")
                    with col_del:
                        if st.button("🗑️ Törlés", key=f"del_{d['id']}"):
                            delete_dog(d['id'])
                            st.rerun()
        elif password_input != "":
            st.error("❌ Hibás jelszó! A menhelyi adatok módosításához kérj hozzáférést az adminisztrátortól.")
        else:
            st.info("ℹ️ Ez a felület jelszóval védett. A látogatók az első fülön tudnak kutyát keresni.")

if __name__ == "__main__":
    main()
