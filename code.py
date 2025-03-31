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
        max_matches_in_round = min(num_courts, len(players_this_round) // 4)
        
        possible_pairs = list(combinations(players_this_round, 2))
        random.shuffle(possible_pairs)

        # Intentar formar parejas que no hayan jugado juntas recientemente
        # (Esta lógica es básica, podría mejorarse mucho)
        potential_pairs = []
        players_already_paired = set()
        for p1, p2 in possible_pairs:
            pair_tuple = tuple(sorted((p1, p2)))
            # Priorizar parejas nuevas
            priority = 1 if pair_tuple not in played_pairs else 0 
            if p1 not in players_already_paired and p2 not in players_already_paired:
                 potential_pairs.append( (priority, pair_tuple) )
                 # No añadir aquí a players_already_paired todavía

        # Ordenar por prioridad (nuevas primero), luego aleatorio
        potential_pairs.sort(key=lambda x: x[0], reverse=True) 
        
        final_round_pairs = []
        players_in_final_pairs = set()
        for _, pair_tuple in potential_pairs:
            p1, p2 = pair_tuple
            if p1 not in players_in_final_pairs and p2 not in players_in_final_pairs:
                final_round_pairs.append(pair_tuple)
                players_in_final_pairs.add(p1)
                players_in_final_pairs.add(p2)
                # Actualizar historial para la *próxima* ronda
                # played_pairs.add(pair_tuple) # Mover esto para después de asignar partido

        # --- Enfrentar Parejas ---
        match_count = 0
        assigned_players_in_match = set()
        available_pairs_for_match = list(final_round_pairs) # Copia para pop
        random.shuffle(available_pairs_for_match)

        while match_count < max_matches_in_round and len(available_pairs_for_match) >= 2:
            # Tomar la primera pareja
            pair1 = available_pairs_for_match.pop(0)
            
            # Buscar una segunda pareja compatible (jugadores distintos)
            found_opponent = False
            for i in range(len(available_pairs_for_match)):
                pair2 = available_pairs_for_match[i]
                if not set(pair1) & set(pair2): # Sin jugadores en común
                    # Enfrentamiento encontrado
                    available_pairs_for_match.pop(i) # Quitar oponente de disponibles
                    
                    # Añadir al historial AHORA que se confirma el partido
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
                    break # Pasar al siguiente partido

            if not found_opponent:
                # No se encontró oponente para pair1, devolverla a la lista por si acaso
                # (aunque en esta lógica simple, probablemente no se use más)
                # available_pairs_for_match.append(pair1) # Opcional
                pass # No se pudo formar partido con esta pareja

        players_resting = [p for p in all_players if p not in assigned_players_in_match]

        # Añadir la ronda al fixture solo si tiene partidos
        if round_matches:
             fixture["rounds"].append({
                 "round_num": len(fixture["rounds"]) + 1, # Numerar secuencialmente
                 "matches": round_matches,
                 "resting": players_resting
             })
        # Si no hay partidos, no añadir la ronda (podría pasar si quedan pocos jugadores impares)

    # Asegurar que haya al menos una ronda si es posible
    if not fixture["rounds"] and num_players >= 4 and num_courts >= 1:
         st.warning("No se pudieron generar rondas con la configuración actual y el algoritmo simple. Intenta con más jugadores/pistas o revisa la lógica.")


    return fixture

def calculate_standings(players, fixture_data):
    """Calcula la clasificación basada en los resultados introducidos en el fixture."""
    standings = {
        player: {"JG": 0, "JR": 0, "DG": 0, "PG": 0, "PP": 0, "PE": 0, "PJ": 0}
        for player in players
    }

    if not fixture_data or 'rounds' not in fixture_data:
        return standings, [] # Devuelve vacío si no hay fixture

    for round_data in fixture_data['rounds']:
        for match_idx, match in enumerate(round_data['matches']):
            # Leer resultados directamente del estado de sesión si existen para este widget
            score1_key = f"score1_r{round_data['round_num']}_m{match_idx}"
            score2_key = f"score2_r{round_data['round_num']}_m{match_idx}"

            score1 = st.session_state.get(score1_key, None)
            score2 = st.session_state.get(score2_key, None)

            # Actualizar el fixture en session_state con los valores actuales de los widgets
            # Esto asegura que los cálculos usen los últimos datos ingresados
            match['score1'] = score1
            match['score2'] = score2

            if score1 is not None and score2 is not None:
                s1 = int(score1)
                s2 = int(score2)
                pair1 = match['pair1']
                pair2 = match['pair2']

                # Solo contar si el partido no se ha contado antes para este jugador
                # Necesitamos rastrear qué partidos ya se contaron por jugador
                # Simplificación: Asumimos que si recalculamos todo, está bien.
                # Para rendimiento en apps grandes, se necesitaría optimizar.

                # Actualizar PJ (solo la primera vez que procesamos este partido en un recálculo)
                # Necesitamos una forma más robusta o recalcular todo siempre
                # Vamos a recalcular todo siempre para simplicidad en Streamlit

                # Actualizar Games Ganados/Recibidos
                for p in pair1:
                    standings[p]['JG'] += s1
                    standings[p]['JR'] += s2
                for p in pair2:
                    standings[p]['JG'] += s2
                    standings[p]['JR'] += s1

                # Actualizar Partidos Ganados/Perdidos/Empatados
                if s1 > s2:
                    for p in pair1: standings[p]['PG'] += 1
                    for p in pair2: standings[p]['PP'] += 1
                elif s2 > s1:
                    for p in pair1: standings[p]['PP'] += 1
                    for p in pair2: standings[p]['PG'] += 1
                else: # Empate
                    for p in pair1: standings[p]['PE'] += 1
                    for p in pair2: standings[p]['PE'] += 1

    # Recalcular PJ y DG al final
    for player in players:
        player_stats = standings[player]
        # Recalcular PJ contando partidos donde el score no es None
        count_pj = 0
        for r in fixture_data['rounds']:
            for m in r['matches']:
                 if m['score1'] is not None and m['score2'] is not None:
                      if player in m['pair1'] or player in m['pair2']:
                           count_pj +=1
        player_stats['PJ'] = count_pj // 2 # Cada partido involucra 2 ocurrencias del jugador en la cuenta
        
        # Asegurar PJ correcto si un jugador jugó pero no se ingresó resultado aún
        # (Podría ser 0 si todos sus partidos están sin resultado)
        # Comentado por ahora, recalculamos basado en scores no None
        # player_stats['PJ'] = player_stats['PG'] + player_stats['PP'] + player_stats['PE']
        
        player_stats['DG'] = player_stats['JG'] - player_stats['JR']


    # Ordenar: 1º PG (desc), 2º DG (desc), 3º JG (desc) - Criterio común
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
            config['num_players'] = st.number_input(
                "Número total de jugadores (par >= 4)", 
                min_value=4, 
                step=2, 
                value=8
            )
        with col2:
            config['num_courts'] = st.number_input(
                "Número de pistas disponibles (>= 1)", 
                min_value=1, 
                step=1, 
                value=2
            )

        st.subheader("Nombres de los Jugadores")
        player_names = {} 
        cols_players = st.columns(3) # Organizar en columnas para mejor layout
        for i in range(config['num_players']):
             # Usar session_state para recordar los nombres entre re-runs del form
             default_name = st.session_state.player_inputs.get(i, f"Jugador {i+1}") 
             player_names[i] = cols_players[i % 3].text_input(
                 f"Jugador {i + 1}", 
                 value=default_name, 
                 key=f"player_{i}" # Clave única para cada input
             )
             st.session_state.player_inputs[i] = player_names[i] # Guardar para la próxima vez
             
        submitted = st.form_submit_button("Registrar Jugadores y Generar Fixture")
        
        if submitted:
            players = [name.strip() for name in player_names.values() if name.strip()]
            
            # Validaciones
            if len(players) != config['num_players']:
                st.error(f"Error: Se esperaban {config['num_players']} nombres de jugador, pero se encontraron {len(players)} no vacíos.")
            elif len(set(players)) != len(players):
                 st.error("Error: Hay nombres de jugador duplicados.")
            elif config['num_courts'] > config['num_players'] // 4 and config['num_players'] > 0 :
                 st.warning(f"Advertencia: Tienes {config['num_courts']} pistas pero solo se pueden usar {config['num_players'] // 4} simultáneamente con {config['num_players']} jugadores.")
                 config['num_courts'] = config['num_players'] // 4 # Ajustar para el algoritmo
            
            else:
                # Guardar configuración y jugadores
                st.session_state.config = config
                st.session_state.players = players
                
                # Generar Fixture
                st.session_state.fixture = generate_simplified_fixture(players, config['num_courts'])
                
                if st.session_state.fixture and st.session_state.fixture['rounds']:
                     st.session_state.tournament_configured = True
                     st.success("¡Torneo configurado y fixture generado!")
                     # Limpiar inputs temporales
                     st.session_state.player_inputs = {} 
                     # Forzar re-run para pasar a la siguiente fase
                     st.experimental_rerun() 
                else:
                     st.error("No se pudo generar el fixture. Revisa la configuración o el número de jugadores/pistas.")


# --- Fase 2: Visualización y Gestión del Torneo ---
if st.session_state.tournament_configured:
    st.header(f"🏆 Torneo: {st.session_state.config.get('name', 'Sin Nombre')}")
    st.caption(f"{len(st.session_state.players)} jugadores | {st.session_state.config.get('num_courts', '?')} pistas")

    # Calcular standings ANTES de mostrar las pestañas para tener los datos listos
    # Asegurarse de que fixture existe y tiene rondas
    if st.session_state.fixture and 'rounds' in st.session_state.fixture:
        # Recalcular standings en cada interacción que pueda cambiar resultados
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
                        
                        # Usar columnas para alinear mejor
                        col_match, col_score1, col_score2 = st.columns([3, 1, 1]) 
                        
                        with col_match:
                            st.markdown(f"**Pista {match['court']}**: {p1_name} **vs** {p2_name}")
                        
                        # Claves únicas para los inputs de resultado
                        score1_key = f"score1_r{round_data['round_num']}_m{match_idx}"
                        score2_key = f"score2_r{round_data['round_num']}_m{match_idx}"

                        with col_score1:
                            # Usar st.session_state para obtener el valor guardado
                            current_score1 = st.session_state.get(score1_key) 
                            st.number_input(
                                f"Games {match['pair1'][0].split()[0]}/{match['pair1'][1].split()[0]}", 
                                min_value=0, 
                                step=1, 
                                value=current_score1, # Valor actual del estado
                                key=score1_key, # Clave para guardar/recuperar estado
                                label_visibility="collapsed" # Ocultar label si es redundante
                            )
                        
                        with col_score2:
                            current_score2 = st.session_state.get(score2_key)
                            st.number_input(
                                f"Games {match['pair2'][0].split()[0]}/{match['pair2'][1].split()[0]}", 
                                min_value=0, 
                                step=1, 
                                value=current_score2, 
                                key=score2_key,
                                label_visibility="collapsed"
                            )
                        st.divider()


    with tab2:
        st.subheader("Tabla de Clasificación")
        
        if not standings or not sorted_players:
            st.info("Aún no hay resultados para calcular la clasificación.")
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
        
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()