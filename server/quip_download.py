#!/usr/bin/env python3
"""
Video‑ingestion script for MariaDB.

- Reads DB credentials from environment variables:
    DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
- Retrieves a JSON array of video objects from the URL in API_URL.
- Inserts each record into the `videos` table.
- Uses INSERT … ON DUPLICATE KEY UPDATE to avoid duplicate‑key failures.
- Provides robust error handling and progress output.

Dependencies:
    pip install requests mysql-connector-python
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

import requests
import mysql.connector
from mysql.connector import errorcode, MySQLConnection, cursor

# --------------------------------------------------------------------------- #
# Configuration & Logging
# --------------------------------------------------------------------------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

API_URL = "https://quipvid.com/api/quips/"
if not API_URL:
    logging.error("Environment variable API_URL is not set.")
    sys.exit(1)

# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #


def get_db_connection() -> MySQLConnection:
    """Create and return a MySQL/MariaDB connection using env vars."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="vibeout",
            password="viebout",
            database="vibeout_quips",
        )
        logging.info("Connected to MariaDB at %s", os.getenv("DB_HOST", "localhost"))
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logging.error("Invalid DB credentials")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            logging.error("Database does not exist")
        else:
            logging.error("Database connection error: %s", err)
        sys.exit(1)


def fetch_video_data(url: str) -> List[Dict[str, Any]]:
    """GET the JSON payload from the API and return a list of video dicts."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            logging.error("API did not return a list – aborting.")
            sys.exit(1)
        logging.info("Fetched %d video records from API.", len(data))
        return data
    except requests.RequestException as exc:
        logging.error("Network error while fetching video data: %s", exc)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        logging.error("Failed to decode JSON response: %s", exc)
        sys.exit(1)


def upsert_videos(conn: MySQLConnection, videos: List[Dict[str, Any]]) -> None:
    """
    Insert or update each video record.

    The `videos` table is expected to have a PRIMARY KEY or UNIQUE index on `id`.
    """
    sql = """
        INSERT INTO videos
            (id, url, name, title, image, video, user, views, poster, script)
        VALUES
            (%(id)s, %(url)s, %(name)s, %(title)s, %(image)s,
             %(video)s, %(user)s, %(views)s, %(poster)s, %(script)s)
        ON DUPLICATE KEY UPDATE
            url = VALUES(url),
            name = VALUES(name),
            title = VALUES(title),
            image = VALUES(image),
            video = VALUES(video),
            user = VALUES(user),
            views = VALUES(views),
            poster = VALUES(poster),
            script = VALUES(script);
    """

    cursor = conn.cursor(dictionary=True)
    total = len(videos)
    success = 0

    for idx, video in enumerate(videos, start=1):
        try:
            # Ensure required keys exist; missing keys become None
            payload = {
                "id": video.get("id"),
                "url": video.get("url"),
                "name": video.get("name"),
                "title": video.get("title"),
                "image": video.get("image"),
                "video": video.get("video"),
                "user": video.get("user"),
                "views": video.get("views"),
                "poster": video.get("poster"),
                "script": video.get("script"),
            }
            cursor.execute(sql, payload)
            success += cursor.rowcount
            logging.info("Processed %d/%d (id=%s)", idx, total, payload["id"])
        except mysql.connector.Error as err:
            logging.warning(
                "Failed to upsert video id=%s: %s (continuing)", video.get("id"), err
            )
            # Continue with next record; do not abort the whole batch.

    # Commit once after the loop – atomic for the whole batch.
    try:
        conn.commit()
        logging.info(
            "Database commit successful. %d rows affected (including updates).",
            success,
        )
    except mysql.connector.Error as err:
        conn.rollback()
        logging.error("Commit failed, transaction rolled back: %s", err)
        sys.exit(1)
    finally:
        cursor.close()


# --------------------------------------------------------------------------- #
# Main execution
# --------------------------------------------------------------------------- #


def main() -> None:
    conn = get_db_connection()
    try:
        videos = fetch_video_data(API_URL)
        if not videos:
            logging.info("No video records to process.")
            return
        upsert_videos(conn, videos)
        logging.info("All video records have been processed.")
    finally:
        conn.close()
        logging.info("Database connection closed.")


if __name__ == "__main__":
    main()