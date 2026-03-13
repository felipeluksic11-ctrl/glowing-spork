import streamlit as st
import pandas as pd
import os
from datetime import datetime

LANZAMIENTOS_CSV = "lanzamientos.csv"
FUENTES_CSV = "fuentes_lanzamientos.csv"

COLORES_STATUS_FUENTE = {
    "ok": {"color": "#2ecc71", "icon": "🟢", "label": "Activo"},
    "warning": {"color": "#f39c12", "icon": "🟡", "label": "Degradado"},
    "error": {"color": "#e74c3c", "icon": "🔴", "label": "Error"},
    "unknown": {"color": "#95a5a6", "icon": "⚪", "label": "Sin datos"},
}

COLORES_ETAPA = {
    "Preventa": "#9b59b6",
    "Lanzamiento": "#2ecc71",
    "En construcción": "#f39c12",
    "Próximamente": "#3498db",
}

PORTALES_INMOBILIARIOS = [
    # --- Portales de listings (scraping directo) ---
    {"portal": "La Haus", "dominio": "lahaus.mx", "tipo": "Portal listings", "cobertura": "Nacional", "enfoque": "Plataforma líder en preventa de desarrollos nuevos, alta tasa de datos"},
    {"portal": "Inmuebles24", "dominio": "inmuebles24.com", "tipo": "Portal listings", "cobertura": "Nacional", "enfoque": "Mayor volumen de listings, preventa y desarrollos nuevos"},
    {"portal": "Lamudi", "dominio": "lamudi.com.mx", "tipo": "Portal listings", "cobertura": "Nacional", "enfoque": "Fuerte en preventa y desarrollos premium"},
    {"portal": "Behome", "dominio": "behome.mx", "tipo": "Portal listings", "cobertura": "Riviera Maya / Cancún", "enfoque": "Especializado en Riviera Maya, preventa turística y residencial"},
    {"portal": "Monterrey Skyline", "dominio": "monterreyskyline.com", "tipo": "Portal listings", "cobertura": "Monterrey / Nuevo León", "enfoque": "Análisis detallado de preventas y precios por m2 en MTY"},
    {"portal": "Propiedades.com", "dominio": "propiedades.com", "tipo": "Portal listings", "cobertura": "Nacional", "enfoque": "Catálogo amplio de desarrollos nuevos"},
    {"portal": "Casas y Terrenos", "dominio": "casasyterrenos.com", "tipo": "Portal listings", "cobertura": "Nacional", "enfoque": "Enfocado en desarrollos nuevos y preventa"},
    {"portal": "Proyectos Inmobiliarios", "dominio": "proyectos-inmobiliarios.com", "tipo": "Directorio", "cobertura": "Nacional", "enfoque": "Directorio de desarrollos por ciudad y tipo"},
    {"portal": "Luumo Real Estate", "dominio": "luumorealestate.com", "tipo": "Portal listings", "cobertura": "Quintana Roo", "enfoque": "Desarrollos en preventa y entrega inmediata en Q. Roo"},
    # --- Revistas y medios especializados (PDFs, noticias, análisis) ---
    {"portal": "Inmobiliare Magazine", "dominio": "inmobiliare.com", "tipo": "Revista", "cobertura": "Nacional", "enfoque": "Revista líder del sector, reportajes de lanzamientos y PDFs descargables"},
    {"portal": "Real Estate Market", "dominio": "realestatemarket.com.mx", "tipo": "Revista", "cobertura": "Nacional", "enfoque": "Análisis de mercado, nuevos desarrollos, entrevistas a desarrolladores"},
    {"portal": "Revista Equipar", "dominio": "revistaequipar.com", "tipo": "Revista", "cobertura": "Nacional", "enfoque": "Cobertura de proyectos comerciales, residenciales y turísticos"},
    {"portal": "Centro Urbano", "dominio": "centrourbano.com", "tipo": "Noticias", "cobertura": "Nacional", "enfoque": "Noticias diarias del sector inmobiliario, lanzamientos y tendencias"},
    {"portal": "Obras Web", "dominio": "obrasweb.mx", "tipo": "Noticias", "cobertura": "Nacional", "enfoque": "Noticias de construcción, infraestructura y desarrollos nuevos"},
    {"portal": "El Economista Inmobiliario", "dominio": "eleconomista.com.mx/sector_inmobiliario", "tipo": "Noticias", "cobertura": "Nacional", "enfoque": "Sección inmobiliaria de El Economista, datos de mercado"},
    {"portal": "Expansión Inmobiliario", "dominio": "expansion.mx/empresas", "tipo": "Noticias", "cobertura": "Nacional", "enfoque": "Cobertura de inversiones, nuevos proyectos y desarrolladores"},
    # --- Buscadores y fuentes complementarias ---
    {"portal": "Google News MX", "dominio": "news.google.com", "tipo": "Buscador", "cobertura": "Nacional", "enfoque": "Búsqueda de noticias recientes sobre lanzamientos inmobiliarios"},
    {"portal": "ARPR México", "dominio": "arprmexico.com", "tipo": "Consultoría", "cobertura": "Nacional", "enfoque": "Consultora con reportes de mercado y análisis de desarrollos"},
    {"portal": "Factor Inmobiliario", "dominio": "factorinmobiliario.mx", "tipo": "Portal listings", "cobertura": "Cancún / Q. Roo", "enfoque": "Desarrollos en preventa, venta y entrega en Cancún y Riviera Maya"},
    {"portal": "GDC Desarrollos", "dominio": "gdcdesarrollos.com", "tipo": "Desarrolladora", "cobertura": "CDMX", "enfoque": "Preventa de departamentos en CDMX, datos directos de desarrolladora"},
    {"portal": "TheRedSearch", "dominio": "theredsearch.com", "tipo": "Plataforma datos", "cobertura": "Yucatán / Q. Roo", "enfoque": "Plataforma con 1700+ desarrollos en Península de Yucatán (scraping autenticado)"},
    {"portal": "Trovit", "dominio": "casas.trovit.com.mx", "tipo": "Agregador", "cobertura": "Nacional", "enfoque": "Agregador de listings de múltiples portales inmobiliarios"},
]


def cargar_lanzamientos():
    if os.path.exists(LANZAMIENTOS_CSV):
        return pd.read_csv(LANZAMIENTOS_CSV)
    return pd.DataFrame()


def cargar_fuentes():
    if os.path.exists(FUENTES_CSV):
        return pd.read_csv(FUENTES_CSV)
    return pd.DataFrame()


def eliminar_proyectos_por_portal(portal_name):
    """Elimina todos los proyectos de un portal del CSV."""
    if not os.path.exists(LANZAMIENTOS_CSV):
        return 0
    df = pd.read_csv(LANZAMIENTOS_CSV)
    antes = len(df)
    df = df[df["portal_fuente"] != portal_name]
    df.to_csv(LANZAMIENTOS_CSV, index=False)
    return antes - len(df)


def eliminar_fuente_historial(portal_name):
    """Elimina el historial de consultas de un portal."""
    if not os.path.exists(FUENTES_CSV):
        return 0
    df = pd.read_csv(FUENTES_CSV)
    antes = len(df)
    df = df[df["portal"] != portal_name]
    df.to_csv(FUENTES_CSV, index=False)
    return antes - len(df)


def eliminar_proyecto_por_indice(idx):
    """Elimina un proyecto individual del CSV por su índice."""
    if not os.path.exists(LANZAMIENTOS_CSV):
        return False
    df = pd.read_csv(LANZAMIENTOS_CSV)
    if idx < 0 or idx >= len(df):
        return False
    df = df.drop(df.index[idx]).reset_index(drop=True)
    df.to_csv(LANZAMIENTOS_CSV, index=False)
    return True


def get_portal_status(df_fuentes, portal_name):
    """Determina el status de un portal desde el historial de fuentes."""
    status_key = "unknown"
    last_date = ""
    last_found = 0
    total_found = 0

    if not df_fuentes.empty:
        df_portal = df_fuentes[df_fuentes["portal"] == portal_name]
        if not df_portal.empty:
            ultimo = df_portal.iloc[-1]
            last_status = str(ultimo.get("status", ""))
            last_date = str(ultimo.get("fecha_consulta", ""))
            last_found = int(ultimo.get("proyectos_encontrados", 0))
            total_found = int(df_portal["proyectos_encontrados"].sum())

            if last_status == "ok":
                status_key = "ok"
            elif "bloqueado" in last_status or "error" in last_status:
                status_key = "error"
            elif "warning" in last_status:
                status_key = "warning"

    return status_key, last_date, last_found, total_found


# --- UI ---

st.set_page_config(page_title="Detector de Lanzamientos", page_icon="🚀", layout="wide")
st.title("🚀 Detector de Lanzamientos Inmobiliarios")

tab_lanzamientos, tab_fuentes = st.tabs(["📊 Lanzamientos", "🌐 Fuentes y Dominios"])

# --- TAB: Lanzamientos ---
with tab_lanzamientos:
    df_lanz = cargar_lanzamientos()
    df_fuentes = cargar_fuentes()

    if df_lanz.empty:
        st.info("No hay lanzamientos detectados. Ejecuta `/detector-lanzamientos` en Claude Code para iniciar el scraping de portales inmobiliarios.")

        st.divider()
        st.subheader("Portales configurados para monitoreo")
        for p in PORTALES_INMOBILIARIOS:
            st.markdown(
                f"""<div style="display:flex;align-items:center;padding:8px 12px;margin:4px 0;background:#1a1a2e;border-radius:8px;border-left:4px solid #95a5a6;">
                    <span style="font-size:14px;margin-right:8px;">⚪</span>
                    <div style="flex:1;">
                        <span style="font-weight:600;font-size:14px;">{p['portal']}</span>
                        <span style="color:#888;font-size:12px;margin-left:8px;">{p['dominio']}</span>
                    </div>
                    <span style="color:#aaa;font-size:12px;">{p['enfoque']}</span>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        # --- KPI Bar ---
        total_lanz = len(df_lanz)
        estados_rep = df_lanz["estado_republica"].nunique() if "estado_republica" in df_lanz.columns else 0
        ciudades = df_lanz["ciudad"].nunique() if "ciudad" in df_lanz.columns else 0
        ultima_deteccion = df_lanz["fecha_deteccion"].max() if "fecha_deteccion" in df_lanz.columns else "N/A"
        portales_activos = df_lanz["portal_fuente"].nunique() if "portal_fuente" in df_lanz.columns else 0

        delta_lanz = ""
        if "fecha_deteccion" in df_lanz.columns:
            hace_7 = (datetime.now() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
            nuevos_semana = len(df_lanz[df_lanz["fecha_deteccion"] >= hace_7])
            if nuevos_semana > 0:
                delta_lanz = f"+{nuevos_semana} esta semana"

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Proyectos detectados", total_lanz, delta=delta_lanz)
        col2.metric("Estados", estados_rep)
        col3.metric("Ciudades", ciudades)
        col4.metric("Portales activos", portales_activos)
        col5.metric("Ultima deteccion", ultima_deteccion)

        st.divider()

        # --- Filtros ---
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            estados_opts = ["Todos"] + sorted(df_lanz["estado_republica"].dropna().unique().tolist()) if "estado_republica" in df_lanz.columns else ["Todos"]
            filtro_estado_rep = st.selectbox("Estado de la republica", estados_opts, key="lanz_estado")
        with col_f2:
            etapas_opts = ["Todas"] + sorted(df_lanz["etapa"].dropna().unique().tolist()) if "etapa" in df_lanz.columns else ["Todas"]
            filtro_etapa = st.selectbox("Etapa", etapas_opts, key="lanz_etapa")
        with col_f3:
            tipos_opts = ["Todos"] + sorted(df_lanz["tipo_unidades"].dropna().unique().tolist()) if "tipo_unidades" in df_lanz.columns else ["Todos"]
            filtro_tipo_u = st.selectbox("Tipo unidades", tipos_opts, key="lanz_tipo")
        with col_f4:
            portales_opts = ["Todos"] + sorted(df_lanz["portal_fuente"].dropna().unique().tolist()) if "portal_fuente" in df_lanz.columns else ["Todos"]
            filtro_portal = st.selectbox("Portal", portales_opts, key="lanz_portal")

        df_lanz_f = df_lanz.copy()
        if filtro_estado_rep != "Todos":
            df_lanz_f = df_lanz_f[df_lanz_f["estado_republica"] == filtro_estado_rep]
        if filtro_etapa != "Todas":
            df_lanz_f = df_lanz_f[df_lanz_f["etapa"] == filtro_etapa]
        if filtro_tipo_u != "Todos":
            df_lanz_f = df_lanz_f[df_lanz_f["tipo_unidades"] == filtro_tipo_u]
        if filtro_portal != "Todos":
            df_lanz_f = df_lanz_f[df_lanz_f["portal_fuente"] == filtro_portal]

        st.divider()

        # --- Distribuciones visuales ---
        col_dist1, col_dist2 = st.columns(2)

        with col_dist1:
            st.markdown("##### Por estado de la republica")
            if "estado_republica" in df_lanz_f.columns:
                por_estado = df_lanz_f["estado_republica"].value_counts().head(10)
                max_val = por_estado.max() if not por_estado.empty else 1
                for estado, count in por_estado.items():
                    pct = count / max_val * 100
                    st.markdown(
                        f"""<div style="display:flex;align-items:center;margin-bottom:3px;">
                            <span style="width:140px;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{estado}</span>
                            <div style="flex:1;background:#333;border-radius:4px;height:18px;margin:0 8px;">
                                <div style="width:{pct}%;background:#3498db;height:100%;border-radius:4px;"></div>
                            </div>
                            <span style="width:30px;font-size:13px;text-align:right;">{count}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        with col_dist2:
            st.markdown("##### Por etapa")
            if "etapa" in df_lanz_f.columns:
                por_etapa = df_lanz_f["etapa"].value_counts()
                max_val_e = por_etapa.max() if not por_etapa.empty else 1
                for etapa_val, count in por_etapa.items():
                    pct = count / max_val_e * 100
                    color = COLORES_ETAPA.get(etapa_val, "#3498db")
                    st.markdown(
                        f"""<div style="display:flex;align-items:center;margin-bottom:3px;">
                            <span style="width:140px;font-size:13px;">{etapa_val}</span>
                            <div style="flex:1;background:#333;border-radius:4px;height:18px;margin:0 8px;">
                                <div style="width:{pct}%;background:{color};height:100%;border-radius:4px;"></div>
                            </div>
                            <span style="width:30px;font-size:13px;text-align:right;">{count}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        st.divider()

        # --- Cards de proyectos detectados ---
        st.subheader(f"Proyectos detectados ({len(df_lanz_f)})")

        for i in range(0, len(df_lanz_f), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(df_lanz_f):
                    break
                row = df_lanz_f.iloc[idx]
                original_idx = df_lanz_f.index[idx]
                nombre = row.get("nombre_proyecto", "Sin nombre")
                ciudad = row.get("ciudad", "")
                estado_r = row.get("estado_republica", "")
                zona = row.get("zona", "")
                etapa_val = row.get("etapa", "")
                precio = row.get("rango_precios", "")
                tipo = row.get("tipo_unidades", "")
                portal = row.get("portal_fuente", "")
                fecha = row.get("fecha_deteccion", "")
                url = row.get("url_fuente", "")
                desarrolladora = row.get("desarrolladora", "")
                num_uds = row.get("num_unidades", "")

                color_etapa = COLORES_ETAPA.get(etapa_val, "#95a5a6")

                ubicacion_parts = [p for p in [zona, ciudad, estado_r] if p and str(p) != "nan"]
                ubicacion_str = ", ".join(ubicacion_parts) if ubicacion_parts else "Sin ubicacion"

                with col:
                    with st.container(border=True):
                        header_col, badge_col = st.columns([3, 1])
                        with header_col:
                            st.markdown(f"**{nombre}**")
                            if desarrolladora and str(desarrolladora) != 'nan':
                                st.caption(str(desarrolladora))
                        with badge_col:
                            st.markdown(
                                f'<span style="background:{color_etapa};color:white;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;white-space:nowrap;float:right;">{etapa_val}</span>',
                                unsafe_allow_html=True,
                            )
                        st.caption(f"📍 {ubicacion_str}")

                        mc1, mc2, mc3 = st.columns(3)
                        mc1.caption(f"{'💰 ' + str(precio) if precio and str(precio) != 'nan' else '💰 Sin precio'}")
                        mc2.caption(f"🏠 {tipo if tipo and str(tipo) != 'nan' else 'N/A'}")
                        try:
                            uds_display = int(float(num_uds)) if num_uds and str(num_uds) not in ('nan', '', 'N/A') else "N/A"
                        except (ValueError, TypeError):
                            uds_display = "N/A"
                        mc3.caption(f"📦 {uds_display} uds")

                        footer_cols = st.columns([2, 1, 1])
                        footer_cols[0].caption(f"{portal} · {fecha}")
                        if url and str(url) != "nan":
                            footer_cols[1].markdown(
                                f'<a href="{url}" target="_blank" style="color:#3498db;text-decoration:none;font-size:11px;float:right;">Ver en portal ↗</a>',
                                unsafe_allow_html=True,
                            )
                        if footer_cols[2].button("🗑️", key=f"del_proy_{original_idx}", help="Eliminar proyecto"):
                            eliminar_proyecto_por_indice(original_idx)
                            st.rerun()

        st.divider()

        csv_lanz_export = df_lanz_f.to_csv(index=False)
        st.download_button(
            "📥 Descargar lanzamientos CSV",
            csv_lanz_export,
            file_name=f"lanzamientos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# --- TAB: Fuentes ---
with tab_fuentes:
    st.header("Portales inmobiliarios monitoreados")
    st.caption("Status y efectividad de cada fuente de datos para deteccion de lanzamientos")

    df_fuentes_tab = cargar_fuentes()

    # --- KPI de fuentes ---
    total_portales = len(PORTALES_INMOBILIARIOS)
    if not df_fuentes_tab.empty:
        portales_consultados = df_fuentes_tab["portal"].nunique()
        total_consultas = len(df_fuentes_tab)
        consultas_ok = len(df_fuentes_tab[df_fuentes_tab["status"] == "ok"])
        tasa_exito = round(consultas_ok / total_consultas * 100) if total_consultas > 0 else 0
        total_encontrados = df_fuentes_tab["proyectos_encontrados"].sum() if "proyectos_encontrados" in df_fuentes_tab.columns else 0
        ultima_consulta = df_fuentes_tab["fecha_consulta"].max() if "fecha_consulta" in df_fuentes_tab.columns else "N/A"
    else:
        portales_consultados = 0
        total_consultas = 0
        tasa_exito = 0
        total_encontrados = 0
        ultima_consulta = "N/A"

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Portales configurados", total_portales)
    col2.metric("Portales consultados", portales_consultados)
    col3.metric("Tasa de exito", f"{tasa_exito}%")
    col4.metric("Proyectos encontrados", int(total_encontrados))
    col5.metric("Ultima consulta", ultima_consulta)

    st.divider()

    # --- Grid de portales con status ---
    st.subheader("Dominios principales")

    for i in range(0, len(PORTALES_INMOBILIARIOS), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(PORTALES_INMOBILIARIOS):
                break
            portal_info = PORTALES_INMOBILIARIOS[idx]
            portal_name = portal_info["portal"]

            status_key, last_date, last_found, total_found_portal = get_portal_status(df_fuentes_tab, portal_name)
            status_info = COLORES_STATUS_FUENTE[status_key]

            with col:
                with st.container(border=True):
                    header_col, badge_col = st.columns([3, 1])
                    with header_col:
                        st.markdown(f"{status_info['icon']} **{portal_name}**")
                    with badge_col:
                        st.markdown(
                            f'<span style="background:{status_info["color"]}22;color:{status_info["color"]};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;float:right;">{status_info["label"]}</span>',
                            unsafe_allow_html=True,
                        )
                    st.caption(f"🔗 {portal_info['dominio']}")
                    st.caption(portal_info['enfoque'])

                    mc1, mc2 = st.columns(2)
                    mc1.caption(f"Tipo: {portal_info['tipo']}")
                    mc2.caption(f"Cobertura: {portal_info['cobertura']}")

                    if last_date and last_date != "nan":
                        st.caption(f"Ultima consulta: {last_date} · {last_found} encontrados · Total hist: {total_found_portal}")

    st.divider()

    # --- Tabla dominios completa ---
    st.subheader("Directorio completo de dominios")

    dominios_data = []
    for p in PORTALES_INMOBILIARIOS:
        status_key, last_date, _, total_found_p = get_portal_status(df_fuentes_tab, p["portal"])
        consultas_p = 0
        if not df_fuentes_tab.empty:
            consultas_p = len(df_fuentes_tab[df_fuentes_tab["portal"] == p["portal"]])

        efectividad = round(total_found_p / consultas_p, 1) if consultas_p > 0 else 0

        dominios_data.append({
            "Status": COLORES_STATUS_FUENTE[status_key]["icon"],
            "Portal": p["portal"],
            "Dominio": p["dominio"],
            "Tipo": p["tipo"],
            "Enfoque": p["enfoque"],
            "Consultas": consultas_p,
            "Proyectos encontrados": total_found_p,
            "Efectividad (proy/consulta)": efectividad,
            "Ultima consulta": last_date if last_date != "nan" else "",
        })

    df_dominios = pd.DataFrame(dominios_data)
    st.dataframe(
        df_dominios,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("", width="small"),
            "Portal": st.column_config.TextColumn("Portal", width="medium"),
            "Dominio": st.column_config.TextColumn("Dominio", width="medium"),
            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
            "Enfoque": st.column_config.TextColumn("Enfoque", width="large"),
            "Consultas": st.column_config.NumberColumn("Consultas", width="small"),
            "Proyectos encontrados": st.column_config.NumberColumn("Encontrados", width="small"),
            "Efectividad (proy/consulta)": st.column_config.NumberColumn("Efect.", width="small", format="%.1f"),
            "Ultima consulta": st.column_config.TextColumn("Ultima", width="small"),
        },
    )

    # --- Administrar fuentes ---
    st.divider()
    st.subheader("Administrar fuentes")
    st.caption("Elimina fuentes y sus proyectos asociados del sistema")

    df_lanz_admin = cargar_lanzamientos()
    if not df_lanz_admin.empty and "portal_fuente" in df_lanz_admin.columns:
        portales_con_datos = df_lanz_admin["portal_fuente"].value_counts()

        for portal_name, count in portales_con_datos.items():
            col_info, col_btn = st.columns([4, 1])
            col_info.markdown(f"**{portal_name}** — {count} proyectos")
            if col_btn.button(f"🗑️ Eliminar", key=f"del_fuente_{portal_name}"):
                n_proy = eliminar_proyectos_por_portal(portal_name)
                n_hist = eliminar_fuente_historial(portal_name)
                st.success(f"Eliminados {n_proy} proyectos y {n_hist} registros de {portal_name}")
                st.rerun()
    else:
        st.info("No hay fuentes con proyectos registrados.")

    # --- Historial de consultas ---
    if not df_fuentes_tab.empty:
        st.divider()
        with st.expander("📋 Historial de consultas", expanded=False):
            df_hist_fuentes = df_fuentes_tab.sort_values("fecha_consulta", ascending=False) if "fecha_consulta" in df_fuentes_tab.columns else df_fuentes_tab
            st.dataframe(df_hist_fuentes, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Automatizacion")
    st.code("/loop 1d /detector-lanzamientos", language="bash")
    st.caption("Ejecuta este comando en Claude Code para activar la deteccion diaria automatica de nuevos lanzamientos.")
