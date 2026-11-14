

import streamlit as st
import psycopg2
import base64


# ==========================================
# ADATBÁZIS KAPCSOLAT
# ==========================================

def get_connection():
    return psycopg2.connect(
        st.secrets["DB_URL"],
        connect_timeout=5
    )


def init_database():
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dogs (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        size TEXT,
                        energy_level INTEGER,
                        needs_garden BOOLEAN DEFAULT FALSE,
                        kid_friendly BOOLEAN DEFAULT FALSE,
                        experience_required BOOLEAN DEFAULT FALSE,
                        shelter_name TEXT,
                        shelter_contact TEXT,
                        image_data TEXT
                    )
                """)
    finally:
        conn.close()


# ==========================================
# KUTYA MENTÉSE
# ==========================================

def save_dog(name, size, energy, garden, kids, exp,
             shelter_name, shelter_contact, image_base64):

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO dogs (
                        name, size, energy_level,
                        needs_garden, kid_friendly,
                        experience_required, shelter_name,
                        shelter_contact, image_data
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    name, size, energy, garden, kids, exp,
                    shelter_name, shelter_contact, image_base64
                ))
    finally:
        conn.close()


# ==========================================
# KUTYA TÖRLÉSE
# ==========================================

def delete_dog(dog_id):

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM dogs WHERE id = %s",
                    (dog_id,)
                )
    finally:
        conn.close()


# ==========================================
# KUTYÁK LEKÉRDEZÉSE
# ==========================================

def get_all_dogs():

    conn = None

    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, size, energy_level,
                needs_garden, kid_friendly,
                experience_required, shelter_name,
                shelter_contact, image_data
                FROM dogs
                ORDER BY id DESC
            """)

            rows = cursor.fetchall()

        dogs = []

        for d in rows:
            dogs.append({
                "id": d[0],
                "name": d[1],
                "size": d[2],
                "energy_level": d[3],
                "needs_garden": d[4],
                "kid_friendly": d[5],
                "experience_required": d[6],
                "shelter_name": d[7] or "Nincs megadva",
                "shelter_contact": d[8] or "Nincs megadva",
                "image_data": d[9]
            })

        return dogs

    except Exception as e:
        st.error(f"Adatbázis hiba: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================================
# PÁROSÍTÁSI RENDSZER
# ==========================================

def calculate_match_score(
    dog, app_housing, app_work,
    app_garden, app_kids, app_exp
):

    if dog.get("needs_garden") and not app_garden:
        return 0

    if dog.get("experience_required") and not app_exp:
        return 0

    if app_kids and not dog.get("kid_friendly"):
        return 0

    score = 3

    if not (
        dog.get("energy_level", 3) >= 4
        and app_work > 6
        and app_housing == "Lakás"
    ):
        score += 1

    if not (
        dog.get("size") == "Nagy (L)"
        and app_housing == "Lakás"
        and not app_garden
    ):
        score += 1

    return int(score / 5 * 100)


# ==========================================
# KUTYA ADATLAP
# ==========================================

def render_dog_card(dog, score):

    with st.container(border=True):

        col1, col2 = st.columns((1, 2))

        with col1:

            if dog.get("image_data"):
                try:
                    st.image(
                        base64.b64decode(dog["image_data"]),
                        use_container_width=True
                    )
                except Exception:
                    st.warning("A kép nem jeleníthető meg.")
            else:
                st.markdown("🐕")
                st.caption("Nincs fotó")

        with col2:

            badge = (
                "🥇 Tökéletes párosítás!"
                if score == 100
                else "👍 Jó választás lehet"
            )

            st.subheader(f"{dog['name']} – {score}%")

            st.write(badge)

            st.write(f"**Méret:** {dog['size']}")

            st.write(
                f"**Energiaszint:** {dog['energy_level']}/5"
            )

            st.write(
                f"**Kert igény:** "
                f"{'Igen' if dog['needs_garden'] else 'Nem'}"
            )

            st.write(
                f"**Gyerekbarát:** "
                f"{'Igen' if dog['kid_friendly'] else 'Nem'}"
            )

            st.write(
                f"**Tapasztalt gazdit igényel:** "
                f"{'Igen' if dog['experience_required'] else 'Nem'}"
            )

            st.write(f"🏠 **Menhely:** {dog['shelter_name']}")

            st.write(
                f"📞 **Elérhetőség:** {dog['shelter_contact']}"
            )


# ==========================================
# ÉLES KUTYAKERESŐ
# ==========================================

def render_live_search():

    st.header("🔍 Találd meg a tökéletes társat!")

    col1, col2 = st.columns(2)

    with col1:

        app_name = st.text_input("Jelentkező neve")

        app_housing = st.selectbox(
            "Lakóhely típusa",
            ("Lakás", "Kertes ház")
        )

        app_work = st.slider(
            "Napi távol töltött órák",
            0, 12, 4
        )

    with col2:

        app_garden = st.checkbox(
            "Van saját, biztonságos kertem"
        )

        app_kids = st.checkbox(
            "Van kisgyermek a családban"
        )

        app_exp = st.checkbox(
            "Tapasztalt kutyatartó vagyok"
        )

    if st.button(
        "🔍 Hozzám illő kutyák keresése",
        type="primary"
    ):

        dogs = get_all_dogs()

        if not dogs:
            st.info("Jelenleg nincs feltöltött kutya.")
            return

        matches = []

        for dog in dogs:

            score = calculate_match_score(
                dog, app_housing, app_work,
                app_garden, app_kids, app_exp
            )

            if score >= 60:
                matches.append((score, dog))

        matches.sort(
            key=lambda item: item[0],
            reverse=True
        )

        st.subheader(
            f"✨ Riport: {app_name or 'Jelentkező'} részére"
        )

        if not matches:
            st.warning("Nincs megfelelő kutyatalálat.")
            return

        st.success(f"{len(matches)} kutyát találtunk!")

        for score, dog in matches:
            render_dog_card(dog, score)


# ==========================================
# DEMÓ MÓD
# ==========================================

def render_demo_tab():

    st.header("🧪 Interaktív Demó Mód")

    st.info(
        "Próbáld ki a rendszert jelszó nélkül! "
        "A demó kutyák csak ebben a munkamenetben jelennek meg."
    )

    with st.expander("➕ Próbakutya feltöltése", expanded=True):

        with st.form("demo_form", clear_on_submit=True):

            name = st.text_input("Tesztkutya neve")

            shelter = st.text_input(
                "Szervezet neve",
                "Teszt Menhely"
            )

            contact = st.text_input(
                "Elérhetőség",
                "+36 20 111 2222"
            )

            size = st.selectbox(
                "Kutya mérete",
                ("Kicsi (S)", "Közepes (M)", "Nagy (L)")
            )

            energy = st.slider("Energiaszint", 1, 5, 3)

            image_file = st.file_uploader(
                "Kutya fotója",
                type=["jpg", "jpeg", "png"]
            )

            garden = st.checkbox(
                "Kizárólag kertes házba költözhet"
            )

            kids = st.checkbox("Gyerekbarát")

            exp = st.checkbox("Tapasztalt gazdit igényel")

            submitted = st.form_submit_button(
                "🧪 Próbakutya hozzáadása"
            )

        if submitted:

            if not name.strip():
                st.error("Add meg a kutya nevét!")

            else:

                image_data = (
                    base64.b64encode(
                        image_file.getvalue()
                    ).decode("utf-8")
                    if image_file else None
                )

                st.session_state.demo_dogs.insert(
                    0,
                    {
                        "name": name.strip(),
                        "size": size,
                        "energy_level": energy,
                        "needs_garden": garden,
                        "kid_friendly": kids,
                        "experience_required": exp,
                        "shelter_name": shelter,
                        "shelter_contact": contact,
                        "image_data": image_data
                    }
                )

                st.success(f"{name} hozzáadva!")

    st.divider()

    st.subheader("🔍 Demó párosítás")

    col1, col2 = st.columns(2)

    with col1:

        housing = st.selectbox(
            "Gazdi lakóhelye",
            ("Lakás", "Kertes ház")
        )

        work = st.slider(
            "Napi távol töltött órák",
            0, 12, 4
        )

    with col2:

        garden = st.checkbox("Van saját kertje")

        kids = st.checkbox("Van kisgyermeke")

        exp = st.checkbox("Tapasztalt kutyatartó")

    if st.button(
        "🚀 Demó párosítás indítása",
        type="primary"
    ):

        matches = []

        for dog in st.session_state.demo_dogs:

            score = calculate_match_score(
                dog, housing, work, garden, kids, exp
            )

            if score >= 60:
                matches.append((score, dog))

        matches.sort(
            key=lambda item: item[0],
            reverse=True
        )

        if not matches:
            st.warning("Nincs megfelelő demó kutya.")
            return

        for score, dog in matches:
            render_dog_card(dog, score)


# ==========================================
# MENHELYI ADMIN
# ==========================================

def render_admin_tab():

    st.header("🔐 Menhelyi nyilvántartás")

    password = st.secrets.get(
        "MENHELY_JELSZO",
        ""
    )

    if not password:
        st.error("Nincs beállítva a menhelyi jelszó!")
        return

    password_input = st.text_input(
        "Menhelyi jelszó",
        type="password"
    )

    if not password_input:
        st.info("A felület jelszóval védett.")
        return

    if password_input != password:
        st.error("Hibás jelszó!")
        return

    st.success("🔓 Sikeres bejelentkezés!")

    with st.form("admin_dog_form", clear_on_submit=True):

        name = st.text_input("Kutya neve")

        shelter = st.text_input("Menhely neve")

        contact = st.text_input("Elérhetőség")

        size = st.selectbox(
            "Kutya mérete",
            ("Kicsi (S)", "Közepes (M)", "Nagy (L)")
        )

        energy = st.slider("Energiaszint", 1, 5, 3)

        image_file = st.file_uploader(
            "Kutya fotója",
            type=["jpg", "jpeg", "png"]
        )

        garden = st.checkbox(
            "Kizárólag kertes házba költözhet"
        )

        kids = st.checkbox("Gyerekbarát")

        exp = st.checkbox("Tapasztalt gazdit igényel")

        submitted = st.form_submit_button("💾 Kutya mentése")

    if submitted:

        if not name.strip():
            st.error("Add meg a kutya nevét!")

        else:

            image_data = (
                base64.b64encode(
                    image_file.getvalue()
                ).decode("utf-8")
                if image_file else None
            )

            try:

                save_dog(
                    name.strip(), size, energy,
                    garden, kids, exp,
                    shelter, contact, image_data
                )

                st.success(f"{name} sikeresen elmentve!")

                st.rerun()

            except Exception as e:
                st.error(f"Mentési hiba: {e}")

    st.divider()

    st.subheader("🐾 Feltöltött kutyák")

    dogs = get_all_dogs()

    if not dogs:
        st.info("Nincs még feltöltött kutya.")

    for dog in dogs:

        col1, col2 = st.columns((3, 1))

        with col1:
            st.write(
                f"🐾 **{dog['name']}** – {dog['shelter_name']}"
            )

        with col2:

            if st.button(
                "🗑️ Törlés",
                key=f"delete_{dog['id']}"
            ):

                try:

                    delete_dog(dog["id"])

                    st.success("Kutya törölve!")

                    st.rerun()

                except Exception as e:
                    st.error(f"Törlési hiba: {e}")


# ==========================================
# FŐPROGRAM
# ==========================================

def main():

    st.set_page_config(
        page_title="Gazdikereső",
        page_icon="🐶",
        layout="wide"
    )

    if "demo_dogs" not in st.session_state:
        st.session_state.demo_dogs = []

    st.title("🐶 Gazdikereső")

    st.subheader(
        "Találd meg a hozzád legjobban illő négylábú társat!"
    )

    st.write(
        "Segítünk összekötni a gazdijelölteket "
        "a szerető otthonra váró kutyákkal."
    )

    try:
        init_database()
    except Exception as e:
        st.warning(
            f"Az adatbázis nem érhető el: {e}"
        )

    tab1, tab2, tab3 = st.tabs([
        "🔍 Kutyakereső",
        "🧪 Demó mód",
        "🔐 Menhelyi admin"
    ])

    with tab1:
        render_live_search()

    with tab2:
        render_demo_tab()

    with tab3:
        render_admin_tab()


if __name__ == "__main__":
    main()
