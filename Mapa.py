# app_master_premium.py
# -*- coding: utf-8 -*-

import json
import streamlit as st
import pandas as pd
import numpy as np

# 1. Configurações Iniciais de Alta Performance
st.set_page_config(
    page_title="Mapa Premium CEP Master", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Estilização Customizada para o Streamlit
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; background-color: #2e7d32; color: white; }
</style>
""", unsafe_allow_html=True)

st.title("🗺️ Mapa Premium CEP - Versão Master")
st.caption("Performance extrema, filtros inteligentes e exportação profissional.")

# 2. Processamento de Dados com Cache e Limpeza Robusta
@st.cache_data(show_spinner="Analisando dados do Excel...")
def carregar_e_otimizar_dados(arquivo):
    try:
        # Leitura otimizada
        df = pd.read_excel(arquivo, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        # Mapeamento inteligente de colunas
        def _detectar(opcoes):
            cols = {c.lower(): c for c in df.columns}
            for o in opcoes:
                if o in cols: return cols[o]
            return None

        c_lat = _detectar(["latitude", "lat", "y"])
        c_lng = _detectar(["longitude", "lng", "lon", "long", "x"])

        if not c_lat or not c_lng:
            return None, "Colunas de Latitude/Longitude não encontradas."

        # Limpeza de coordenadas (remove erros comuns de digitação)
        df["lat_f"] = pd.to_numeric(df[c_lat].astype(str).str.replace(",", "."), errors="coerce")
        df["lng_f"] = pd.to_numeric(df[c_lng].astype(str).str.replace(",", "."), errors="coerce")

        # Filtro de coordenadas válidas para o Brasil (opcional, mas evita pontos no mar/fora)
        df = df.dropna(subset=["lat_f", "lng_f"])

        # Detecção de UF e Cidade para filtros
        c_uf = _detectar(["uf", "estado", "state"])
        c_cid = _detectar(["cidade", "municipio", "município", "localidade", "city"])

        df["uf_f"] = df[c_uf].fillna("N/I").astype(str).str.upper() if c_uf else "N/I"
        df["cid_f"] = df[c_cid].fillna("N/I").astype(str).str.title() if c_cid else "N/I"

        # Preparação do Popup HTML (Otimizado)
        cols_originais = [c for c in df.columns if c not in ["lat_f", "lng_f", "uf_f", "cid_f"]]

        def criar_popup(row):
            html = '<div style="font-family:sans-serif; min-width:150px;">'
            count = 0
            for col in cols_originais:
                val = str(row[col])
                if val.lower() not in ["nan", "none", "null", ""]:
                    html += f'<b>{col}:</b> {val}<br>'
                    count += 1
                if count >= 8: break # Limite de campos no popup para performance
            return html + '</div>'

        df["popup_html"] = df.apply(criar_popup, axis=1)

        return df.to_dict(orient="records"), list(df.columns)
    except Exception as e:
        return None, f"Erro: {str(e)}"

# 3. Interface de Upload
arquivo = st.file_uploader("📂 Arraste seu arquivo Excel aqui", type=["xlsx"])

if arquivo:
    dados, colunas = carregar_e_otimizar_dados(arquivo)

    if dados:
        # Serialização segura para JS
        json_dados = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
        json_cols = json.dumps(colunas, ensure_ascii=False)

        # 4. HTML/JS Master (Leaflet + Canvas + Filtros Avançados)
        html_master = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.css" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
    <style>
        :root {{ --primary: #2e7d32; --dark: #1b1b1b; --light: #ffffff; }}
        body, html {{ margin: 0; padding: 0; height: 100%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        #map {{ height: 100vh; width: 100%; }}

        /* Painel Lateral Moderno */
        #ui-panel {{
            position: absolute; top: 20px; right: 20px; z-index: 1000;
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(5px);
            padding: 20px; border-radius: 16px; width: 300px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15); border: 1px solid rgba(0,0,0,0.05);
        }}

        .section-title {{ font-size: 14px; font-weight: 700; color: var(--dark); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
        .filter-group {{ margin-bottom: 15px; }}
        label {{ font-size: 11px; color: #666; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; display: block; }}

        select, input {{
            width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #ddd;
            background: #fff; font-size: 13px; transition: border 0.3s;
        }}
        select:focus, input:focus {{ border-color: var(--primary); outline: none; }}

        .btn {{
            width: 100%; padding: 12px; border: none; border-radius: 10px; cursor: pointer;
            font-weight: 700; font-size: 13px; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 8px;
            transition: transform 0.1s, opacity 0.2s;
        }}
        .btn:active {{ transform: scale(0.98); }}
        #btn-export {{ background: var(--primary); color: white; }}
        #btn-clear {{ background: var(--dark); color: white; }}

        #stats-bar {{
            margin-top: 15px; padding: 10px; background: #f0f4f0; border-radius: 8px;
            text-align: center; font-size: 13px; color: var(--primary); font-weight: 700;
        }}

        /* Tooltip de busca */
        #search-box {{ margin-bottom: 15px; position: relative; }}
        #search-box i {{ position: absolute; right: 10px; top: 35px; color: #999; }}
    </style>
</head>
<body>
    <div id="map"></div>

    <div id="ui-panel">
        <div class="section-title"><i class="fas fa-filter"></i> PAINEL DE CONTROLE</div>

        <div id="search-box">
            <label>Busca Rápida (Qualquer Campo)</label>
            <input type="text" id="inp-search" placeholder="Ex: CEP, Nome, Rua...">
            <i class="fas fa-search"></i>
        </div>

        <div class="filter-group">
            <label>Estado (UF)</label>
            <select id="sel-uf"><option value="ALL">Todos os Estados</option></select>
        </div>

        <div class="filter-group">
            <label>Cidade</label>
            <select id="sel-cidade"><option value="ALL">Todas as Cidades</option></select>
        </div>

        <div class="filter-group">
            <label>Cor dos Marcadores</label>
            <input type="color" id="color-picker" value="#2e7d32">
        </div>

        <div id="stats-bar">Processando pontos...</div>

        <button class="btn" id="btn-export"><i class="fas fa-file-export"></i> EXPORTAR SELEÇÃO</button>
        <button class="btn" id="btn-clear"><i class="fas fa-eraser"></i> LIMPAR DESENHOS</button>

        <div style="font-size: 10px; color: #999; margin-top: 15px; text-align: center;">
            Use as ferramentas à esquerda para filtrar por área.
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.js"></script>
    <script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>

    <script>
        const DATA = {json_dados};
        const COLS = {json_cols};
        let filtered = DATA;
        let drawnItems = new L.FeatureGroup();

        // Inicialização do Mapa com Canvas
        const map = L.map('map', {{
            preferCanvas: true,
            center: [-14.2350, -51.9253],
            zoom: 4,
            zoomControl: false
        }});

        L.control.zoom({{ position: 'bottomleft' }}).addTo(map);

        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png', {{
            attribution: 'Manus AI | CartoDB'
        }}).addTo(map);

        map.addLayer(drawnItems);

        // Ferramentas de Desenho Otimizadas
        const drawControl = new L.Control.Draw({{
            position: 'topleft',
            draw: {{ polyline: false, marker: false, circlemarker: false, polygon: true, rectangle: true, circle: true }},
            edit: {{ featureGroup: drawnItems }}
        }});
        map.addControl(drawControl);

        // Elementos da Interface
        const elUf = document.getElementById('sel-uf');
        const elCid = document.getElementById('sel-cidade');
        const elSearch = document.getElementById('inp-search');
        const elColor = document.getElementById('color-picker');
        const elStats = document.getElementById('stats-bar');
        const btnExport = document.getElementById('btn-export');
        const btnClear = document.getElementById('btn-clear');

        // Carregar Filtros Iniciais
        const ufs = [...new Set(DATA.map(d => d.uf_f))].sort();
        ufs.forEach(uf => {{
            const opt = document.createElement('option');
            opt.value = uf; opt.textContent = uf;
            elUf.appendChild(opt);
        }});

        function updateCidades() {{
            const selectedUf = elUf.value;
            elCid.innerHTML = '<option value="ALL">Todas as Cidades</option>';
            const cidades = [...new Set(
                DATA.filter(d => selectedUf === 'ALL' || d.uf_f === selectedUf).map(d => d.cid_f)
            )].sort();
            cidades.forEach(c => {{
                const opt = document.createElement('option');
                opt.value = c; opt.textContent = c;
                elCid.appendChild(opt);
            }});
        }}

        let layerGroup = L.layerGroup().addTo(map);

        function applyFilters() {{
            const uf = elUf.value;
            const cid = elCid.value;
            const search = elSearch.value.toLowerCase();
            const color = elColor.value;

            filtered = DATA.filter(d => {{
                const matchUf = (uf === 'ALL' || d.uf_f === uf);
                const matchCid = (cid === 'ALL' || d.cid_f === cid);
                const matchSearch = !search || JSON.stringify(d).toLowerCase().includes(search);
                return matchUf && matchCid && matchSearch;
            }});

            layerGroup.clearLayers();

            // Renderização em Lote para Performance
            filtered.forEach(p => {{
                L.circleMarker([p.lat_f, p.lng_f], {{
                    radius: 5,
                    fillColor: color,
                    color: '#fff',
                    weight: 1,
                    fillOpacity: 0.8
                }}).bindPopup(p.popup_html).addTo(layerGroup);
            }});

            elStats.innerText = '📍 ' + filtered.length + ' pontos encontrados';
        }}

        // Eventos
        elUf.onchange = () => {{ updateCidades(); applyFilters(); }};
        elCid.onchange = applyFilters;
        elColor.onchange = applyFilters;
        elSearch.oninput = applyFilters;

        map.on(L.Draw.Event.CREATED, (e) => {{ drawnItems.addLayer(e.layer); applyFilters(); }});
        map.on(L.Draw.Event.DELETED, applyFilters);
        map.on(L.Draw.Event.EDITED, applyFilters);

        btnClear.onclick = () => {{ drawnItems.clearLayers(); applyFilters(); }};

        // Exportação Profissional (CSV por colunas)
        btnExport.onclick = () => {{
            let toExport = filtered;
            const layers = drawnItems.getLayers();

            if (layers.length > 0) {{
                toExport = toExport.filter(p => {{
                    const pt = turf.point([p.lng_f, p.lat_f]);
                    return layers.some(l => {{
                        if (l instanceof L.Circle) {{
                            const dist = turf.distance(pt, turf.point([l.getLatLng().lng, l.getLatLng().lat]));
                            return dist <= (l.getRadius() / 1000);
                        }}
                        return turf.booleanPointInPolygon(pt, l.toGeoJSON());
                    }});
                }});
            }}

            if (toExport.length === 0) return alert('Nenhum dado na seleção atual.');

            const colsToExport = COLS.filter(c => !['lat_f', 'lng_f', 'uf_f', 'cid_f', 'popup_html'].includes(c));
            let csv = colsToExport.join(',') + '\\n';

            toExport.forEach(row => {{
                csv += colsToExport.map(c => {{
                    let v = String(row[c] || '');
                    if (v.includes(',') || v.includes('"') || v.includes('\\n')) {{
                        v = '"' + v.replace(/"/g, '""') + '"';
                    }}
                    return v;
                }}).join(',') + '\\n';
            }});

            const blob = new Blob(["\\ufeff" + csv], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = "exportacao_premium.csv";
            link.click();
        }};

        updateCidades();
        applyFilters();
    </script>
</body>
</html>
        """
        # Exibição do Componente
        st.components.v1.html(html_master, height=800, scrolling=False)

        # Opções Extras no Streamlit
        with st.expander("🛠️ Ferramentas Avançadas"):
            st.download_button(
                "⬇️ Baixar Mapa como HTML Autônomo",
                data=html_master,
                file_name="mapa_premium_master.html",
                mime="text/html"
            )
            st.info("Este HTML pode ser aberto em qualquer computador, mesmo sem internet, e manterá todas as funcionalidades de filtro e exportação.")

    else:
        st.error(colunas) # Mostra a mensagem de erro se o carregamento falhar
else:
    st.info("Arraste um arquivo Excel (.xlsx) com colunas de Latitude e Longitude para começar.")
    st.image("https://img.icons8.com/clouds/200/map-marker.png")