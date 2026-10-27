import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import plotly.express as px
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(page_title="Análisis de Discrepancias CBD", layout="wide")

st.title("Análisis de Discrepancias: Validaciones vs GPS")
st.markdown("""
Esta aplicación permite detectar discrepancias grandes entre los datos de billetaje (validaciones) y los datos de GPS (CBD), así como identificar caídas a 0 en las validaciones.
""")

# Parámetros de conexión a BD (Hardcoded de tu backend/.env para facilidad)
DB_HOST = "168.90.177.232"
DB_PORT = "2024"
DB_NAME = "bbdd-monitoreo-cid"
DB_USER = "cid_admin_user"
DB_PASSWORD = "vmtdmtcidccm"

@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

@st.cache_data(ttl=600)
def get_data(fecha_inicio, fecha_fin):
    conn = init_connection()
    
    # 1. Obtener Validaciones (Servicios Diarios)
    query_val = """
        SELECT
            sd.fecha,
            sd.id_eot_catalogo as eot_id,
            sd.hora,
            COUNT(DISTINCT sd.idsam)::integer as validaciones
        FROM public.servicios_diarios sd
        WHERE sd.fecha BETWEEN %s AND %s
          AND sd.hora BETWEEN 4 AND 23
          AND sd.id_eot_catalogo NOT IN (72, 75)
        GROUP BY sd.fecha, sd.id_eot_catalogo, sd.hora
    """
    df_val = pd.read_sql_query(query_val, conn, params=(fecha_inicio, fecha_fin))
    
    # 2. Obtener GPS (CBD Detalle Buses)
    query_gps = """
        SELECT 
            cdb.fecha,
            e.cod_catalogo as eot_id,
            EXTRACT(HOUR FROM (cdb.hora * INTERVAL '1 hour')::time)::integer as hora,
            COUNT(DISTINCT cdb.mean_id)::integer as gps
        FROM control_metricas.cbd_detalle_buses cdb
        INNER JOIN public.eots e ON cdb.id_eot_vmt_hex = e.id_eot_vmt_hex
        WHERE cdb.fecha BETWEEN %s AND %s
          AND EXTRACT(HOUR FROM (cdb.hora * INTERVAL '1 hour')::time) BETWEEN 4 AND 23
        GROUP BY cdb.fecha, e.cod_catalogo, EXTRACT(HOUR FROM (cdb.hora * INTERVAL '1 hour')::time)
    """
    df_gps = pd.read_sql_query(query_gps, conn, params=(fecha_inicio, fecha_fin))
    
    # 3. Obtener nombres de EOTs
    query_eots = "SELECT cod_catalogo as eot_id, eot_nombre FROM public.eots"
    df_eots = pd.read_sql_query(query_eots, conn)
    
    # Merge de validaciones y GPS
    # Llenamos con 0 donde falten datos en alguna de las fuentes
    df_merged = pd.merge(df_val, df_gps, on=['fecha', 'eot_id', 'hora'], how='outer').fillna(0)
    df_merged = pd.merge(df_merged, df_eots, on='eot_id', how='left')
    
    df_merged['validaciones'] = df_merged['validaciones'].astype(int)
    df_merged['gps'] = df_merged['gps'].astype(int)
    
    return df_merged

# Controles de UI
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha Inicio", datetime.today() - timedelta(days=7))
with col2:
    fecha_fin = st.date_input("Fecha Fin", datetime.today())

st.sidebar.header("Filtros de Discrepancia")
diferencia_abs_min = st.sidebar.number_input("Diferencia mínima absoluta (Validaciones vs GPS)", value=20, min_value=0)
umbral_cero_gps = st.sidebar.number_input("Si Validaciones = 0, mínimo de GPS requerido para alertar", value=10, min_value=1)

if st.button("Analizar Datos"):
    with st.spinner('Obteniendo datos de la base de datos...'):
        df = get_data(fecha_inicio, fecha_fin)
        
        # Calcular discrepancias
        df['diferencia_abs'] = abs(df['validaciones'] - df['gps'])
        
        # Detectar "caídas a 0" (Validaciones en 0 pero GPS indica que hubo servicio)
        df['caida_a_cero'] = (df['validaciones'] == 0) & (df['gps'] >= umbral_cero_gps)
        
        # Detectar discrepancias grandes
        df['discrepancia_grande'] = df['diferencia_abs'] >= diferencia_abs_min
        
        # Filtrar solo los registros que cumplen alguna condición anómala
        anomalias = df[df['caida_a_cero'] | df['discrepancia_grande']].copy()
        anomalias = anomalias.sort_values(by=['fecha', 'eot_nombre', 'hora'])
        
        st.subheader("Resultados del Análisis")
        
        if anomalias.empty:
            st.success("No se encontraron discrepancias significativas en el rango seleccionado con los filtros actuales.")
        else:
            st.warning(f"Se encontraron {len(anomalias)} registros con posibles anomalías.")
            
            # Formatear tabla para mostrar
            mostrar_df = anomalias[['fecha', 'eot_nombre', 'hora', 'validaciones', 'gps', 'diferencia_abs', 'caida_a_cero']].copy()
            mostrar_df['Tipo de Problema'] = mostrar_df.apply(
                lambda x: "🚨 Cae a Cero" if x['caida_a_cero'] else "⚠️ Discrepancia Grande", axis=1
            )
            
            st.dataframe(
                mostrar_df[['fecha', 'eot_nombre', 'hora', 'validaciones', 'gps', 'diferencia_abs', 'Tipo de Problema']],
                use_container_width=True,
                height=400
            )
            
            # Resumen por empresa
            st.subheader("Resumen de Anomalías por Empresa")
            resumen = anomalias.groupby('eot_nombre').size().reset_index(name='Cantidad de Anomalías')
            resumen = resumen.sort_values('Cantidad de Anomalías', ascending=False)
            
            fig = px.bar(resumen, x='eot_nombre', y='Cantidad de Anomalías', title="Empresas con más discrepancias/caídas a 0")
            st.plotly_chart(fig, use_container_width=True)
            
            # Exportar
            csv = mostrar_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Descargar CSV de Discrepancias",
                csv,
                "discrepancias_cbd.csv",
                "text/csv",
                key='download-csv'
            )
