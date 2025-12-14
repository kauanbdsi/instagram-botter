# instagram-botter 

Este repositorio contiene herramientas de automatización para acciones en Instagram. WARNING: El uso de estas herramientas puede violar los términos de servicio de Instagram. Úsalas con responsabilidad y en cuentas de prueba.

## Mejoras propuestas
- Session con reintentos y backoff
- Logging y CLI
- Soporte para proxies y dry-run
- Requisitos fijados en `reqs.txt`

## Instalación
1. Crear y activar un entorno virtual:
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:
```bash
pip install -r reqs.txt
```

3. Configurar variables (opcional) en un `.env`:
```
USER_AGENT="Mozilla/5.0 (compatible; instagram-botter/1.0)"
CONCURRENCY=2
HTTP_RETRIES=5
BACKOFF_FACTOR=0.5
LOG_LEVEL=INFO
```

## Uso
Prepara un archivo `targets.txt` con cada URL/ID objetivo en una línea.
Ejemplo:
```
https://www.instagram.com/p/EXAMPLEPOST/
https://www.instagram.com/username/
```

Ejecuta (simulación):
```bash
python main.py --targets-file targets.txt --action like --dry-run
```

Ejecuta (real, con proxy por ejemplo):
```bash
python main.py -t targets.txt -a follow --proxy "http://user:pass@proxy:port"
```

## Riesgos y recomendaciones
- Usa cuentas de pruebas.
- Incrementa tiempos entre acciones y limita la concurrencia.
- Monitoriza códigos HTTP (429/403) y añade backoff más agresivo si aparecen.
- Considera usar una librería mantenida (instagrapi) para flujos de autenticación y manejo de sesiones, captcha y cambios del API.
