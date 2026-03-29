import time

import redis


def main():
    client = redis.Redis(host="localhost", port=6379, db=0)

    client.set("cache:usuario:1", "Matias", ex=60)
    client.set("cache:visitas", 42, ex=30)

    print("usuario 1:", client.get("cache:usuario:1"))
    print("visitas:", client.get("cache:visitas"))

    print("Esperando 35 segundos para demostrar expiración de caché...")
    time.sleep(35)

    print("visitas después de expiración:", client.get("cache:visitas"))


if __name__ == "__main__":
    main()
