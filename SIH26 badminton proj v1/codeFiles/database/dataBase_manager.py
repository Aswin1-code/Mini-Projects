import sqlite3
import os
from datetime import datetime


# =====================================================
# DATABASE PATH
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, "badminton.db")


# =====================================================
# DATABASE CONNECTION
# =====================================================

def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# =====================================================
# INITIALIZE DATABASE
# =====================================================

def initialize_database():

    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------------------------------
    # PLAYERS TABLE
    # -------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            created_date TEXT NOT NULL
        )
    """)

    # -------------------------------------------------
    # SESSIONS TABLE
    # -------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            session_number INTEGER NOT NULL,
            session_date TEXT NOT NULL,

            total_swings INTEGER,

            avg_speed REAL,
            avg_impact REAL,
            avg_power REAL,

            consistency_score REAL,
            stability_score REAL,
            fatigue_score REAL,

            player_level TEXT,
            player_type TEXT,

            FOREIGN KEY (player_id)
                REFERENCES players(player_id)
        )
    """)

    # -------------------------------------------------
    # SWINGS TABLE
    # -------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS swings (
            swing_id INTEGER PRIMARY KEY AUTOINCREMENT,

            player_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,

            timestamp TEXT,

            ax REAL,
            ay REAL,
            az REAL,

            gx REAL,
            gy REAL,
            gz REAL,

            speed REAL,
            impact REAL,
            duration REAL,

            power REAL,
            efficiency REAL,

            stroke_type TEXT,
            intensity TEXT,

            FOREIGN KEY (player_id)
                REFERENCES players(player_id),

            FOREIGN KEY (session_id)
                REFERENCES sessions(session_id)
        )
    """)

    conn.commit()
    conn.close()

    print("✅ Database initialized successfully")
    print(f"📁 Database: {DATABASE_FILE}")


# =====================================================
# PLAYER FUNCTIONS
# =====================================================

def add_player(player_name):

    conn = get_connection()
    cursor = conn.cursor()

    created_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cursor.execute("""
        INSERT INTO players (
            player_name,
            created_date
        )
        VALUES (?, ?)
    """, (
        player_name,
        created_date
    ))

    player_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return player_id


def get_player(player_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM players
        WHERE player_id = ?
    """, (
        player_id,
    ))

    player = cursor.fetchone()

    conn.close()

    return player


def get_all_players():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM players
        ORDER BY player_id
    """)

    players = cursor.fetchall()

    conn.close()

    return players


def get_player_by_name(player_name):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM players
        WHERE player_name = ?
    """, (
        player_name,
    ))

    player = cursor.fetchone()

    conn.close()

    return player


def get_or_create_player(player_name):

    player = get_player_by_name(player_name)

    if player is not None:
        return player[0]

    return add_player(player_name)


# =====================================================
# SESSION FUNCTIONS
# =====================================================

def get_next_session_number(player_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT MAX(session_number)
        FROM sessions
        WHERE player_id = ?
    """, (
        player_id,
    ))

    result = cursor.fetchone()

    conn.close()

    if result[0] is None:
        return 1

    return result[0] + 1


def create_session(player_id):

    session_number = get_next_session_number(
        player_id
    )

    session_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO sessions (
            player_id,
            session_number,
            session_date
        )
        VALUES (?, ?, ?)
    """, (
        player_id,
        session_number,
        session_date
    ))

    session_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return session_id, session_number


# =====================================================
# UPDATE SESSION SUMMARY
# =====================================================

def update_session(
    session_id,
    total_swings,
    avg_speed,
    avg_impact,
    avg_power,
    consistency_score,
    stability_score,
    fatigue_score,
    player_level,
    player_type
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sessions
        SET
            total_swings = ?,
            avg_speed = ?,
            avg_impact = ?,
            avg_power = ?,
            consistency_score = ?,
            stability_score = ?,
            fatigue_score = ?,
            player_level = ?,
            player_type = ?

        WHERE session_id = ?
    """, (
        total_swings,
        avg_speed,
        avg_impact,
        avg_power,
        consistency_score,
        stability_score,
        fatigue_score,
        player_level,
        player_type,
        session_id
    ))

    conn.commit()
    conn.close()


# =====================================================
# GET PLAYER SESSIONS
# =====================================================

def get_player_sessions(player_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM sessions
        WHERE player_id = ?

        ORDER BY session_number
    """, (
        player_id,
    ))

    sessions = cursor.fetchall()

    conn.close()

    return sessions


# =====================================================
# SAVE SINGLE SWING
# =====================================================

def save_swing(
    player_id,
    session_id,
    timestamp,
    ax,
    ay,
    az,
    gx,
    gy,
    gz,
    speed,
    impact,
    duration,
    power,
    efficiency,
    stroke_type,
    intensity
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO swings (
            player_id,
            session_id,
            timestamp,

            ax,
            ay,
            az,

            gx,
            gy,
            gz,

            speed,
            impact,
            duration,

            power,
            efficiency,

            stroke_type,
            intensity
        )

        VALUES (
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?
        )
    """, (
        player_id,
        session_id,
        timestamp,

        ax,
        ay,
        az,

        gx,
        gy,
        gz,

        speed,
        impact,
        duration,

        power,
        efficiency,

        stroke_type,
        intensity
    ))

    conn.commit()
    conn.close()


# =====================================================
# SAVE DATAFRAME SWINGS
# =====================================================

def save_swings_dataframe(
    df,
    player_id,
    session_id
):

    conn = get_connection()
    cursor = conn.cursor()

    for _, row in df.iterrows():

        cursor.execute("""
            INSERT INTO swings (
                player_id,
                session_id,
                timestamp,

                ax,
                ay,
                az,

                gx,
                gy,
                gz,

                speed,
                impact,
                duration,

                power,
                efficiency,

                stroke_type,
                intensity
            )

            VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?
            )
        """, (
            player_id,
            session_id,
            str(
                row.get(
                    "timestamp",
                    ""
                )
            ),

            row.get("ax", None),
            row.get("ay", None),
            row.get("az", None),

            row.get("gx", None),
            row.get("gy", None),
            row.get("gz", None),

            row.get("speed", None),
            row.get("impact", None),
            row.get("duration", None),

            row.get("power", None),
            row.get("efficiency", None),

            row.get(
                "stroke_type",
                None
            ),

            row.get(
                "final_prediction",
                None
            )
        ))

    conn.commit()
    conn.close()


# =====================================================
# GET SESSION SWINGS
# =====================================================

def get_session_swings(session_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM swings
        WHERE session_id = ?

        ORDER BY swing_id
    """, (
        session_id,
    ))

    swings = cursor.fetchall()

    conn.close()

    return swings


# =====================================================
# GET PLAYER SWINGS
# =====================================================

def get_player_swings(player_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM swings
        WHERE player_id = ?

        ORDER BY swing_id
    """, (
        player_id,
    ))

    swings = cursor.fetchall()

    conn.close()

    return swings


# =====================================================
# GET PLAYER HISTORY AS DATAFRAME
# =====================================================

def get_player_history(player_id):

    conn = get_connection()

    query = """
        SELECT

            s.session_number,
            s.session_date,

            s.total_swings,

            s.avg_speed,
            s.avg_impact,
            s.avg_power,

            s.consistency_score,
            s.stability_score,
            s.fatigue_score,

            s.player_level,
            s.player_type

        FROM sessions s

        WHERE s.player_id = ?

        ORDER BY s.session_number
    """

    try:

        import pandas as pd

        df = pd.read_sql_query(
            query,
            conn,
            params=(player_id,)
        )

    finally:

        conn.close()

    return df


# =====================================================
# DATABASE SUMMARY
# =====================================================

def get_database_summary():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM players
    """)

    player_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM sessions
    """)

    session_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM swings
    """)

    swing_count = cursor.fetchone()[0]

    conn.close()

    return {
        "players": player_count,
        "sessions": session_count,
        "swings": swing_count
    }


# =====================================================
# REMOVE TEST PLAYER
# =====================================================

def remove_test_data():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT player_id
        FROM players
        WHERE player_name = ?
    """, (
        "TEST_PLAYER",
    ))

    test_player = cursor.fetchone()

    if test_player is None:

        conn.close()

        print(
            "ℹ️ No TEST_PLAYER found."
        )

        return

    player_id = test_player[0]

    # Delete swings first because
    # swings depend on sessions/players.

    cursor.execute("""
        DELETE FROM swings
        WHERE player_id = ?
    """, (
        player_id,
    ))

    cursor.execute("""
        DELETE FROM sessions
        WHERE player_id = ?
    """, (
        player_id,
    ))

    cursor.execute("""
        DELETE FROM players
        WHERE player_id = ?
    """, (
        player_id,
    ))

    conn.commit()
    conn.close()

    print(
        "🧹 TEST_PLAYER data removed successfully."
    )


# =====================================================
# DATABASE TEST
# =====================================================

def test_database():

    print()
    print("======================================")
    print("🏸 BADMINTON DATABASE TEST")
    print("======================================")

    initialize_database()

    print()
    print("📊 DATABASE SUMMARY")

    summary = get_database_summary()

    print(
        f"Players : {summary['players']}"
    )

    print(
        f"Sessions: {summary['sessions']}"
    )

    print(
        f"Swings  : {summary['swings']}"
    )

    print()
    print("======================================")
    print("✅ DATABASE CHECK COMPLETED")
    print("======================================")


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    test_database()