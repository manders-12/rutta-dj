import sqlite3


class DBConnector:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establish a connection to the SQLite database."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def create_tables(self):
        """Create tables for recommendations and ratings if they don't exist."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER UNIQUE NOT NULL,
                title TEXT,
                author TEXT,
                link TEXT,
                genre TEXT,
                tag TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER UNIQUE NOT NULL,
                recommended_by TEXT,
                track_name TEXT,
                link TEXT,
                rating INTEGER,
                review TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

    def insert_recommendation(self, message_id, author, title, link, genre, tag):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO recommendations (message_id, title, author, link, genre, tag)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (message_id, title, author, link, genre, tag))
        conn.commit()

    def insert_rating(self, message_id, recommended_by, track_name, link, rating, review):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ratings (message_id, recommended_by, track_name, link, rating, review)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (message_id, recommended_by, track_name, link, rating, review))
        conn.commit()
    
    def get_all_recommended_by(self):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT recommended_by FROM ratings
        ''')
        return [row['recommended_by'] for row in cursor.fetchall()]

    def get_tracks_by_rating(self, rating):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM ratings WHERE rating = ?
        ''', (rating,))
        return cursor.fetchall()
    
    def get_tracks_by_recommended_by(self, recommended_by):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM ratings WHERE recommended_by = ?
        ''', (recommended_by,))
        return cursor.fetchall()