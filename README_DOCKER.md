# 🐳 Docker Deployment Guide

## Quick Start

### Levantar todo el sistema

```bash
docker-compose up -d
```

Esto levanta:
- ✅ PostgreSQL (puerto 5433)
- ✅ Redis (puerto 6379)
- ✅ Backend API (puerto 8000)
- ✅ Frontend React (puerto 3000)

### Acceder a los servicios

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **PostgreSQL**: localhost:5433

### Levantar con nginx (proxy reverso)

```bash
docker-compose --profile with-nginx up -d
```

Esto además levanta:
- ✅ nginx en puerto 80
- Acceso unificado: http://localhost

---

## Comandos útiles

### Ver logs

```bash
# Todos los servicios
docker-compose logs -f

# Solo un servicio
docker-compose logs -f api
docker-compose logs -f frontend
```

### Reconstruir después de cambios

```bash
# Rebuild solo el backend
docker-compose build api
docker-compose up -d api

# Rebuild solo el frontend
docker-compose build frontend
docker-compose up -d frontend

# Rebuild todo
docker-compose build
docker-compose up -d
```

### Parar servicios

```bash
# Parar todo
docker-compose down

# Parar y borrar volúmenes (CUIDADO: borra la BD)
docker-compose down -v
```

### Ver servicios corriendo

```bash
docker-compose ps
```

### Acceder a un container

```bash
# Bash en el backend
docker-compose exec api bash

# Bash en el frontend
docker-compose exec frontend sh

# PostgreSQL CLI
docker-compose exec postgres psql -U labor_user -d labor_observatory
```

---

## Estructura de Servicios

```
┌─────────────────────────────────────────┐
│  Docker Compose Network                 │
│                                          │
│  ┌────────────┐      ┌────────────┐    │
│  │ PostgreSQL │      │   Redis    │    │
│  │ :5433      │      │   :6379    │    │
│  └─────┬──────┘      └──────┬─────┘    │
│        │                    │           │
│        └────────┬───────────┘           │
│                 ▼                        │
│          ┌────────────┐                 │
│          │  API       │                 │
│          │  :8000     │                 │
│          └──────┬─────┘                 │
│                 │                        │
│                 ▼                        │
│          ┌────────────┐                 │
│          │ Frontend   │                 │
│          │  :3000     │                 │
│          └──────┬─────┘                 │
│                 │                        │
│          (opcional)                     │
│                 ▼                        │
│          ┌────────────┐                 │
│          │   nginx    │                 │
│          │    :80     │                 │
│          └────────────┘                 │
└─────────────────────────────────────────┘
```

---

## Desarrollo Local vs Docker

### Para desarrollo (hot reload):

```bash
# Backend (local con venv)
source venv/bin/activate
uvicorn src.api.main:app --reload

# Frontend (local con npm)
cd frontend
npm run dev
```

### Para testing como producción:

```bash
# Levantar en Docker
docker-compose up -d

# Ver que todo funcione
curl http://localhost:8000/api/stats
curl http://localhost:3000
```

---

## Troubleshooting

### Error: Puerto ya en uso

```bash
# Ver qué está usando el puerto
lsof -i :8000
lsof -i :3000

# Matar proceso
kill -9 <PID>
```

### Error: Build falla

```bash
# Limpiar cache de Docker
docker-compose down
docker system prune -a
docker-compose build --no-cache
```

### Error: Base de datos no conecta

```bash
# Ver logs de postgres
docker-compose logs postgres

# Verificar que esté saludable
docker-compose ps postgres

# Reiniciar postgres
docker-compose restart postgres
```

### Error: Frontend no conecta con API

Verificar variables de entorno en `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Volúmenes persistentes

```bash
# Ver volúmenes
docker volume ls

# Backup de la base de datos
docker-compose exec postgres pg_dump -U labor_user labor_observatory > backup.sql

# Restaurar backup
docker-compose exec -T postgres psql -U labor_user labor_observatory < backup.sql
```

---

## Para producción

### Variables de entorno

Crear archivo `.env` en la raíz:

```bash
# Database
POSTGRES_PASSWORD=CHANGE_THIS_IN_PRODUCTION
DB_HOST=postgres
DB_PORT=5432

# API
DATABASE_URL=postgresql://labor_user:CHANGE_THIS@postgres:5432/labor_observatory

# Frontend
NEXT_PUBLIC_API_URL=http://your-domain.com/api
```

### Con nginx

```bash
docker-compose --profile with-nginx up -d
```

Accede todo desde: http://localhost

---

## Checklist de deployment

- [ ] Cambiar `POSTGRES_PASSWORD` en `.env`
- [ ] Actualizar `NEXT_PUBLIC_API_URL` para producción
- [ ] Verificar que todos los servicios levanten: `docker-compose ps`
- [ ] Probar frontend: http://localhost:3000
- [ ] Probar API: http://localhost:8000/api/docs
- [ ] Verificar logs: `docker-compose logs -f`
- [ ] Probar scraping desde el frontend
- [ ] Backup inicial de la BD

---

## Recursos

- **Logs**: `./logs/`
- **Outputs**: `./outputs/`
- **Data**: `./data/`
- **Config**: `./config/`

Todos estos directorios están mapeados como volúmenes en Docker.
