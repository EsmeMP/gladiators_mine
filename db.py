import psycopg2
from psycopg2 import pool

# Crear un pool de comexiones
connection_pool = pool.SimpleConnectionPool(
    1, 20,
    database="database_gladiators",
    user="first_gladiator",
    password="gladiator1st",
    host="localhost",
    port="5432"
)

def conectar():
    return connection_pool.getconn()

def desconectar(conn):
    connection_pool.putconn(conn)