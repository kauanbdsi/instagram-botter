#!/usr/bin/env python3
"""
main.py - Refactor sugerido para instagram-botter
Características:
- Session con reintentos y backoff
- CLI (argparse)
- Logging
- Delays aleatorios y control de concurrencia simple
- Soporte para proxies vía env/config
Nota: Este script es un esqueleto seguro y debe adaptarse a los endpoints y flujos reales.
"""

import os
import time
import random
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from dotenv import load_dotenv
from tqdm import tqdm

# Cargar .env si existe
load_dotenv()

# Configuración de logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; instagram-botter/1.0)"),
    "Accept": "application/json, text/plain, */*",
}

def create_session(retries: int = 5, backoff_factor: float = 0.5, proxies: Optional[Dict[str, str]] = None) -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    retry = Retry(
        total=retries,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]),
        backoff_factor=backoff_factor,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    if proxies:
        s.proxies.update(proxies)
    return s

def exponential_backoff_sleep(base: float = 1.0, attempt: int = 0, jitter: float = 0.5):
    wait = base * (2 ** attempt)
    wait = wait * (1 + random.uniform(-jitter, jitter))
    logger.debug("Backoff sleep: %.2fs (attempt=%d)", wait, attempt)
    time.sleep(max(0, wait))

def safe_request(session: requests.Session, method: str, url: str, max_attempts: int = 5, **kwargs) -> Optional[requests.Response]:
    attempt = 0
    while attempt < max_attempts:
        try:
            resp = session.request(method, url, timeout=(10, 30), **kwargs)
            logger.debug("Request %s %s -> %s", method, url, resp.status_code)
            # Manejo básico de rate limit / bloqueos
            if resp.status_code in (429, 420):
                logger.warning("Rate limited (status=%s). Backing off...", resp.status_code)
                exponential_backoff_sleep(base=2.0, attempt=attempt)
                attempt += 1
                continue
            return resp
        except requests.RequestException as e:
            logger.warning("RequestException on %s %s: %s", method, url, e)
            exponential_backoff_sleep(base=1.0, attempt=attempt)
            attempt += 1
    logger.error("Max attempts reached for %s %s", method, url)
    return None

# Ejemplo de acción: visitar perfil / like / follow
def like_post(session: requests.Session, post_url: str, dry_run: bool = False) -> bool:
    logger.info("Like post: %s", post_url)
    if dry_run:
        logger.info("[dry-run] Simulando like a %s", post_url)
        return True
    # Aquí iría la lógica real: obtener CSRF, endpoint correcto, payload, etc.
    resp = safe_request(session, "POST", post_url)  # <- adaptar
    if resp and resp.ok:
        logger.info("Like OK: %s", post_url)
        return True
    logger.warning("Like falló para %s: %s", post_url, getattr(resp, "status_code", "no_resp"))
    return False

def follow_user(session: requests.Session, user_id_or_url: str, dry_run: bool = False) -> bool:
    logger.info("Follow user: %s", user_id_or_url)
    if dry_run:
        logger.info("[dry-run] Simulando follow a %s", user_id_or_url)
        return True
    resp = safe_request(session, "POST", user_id_or_url)  # <- adaptar
    if resp and resp.ok:
        logger.info("Follow OK: %s", user_id_or_url)
        return True
    logger.warning("Follow falló para %s: %s", user_id_or_url, getattr(resp, "status_code", "no_resp"))
    return False

def process_targets(session: requests.Session, targets: List[str], action: str, concurrency: int = 2, dry_run: bool = False):
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = []
        for t in targets:
            if action == "like":
                futures.append(ex.submit(like_post, session, t, dry_run))
            elif action == "follow":
                futures.append(ex.submit(follow_user, session, t, dry_run))
        for f in tqdm(as_completed(futures), total=len(futures)):
            try:
                results.append(f.result())
            except Exception as e:
                logger.exception("Error en tarea: %s", e)
    return results

def load_targets_from_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as fh:
        lines = [l.strip() for l in fh if l.strip()]
    return lines

def parse_args():
    p = argparse.ArgumentParser(description="instagram-botter - herramienta mejorada y más segura")
    p.add_argument("--targets-file", "-t", help="Archivo con URLs/IDs objetivo, una por línea", required=True)
    p.add_argument("--action", "-a", choices=("like", "follow"), default="like", help="Acción a realizar")
    p.add_argument("--concurrency", "-c", type=int, default=int(os.getenv("CONCURRENCY", "2")), help="Máximo de hilos simultáneos")
    p.add_argument("--dry-run", action="store_true", help="No realiza cambios reales, solo simula")
    p.add_argument("--proxy", help="Proxy en formato http://user:pass@host:port (opcional)")
    return p.parse_args()

def main():
    args = parse_args()
    targets = load_targets_from_file(args.targets_file)
    proxies = None
    if args.proxy:
        # aplicar proxy para HTTP y HTTPS
        proxies = {"http": args.proxy, "https": args.proxy}
    session = create_session(
        retries=int(os.getenv("HTTP_RETRIES", "5")),
        backoff_factor=float(os.getenv("BACKOFF_FACTOR", "0.5")),
        proxies=proxies
    )
    # NOTE: login/autenticación debería implementarse aquí con credenciales seguras
    logger.info("Iniciando run: action=%s targets=%d concurrency=%d dry_run=%s", args.action, len(targets), args.concurrency, args.dry_run)
    # Añadir delay aleatorio entre tareas para simular comportamiento humano
    for i, chunk_start in enumerate(range(0, len(targets), args.concurrency)):
        chunk = targets[chunk_start:chunk_start + args.concurrency]
        process_targets(session, chunk, args.action, concurrency=args.concurrency, dry_run=args.dry_run)
        # esperar entre bloques
        sleep_time = random.uniform(2.0, 6.0)
        logger.debug("Sleeping between batches: %.2fs", sleep_time)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
