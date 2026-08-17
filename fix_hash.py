from passlib.context import CryptContext
import psycopg2

pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
h = pwd.hash('123456')

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='postgres',
    password='6618',
    dbname='AquaSys'
)
cur = conn.cursor()
cur.execute("UPDATE usuario SET senha_hash = %s WHERE cpf_cnpj = '000.000.000-00'", (h,))
conn.commit()
print('Atualizado! Hash:', h)
conn.close()