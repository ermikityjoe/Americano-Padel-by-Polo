# 🏓 Gestor de Torneos Americano de Pádel (Streamlit App)

Una aplicación web simple creada con Streamlit para gestionar torneos de pádel estilo americano.

## Funcionalidades

*   Configuración del nombre del torneo, número de jugadores y pistas.
*   Registro de nombres de jugadores.
*   Generación **simplificada** y **aleatoria** de rondas y partidos (¡No garantiza una rotación perfecta ni evita repetición de parejas!).
*   Entrada de resultados (games ganados por pareja) por partido.
*   Visualización de la clasificación en tiempo real (ordenada por PG, DG, JG).
*   Descarga de la clasificación en formato de texto (.txt).

## Cómo Ejecutar Localmente

1.  **Prerrequisitos:**
    *   Tener Python 3.7+ instalado.
    *   Tener Git instalado (para clonar el repositorio).

2.  **Clonar el Repositorio:**
    ```bash
    git clone <URL-de-tu-repositorio-en-GitHub>
    cd <nombre-del-directorio-clonado>
    ```

3.  **Crear un Entorno Virtual (Recomendado):**
    ```bash
    python -m venv venv
    # En Windows:
    venv\Scripts\activate
    # En macOS/Linux:
    source venv/bin/activate
    ```

4.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Ejecutar la Aplicación Streamlit:**
    ```bash
    streamlit run app.py
    ```

6.  Abre tu navegador web y ve a la dirección local que indica Streamlit (normalmente `http://localhost:8501`).

## Importante

*   El algoritmo de generación de fixture es una **aproximación simplificada** y no sigue estrictamente las reglas de un torneo americano perfecto para evitar repeticiones o garantizar que todos jueguen contra todos. Se basa en aleatorización.
*   La aplicación guarda el estado en la sesión del navegador mientras está abierta. Si cierras la pestaña o reinicias, tendrás que empezar de nuevo (a menos que lo despliegues en un servicio que maneje sesiones).