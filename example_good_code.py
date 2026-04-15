# Fichier de TEST — code sécurisé, doit être APPROUVÉ par l'agent

import os
import sqlite3

import requests


def get_user_by_id(user_id: int) -> tuple | None:
    """Récupère un utilisateur par ID avec une requête paramétrée."""
    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    connection.close()
    return row


def call_external_api(payload: dict) -> dict:
    """Appelle l'API externe avec SSL activé et clé depuis l'environnement."""
    api_key = os.environ["EXTERNAL_API_KEY"]
    response = requests.post(
        "https://api.example.com/data",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        verify=True,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def double_value(input_value: int) -> int:
    """Multiplie une valeur par deux."""
    return input_value * 2
