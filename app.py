    st.subheader("🐾 A menhely kutyái")
    try:
        dogs = get_all_dogs(shelter_id=shelter_id)
    except Exception as e:
        st.error(f"Adatbázis hiba: {e}")
        return

    if not dogs:
        st.info("Ehhez a menhelyhez még nincs feltöltött kutya.")
        return

    for dog in dogs:
        with st.container(border=True):
            col1, col2 = st.columns((3, 1))
            with col1:
                st.write(f"🐾 **{dog['name']}**")
                st.caption(dog["size"])
            with col2:
                if st.button("🗑️ Törlés", key=f"shelter_delete_{dog['id']}"):
                    st.session_state.shelter_confirm_delete = dog["id"]
            if st.session_state.get("shelter_confirm_delete") == dog["id"]:
                st.warning(f"Biztosan törlöd {dog['name']} adatlapját?")
                yes, no = st.columns(2)
                with yes:
                    if st.button("Igen, törlés", key=f"shelter_confirm_{dog['id']}"):
                        try:
                            deleted = delete_dog(dog["id"], shelter_id=shelter_id)
                            st.session_state.shelter_confirm_delete = None
                            if deleted:
                                st.success("Kutya sikeresen törölve.")
                            else:
                                st.error("A kutya nem található a saját menhelyi fiókban.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Törlési hiba: {e}")
                with no:
                    if st.button("Mégsem", key=f"shelter_cancel_{dog['id']}"):
                        st.session_state.shelter_confirm_delete = None
                        st.rerun()


# =====================================================
# 16. FŐPROGRAM
# =====================================================

def main():

    if "demo_dogs" not in st.session_state:
        st.session_state.demo_dogs = []

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = None

    if "shelter_logged_in" not in st.session_state:
        st.session_state.shelter_logged_in = False

    st.title(
        "🐶 Gazdikereső"
    )

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

        st.error(
            f"Az adatbázis nem érhető el: {e}"
        )

        st.info(
            "Ellenőrizd a DB_URL beállítását "
            "és az adatbázis elérhetőségét."
        )

        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Kutyakereső",
        "🧪 Demó mód",
        "🏠 Menhelyi belépés",
        "🔐 Adminisztrátor"
    ])

    with tab1:

        render_live_search()

    with tab2:

        render_demo_tab()

    with tab3:

        render_shelter_tab()

    with tab4:

        render_admin_tab()

# =====================================================
# 17. PROGRAM INDÍTÁSA
# =====================================================

if __name__ == "__main__":
    main()
