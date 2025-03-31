 import streamlit as st
import pandas as pd
import random
from itertools import combinations
import math

# --- Funciones Lógicas del Torneo (Adaptadas de la versión de consola) ---

def generate_simplified_fixture(players, num_courts):
    """Genera un fixture SIMPLIFICADO. No garantiza rotación perfecta."""
    num_players = len(players)
    if num_players < 4:
        return {"rounds": []} # No se puede jugar con menos de 4

    # Número de rondas tentativo (N-1 es para Round Robin completo, adaptamos)
    # Para un americano, puede ser menos, depende de cuánto tiempo se tenga.
    # Usemos una heurística: suficientes rondas para que la gente juegue varias veces.
    # Podríamos hacerlo configurable, pero empecemos con N/2 o N-1
    # num_rounds = max(1, num_players // 2) # Ejemplo: jugar aprox la mitad de rondas posibles
    num_rounds = max(1, num_players - 1) # Más cercano al americano completo

    fixture = {"rounds": []}
    all_players = list(players) # Copia para manipular

    # --- Lógica de generación de rondas (Simplificada) ---
    # Esta parte sigue siendo compleja para garantizar justicia y no repetición.
    # Usaremos una aleatorización fuerte en cada ronda como aproximación.
    
    # Historial para minimizar repetición de parejas (simple)
    played_pairs = set() 
    
    for round_num in range(1, num_rounds + 1):
        round_matches = []
        players_this_round = list(all_players)
        random.shuffle(players_this_round)
        
        players_assigned_this_round = set()
        # Ajuste: Asegurar que num_courts no sea mayor que partidos posibles
        max_matches_possible = len(players_this_round) // 4
        actual_num_courts = min(num_courts, max_matches_possible)
        
        if actual_num_courts <= 0: # Si no hay suficientes jugadores para un partido
            continue # Saltar esta iteración de ronda

        possible_pairs = list(combinations(players_this_round, 2))
        random.shuffle(possible_pairs)

        # Intentar formar parejas que no hayan jugado juntas recientemente
        potential_pairs = []
        players_already_paired = set()
        for p1, p2 in possible_pairs:
            pair_tuple = tuple(sorted((p1, p2)))
            priority = 1 if pair_tuple not in played_pairs else 0 
            if p1 not in players_already_paired and p2 not in players_already_paired:
                 potential_pairs.append( (priority, pair_tuple) )

        potential_pairs.sort(key=lambda x: x[0], reverse=True) 
        
        final_round_pairs = []
        players_in_final_pairs = set()
        for _, pair_tuple in potential_pairs:
            p1, p2 = pair_tuple
            if p1 not in players_in_final_pairs and p2 not in players_in_final_pairs:
                final_round_pairs.append(pair_tuple)
                players_in_final_pairs.add(p1)
                players_in_final_pairs.add(p2)

        # --- Enfrentar Parejas ---
        match_count = 0
        assigned_players_in_match = set()
        available_pairs_for_match = list(final_round_pairs) 
        random.shuffle(available_pairs_for_match)

        while match_count < actual_num_courts and len(available_pairs_for_match) >= 2:
            pair1 = available_pairs_for_match.pop(0)
            
            found_opponent = False
            for i in range(len(available_pairs_for_match)):
                pair2 = available_pairs_for_match[i]
                if not set(pair1) & set(pair2): 
                    available_pairs_for_match.pop(i) 
                    
                    played_pairs.add(pair1)
                    played_pairs.add(pair2)

                    round_matches.append({
                        "court": match_count + 1,
                        "pair1": pair1,
                        "pair2": pair2,
                        "score1": None,
                        "score2": None
                    })
                    assigned_players_in_match.update(pair1)
                    assigned_players_in_match.update(pair2)
                    match_count += 1
                    found_opponent = True
                    break 

            if not found_opponent:
                # No se encontró oponente, devolver pair1 si es necesario (poco probable aquí)
                 pass

        players_resting = [p for p in all_players if p not in assigned_players_in_match]

        if round_matches:
             fixture["rounds"].append({
                 "round_num": len(fixture["rounds"]) + 1, 
                 "matches": round_matches,
                 "resting": players_resting
             })

    if not fixture["rounds"] and num_players >= 4 and num_courts >= 1:
         st.warning("No se pudieron generar rondas con la configuración actual y el algoritmo simple. Intenta con más jugadores/pistas o revisa la lógica.")

    return fixture

def calculate_standings(players, fixture_data):
    """Calcula la clasificación basada en los resultados introducidos en el fixture."""
    # Reiniciar standings a cero antes de recalcular
    standings = {
        player: {"JG": 0, "JR": 0, "DG": 0, "PG": 0, "PP": 0, "PE": 0, "PJ": 0}
        for player in players
    }

    if not fixture_data or 'rounds' not in fixture_data:
        return standings, [] 

    # Recalcular todo desde los scores actuales en session_state
    processed_matches_for_player_stats = {p: set() for p in players} # Para evitar doble conteo de PJ/PG/PP/PE

    for round_idx, round_data in enumerate(fixture_data['rounds']):
        for match_idx, match in enumerate(round_data['matches']):
            match_id = f"r{round_data['round_num']}_m{match_idx}" # Identificador único del partido
            
            score1_key = f"score1_{match_id}"
            score2_key = f"score2_{match_id}"

            score1 = st.session_state.get(score1_key) # Obtener de session_state, puede ser None o 0
            score2 = st.session_state.get(score2_key)

            # Convertir a int si no es None, manejar 0 como válido
            s1 = int(score1) if score1 is not None else None
            s2 = int(score2) if score2 is not None else None

            # Actualizar el fixture en session_state (aunque ya leemos de él)
            match['score1'] = s1 
            match['score2'] = s2

            if s1 is not None and s2 is not None:
                pair1 = match['pair1']
                pair2 = match['pair2']

                # Actualizar Games Ganados/Recibidos (siempre se suman)
                for p in pair1:
                    standings[p]['JG'] += s1
                    standings[p]['JR'] += s2
                for p in pair2:
                    standings[p]['JG'] += s2
                    standings[p]['JR'] += s1

                # Actualizar PJ/PG/PP/PE (solo una vez por partido por jugador)
                if s1 > s2: # Gana Pareja 1
                    outcome1, outcome2 = 'PG', 'PP'
                elif s2 > s1: # Gana Pareja 2
                    outcome1, outcome2 = 'PP', 'PG'
                else: # Empate
                    outcome1, outcome2 = 'PE', 'PE'

                for p in pair1:
                    if match_id not in processed_matches_for_player_stats[p]:
                        standings[p]['PJ'] += 1
                        standings[p][outcome1] += 1
                        processed_matches_for_player_stats[p].add(match_id)
                for p in pair2:
                     if match_id not in processed_matches_for_player_stats[p]:
                        standings[p]['PJ'] += 1
                        standings[p][outcome2] += 1
                        processed_matches_for_player_stats[p].add(match_id)


    # Calcular Diferencia de Games al final
    for player in players:
        standings[player]['DG'] = standings[player]['JG'] - standings[player]['JR']

    # Ordenar: 1º PG (desc), 2º DG (desc), 3º JG (desc)
    sorted_players = sorted(
        players,
        key=lambda p: (standings[p]['PG'], standings[p]['DG'], standings[p]['JG']),
        reverse=True
    )

    return standings, sorted_players

def generate_standings_text(standings, sorted_players, tournament_name):
    """Genera el texto formateado para la clasificación."""
    header = f"--- CLASIFICACIÓN: {tournament_name} ---\n"
    separator = "-" * 75 + "\n"
    col_headers = f"{'Pos':<4} {'Jugador':<20} {'PJ':<4} {'PG':<4} {'PE':<4} {'PP':<4} {'JG':<6} {'JR':<6} {'DG':<6}\n"
    
    lines = [header, separator, col_headers, separator]
    
    for i, player in enumerate(sorted_players):
        stats = standings[player]
        lines.append(
            f"{i+1:<4} {player:<20} {stats['PJ']:<4} {stats['PG']:<4} {stats['PE']:<4} {stats['PP']:<4} {stats['JG']:<6} {stats['JR']:<6} {stats['DG']:<6}\n"
        )
    
    lines.append(separator)
    return "".join(lines)

# --- Interfaz de Streamlit ---

st.set_page_config(page_title="Padel Americano Manager", layout="wide")

st.title("🏓 Gestor de Torneos Americano de Pádel")

# Inicializar estado de sesión si no existe
if 'tournament_configured' not in st.session_state:
    st.session_state.tournament_configured = False
    st.session_state.config = {}
    st.session_state.players = []
    st.session_state.fixture = None
    st.session_state.player_inputs = {} # Para guardar temporalmente nombres

# --- Fase 1: Configuración del Torneo ---
if not st.session_state.tournament_configured:
    st.header("1. Configuración del Torneo")
    
    with st.form("config_form"):
        config = {}
        config['name'] = st.text_input("Nombre del Torneo", "Torneo Amigos")
        
        col1, col2 = st.columns(2)
        with col1:
            # Usar valor previo si existe en st.session_state.config
            num_players_value = st.session_state.config.get('num_players', 8)
            config['num_players'] = st.number_input(
                "Número total de jugadores (par >= 4)", 
                min_value=4, 
                step=2, 
                value=num_players_value
            )
        with col2:
            num_courts_value = st.session_state.config.get('num_courts', 2)
            config['num_courts'] = st.number_input(
                "Número de pistas disponibles (>= 1)", 
                min_value=1, 
                step=1, 
                value=num_courts_value
            )

        st.subheader("Nombres de los Jugadores")
        player_names_inputs = {} 
        cols_players = st.columns(3) # Organizar en columnas para mejor layout
        for i in range(config['num_players']):
             # Usar session_state para recordar los nombres entre re-runs del form
             default_name = st.session_state.player_inputs.get(i, f"Jugador {i+1}") 
             player_names_inputs[i] = cols_players[i % 3].text_input(
                 f"Jugador {i + 1}", 
                 value=default_name, 
                 key=f"player_{i}" # Clave única para cada input
             )
             st.session_state.player_inputs[i] = player_names_inputs[i] # Guardar para la próxima vez
             
        submitted = st.form_submit_button("Registrar Jugadores y Generar Fixture")
        
        if submitted:
            players = [name.strip() for name in player_names_inputs.values() if name.strip()]
            
            # Validaciones
            valid = True
            if len(players) != config['num_players']:
                st.error(f"Error: Se esperaban {config['num_players']} nombres de jugador, pero se encontraron {len(players)} no vacíos.")
                valid = False
            if len(set(players)) != len(players):
                 st.error("Error: Hay nombres de jugador duplicados.")
                 valid = False
            if config['num_players'] > 0 and config['num_courts'] > (config['num_players'] // 4):
                 st.warning(f"Advertencia: Tienes {config['num_courts']} pistas pero solo se pueden usar {config['num_players'] // 4} simultáneamente con {config['num_players']} jugadores. Se usarán solo {config['num_players'] // 4}.")
                 # No modificar config['num_courts'] aquí, pasar el valor ajustado a la función
                 adjusted_courts = config['num_players'] // 4
            else:
                 adjusted_courts = config['num_courts']
                 
            if config['num_players'] > 0 and adjusted_courts <= 0:
                 st.error("Error: No hay suficientes jugadores para usar ni una pista.")
                 valid = False

            if valid:
                # Guardar configuración y jugadores
                st.session_state.config = config # Guardar la config original
                st.session_state.players = players
                
                # Generar Fixture usando adjusted_courts
                st.session_state.fixture = generate_simplified_fixture(players, adjusted_courts)
                
                if st.session_state.fixture and st.session_state.fixture['rounds']:
                     st.session_state.tournament_configured = True
                     st.success("¡Torneo configurado y fixture generado!")
                     # Limpiar inputs temporales
                     st.session_state.player_inputs = {} 
                     # Forzar re-run para pasar a la siguiente fase
                     st.rerun() # --- CORREGIDO ---
                else:
                     st.error("No se pudo generar el fixture. Revisa la configuración o el número de jugadores/pistas. Puede que no haya suficientes para formar partidos.")
                     # Mantener la configuración para que el usuario pueda ajustar
                     st.session_state.tournament_configured = False 


# --- Fase 2: Visualización y Gestión del Torneo ---
if st.session_state.tournament_configured:
    st.header(f"🏆 Torneo: {st.session_state.config.get('name', 'Sin Nombre')}")
    st.caption(f"{len(st.session_state.players)} jugadores | {st.session_state.config.get('num_courts', '?')} pistas configuradas")

    # Calcular standings ANTES de mostrar las pestañas
    if st.session_state.fixture and 'rounds' in st.session_state.fixture:
        # Recalcular standings en cada interacción
        standings, sorted_players = calculate_standings(st.session_state.players, st.session_state.fixture)
    else:
        standings, sorted_players = {}, []
        st.error("Error: No se encontró un fixture válido en el estado.")


    tab1, tab2 = st.tabs(["📝 Rondas y Resultados", "📊 Clasificación"])

    with tab1:
        st.subheader("Partidos por Ronda")
        
        if not st.session_state.fixture or not st.session_state.fixture['rounds']:
             st.warning("No hay rondas generadas para este torneo.")
        else:
            # Crear una pestaña Streamlit para cada ronda del fixture
            round_tabs = st.tabs([f"Ronda {r['round_num']}" for r in st.session_state.fixture['rounds']])

            for i, round_data in enumerate(st.session_state.fixture['rounds']):
                with round_tabs[i]:
                    st.markdown(f"**Ronda {round_data['round_num']}**")
                    if round_data['resting']:
                         st.caption(f"Descansan: {', '.join(round_data['resting'])}")
                    
                    if not round_data['matches']:
                        st.info("No hay partidos programados en esta ronda.")
                        continue

                    # Mostrar partidos y campos para resultados
                    for match_idx, match in enumerate(round_data['matches']):
                        p1_name = f"{match['pair1'][0]} / {match['pair1'][1]}"
                        p2_name = f"{match['pair2'][0]} / {match['pair2'][1]}"
                        
                        col_match, col_score1, col_score2 = st.columns([3, 1, 1]) 
                        
                        with col_match:
                            st.markdown(f"**Pista {match['court']}**: {p1_name} **vs** {p2_name}")
                        
                        # Claves únicas para los inputs de resultado
                        match_id = f"r{round_data['round_num']}_m{match_idx}"
                        score1_key = f"score1_{match_id}"
                        score2_key = f"score2_{match_id}"

                        with col_score1:
                            st.number_input(
                                f"Games {match['pair1'][0].split()[0]}/{match['pair1'][1].split()[0]}", 
                                min_value=0, 
                                step=1, 
                                value=st.session_state.get(score1_key), # Leer valor actual del estado
                                key=score1_key, 
                                format="%d", # Asegurar formato entero
                                label_visibility="collapsed" 
                            )
                        
                        with col_score2:
                            st.number_input(
                                f"Games {match['pair2'][0].split()[0]}/{match['pair2'][1].split()[0]}", 
                                min_value=0, 
                                step=1, 
                                value=st.session_state.get(score2_key), 
                                key=score2_key,
                                format="%d",
                                label_visibility="collapsed"
                            )
                        st.divider()


    with tab2:
        st.subheader("Tabla de Clasificación")
        
        if not standings or not sorted_players:
            st.info("Aún no hay resultados ingresados o suficientes para calcular la clasificación.")
        else:
             # Convertir standings a DataFrame para mostrar en tabla
             standings_list = []
             for pos, player_name in enumerate(sorted_players):
                 stats = standings[player_name]
                 standings_list.append({
                     "Pos": pos + 1,
                     "Jugador": player_name,
                     "PJ": stats['PJ'],
                     "PG": stats['PG'],
                     "PE": stats['PE'],
                     "PP": stats['PP'],
                     "JG": stats['JG'],
                     "JR": stats['JR'],
                     "DG": stats['DG']
                 })
             
             df_standings = pd.DataFrame(standings_list)
             
             # Usar st.dataframe para tabla interactiva
             # Ocultar índice de pandas, usar nuestra columna 'Pos'
             st.dataframe(df_standings.set_index('Pos'), use_container_width=True) 

             # Botón de descarga
             st.download_button(
                 label="📄 Descargar Clasificación (.txt)",
                 data=generate_standings_text(standings, sorted_players, st.session_state.config.get('name', 'Torneo')),
                 file_name=f"clasificacion_{st.session_state.config.get('name', 'torneo').replace(' ', '_')}.txt",
                 mime='text/plain'
             )
             
    # Botón para reiniciar (opcional)
    st.divider()
    if st.button("⚠️ Empezar Nuevo Torneo (Borrar Datos Actuales)"):
        # Limpiar todo el estado de sesión relacionado con el torneo
        keys_to_delete = ['tournament_configured', 'config', 'players', 'fixture', 'player_inputs']
        # También borrar las claves de resultados (que tienen formato dinámico)
        result_keys = [k for k in st.session_state.keys() if k.startswith('score1_') or k.startswith('score2_')]
        keys_to_delete.extend(result_keys)
        
        for key in list(st.session_state.keys()): # Iterar sobre una copia de las claves
             if key in keys_to_delete or key.startswith('score1_') or key.startswith('score2_') or key.startswith("player_"):
                 del st.session_state[key]
        
        # Reinicializar valores por defecto importantes
        st.session_state.tournament_configured = False
        st.session_state.config = {}
        st.session_state.players = []
        st.session_state.fixture = None
        st.session_state.player_inputs = {}

        st.rerun() # --- CORREGIDO ---