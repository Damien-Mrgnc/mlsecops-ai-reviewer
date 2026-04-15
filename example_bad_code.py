# Fichier de TEST — contient des failles intentionnelles pour valider l'agent

import requests
import sqlite3

# FAILLE 1 : Secret hardcodé
API_KEY = "sk-prod-1234567890abcdef"
DB_PASSWORD = "super_secret_123"

def get_user(id):
    # FAILLE 2 : Injection SQL
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = " + id)
    return cursor.fetchone()

def call_api(data):
    # FAILLE 3 : SSL désactivé
    return requests.post("https://api.example.com", json=data, verify=False)

def process(x):
    # AVERTISSEMENT : nom de variable non descriptif
    y = x * 2
    return y
