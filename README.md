# TuHoy

Periódico en [tuhoy.com](https://tuhoy.com), servido con **Ghost 5 + MySQL 8**.

En el Dell el stack lo gestiona Coolify (servicio **TuHoy Ghost**). HTTPS lo terminan Cloudflare y Traefik. MySQL no se publica a internet.

## Admin

https://tuhoy.com/ghost

La primera visita abre la pantalla de creación de cuenta. No hay credenciales de fábrica.

## Docker Compose (referencia)

```bash
cp .env.example .env
# edita contraseñas y GHOST_URL
docker compose up -d
```

Ghost escucha el puerto interno **2368**. No bindees 80/443 en el host si Coolify/Traefik ya los usan.

## Cloudflare

Si `tuhoy.com` va por naranja/túnel, el origen suele ver HTTP. Ghost, con `url=https://tuhoy.com`, redirige a HTTPS y el navegador entra en `ERR_TOO_MANY_REDIRECTS`.

Hay que mandar a Ghost `X-Forwarded-Proto: https` (etiquetas Traefik del compose / Coolify) **o** que el túnel/origen hable HTTPS. El redirect HTTP→HTTPS de Coolify debe quedarse apagado detrás de Cloudflare.

## Correo

SMTP no está configurado. El sitio funciona; newsletters e emails de Ghost no. Añade host/usuario/contraseña reales en Coolify cuando los tengas.

## Copias de seguridad

1. Volumen de contenido Ghost (`/var/lib/ghost/content`)
2. Volumen o dump de MySQL (`/var/lib/mysql`)

En Coolify: TuHoy Ghost → Backups.

## Tema

El diseño de periódico (portada, secciones, destacados) se instala después, desde Ghost → Settings → Design, o subiendo un tema a `content/themes`.

## Sitio estático anterior

`public/`, `Dockerfile` y `nginx.conf` son la portada HTML previa. Ya no son el origen de tuhoy.com.
